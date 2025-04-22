"""
Canvas Announcements Sync

This module provides functionality for synchronizing announcement data between
the Canvas API and the local database asynchronously.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

from canvas_mcp.models import DBAnnouncement
from canvas_mcp.utils.db_manager import run_db_persist_in_thread
from canvas_mcp.utils.formatters import convert_html_to_markdown

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService

# Configure logging
logger = logging.getLogger(__name__)


async def sync_announcements(
    sync_service: "SyncService", course_ids: list[int] | None = None
) -> int:
    """
    Synchronize announcement data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        course_ids: List of local course IDs to sync announcements for.

    Returns:
        Number of announcements synced/updated.
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available for announcement sync")
        return 0
    if not course_ids:
        logger.warning("No course IDs provided for announcement sync.")
        return 0

    # Get course mapping (canvas_id -> local_id)
    conn_map, cursor_map = sync_service.db_manager.connect()
    try:
        placeholders = ", ".join("?" * len(course_ids))
        cursor_map.execute(
            f"SELECT id, canvas_course_id FROM courses WHERE id IN ({placeholders})",
            course_ids,
        )
        courses_to_sync = {
            row["canvas_course_id"]: row["id"] for row in cursor_map.fetchall()
        }
    except Exception as e:
        logger.error(f"Failed to fetch course mapping for announcements: {e}")
        return 0
    finally:
        conn_map.close()

    if not courses_to_sync:
        logger.warning("No matching courses found in DB for announcement sync.")
        return 0

    # --- Parallel Fetch Stage ---
    tasks = []
    course_context = []  # Store (local_id, canvas_id) for context

    logger.info(
        f"Creating tasks to fetch announcements for {len(courses_to_sync)} courses..."
    )
    for canvas_course_id, local_course_id in courses_to_sync.items():
        task = asyncio.create_task(
            _fetch_announcements_for_course(
                sync_service, canvas_course_id, local_course_id
            )
        )
        tasks.append(task)
        course_context.append((local_course_id, canvas_course_id))

    logger.info(f"Gathering announcement data for {len(tasks)} tasks...")
    results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Finished gathering announcement data.")

    # --- Process & Validate Stage ---
    all_valid_announcements: list[DBAnnouncement] = []
    total_raw_count = 0
    for i, result in enumerate(results_or_exceptions):
        local_course_id, canvas_course_id = course_context[i]
        if isinstance(result, Exception):
            logger.error(
                f"Failed fetching announcements for course {local_course_id} (Canvas ID: {canvas_course_id}): {result}"
            )
            continue
        if result is None:
            logger.warning(
                f"No announcement data returned for course {local_course_id}"
            )
            continue

        raw_announcements = result
        total_raw_count += len(raw_announcements)

        for raw_announcement in raw_announcements:
            try:
                # Extract author name
                author_name = _extract_author_name(raw_announcement)

                # Convert HTML message to Markdown
                message = getattr(raw_announcement, "message", None)
                if message:
                    message = convert_html_to_markdown(message)  # Keep HTML conversion

                # Prepare data for validation
                announcement_data = {
                    "id": raw_announcement.id,  # Alias for canvas_announcement_id
                    "course_id": local_course_id,
                    "title": getattr(
                        raw_announcement, "title", "Untitled Announcement"
                    ),
                    "message": message,  # Alias for content
                    "author_name": author_name,  # Alias for posted_by
                    "posted_at": getattr(raw_announcement, "posted_at", None),
                }

                # Validate using Pydantic model
                db_announcement = DBAnnouncement.model_validate(announcement_data)
                all_valid_announcements.append(db_announcement)
            except Exception as e:
                logger.error(
                    f"Validation error for announcement {getattr(raw_announcement, 'id', 'N/A')} in course {local_course_id}: {e}",
                    exc_info=True,
                )

    logger.info(
        f"Processed {total_raw_count} raw announcements, {len(all_valid_announcements)} valid announcements found."
    )

    # --- Persist Stage ---
    persisted_count = await run_db_persist_in_thread(
        sync_service.db_manager,
        _persist_announcements,
        sync_service,
        all_valid_announcements,
    )

    logger.info(
        f"Finished announcement sync. Persisted/updated {persisted_count} announcements."
    )
    return persisted_count


async def _fetch_announcements_for_course(
    sync_service: "SyncService", canvas_course_id: int, local_course_id: int
) -> list[Any] | None:
    """Helper async function to wrap the threaded API call for announcements."""
    async with sync_service.api_semaphore:
        logger.debug(
            f"Semaphore acquired for fetching announcements: course {local_course_id}"
        )
        try:
            raw_announcements = await asyncio.to_thread(
                sync_service.api_adapter.get_announcements_raw_by_id,
                canvas_course_id,
                per_page=100,
            )
            logger.debug(
                f"Fetched {len(raw_announcements)} announcements for course {local_course_id}"
            )
            return raw_announcements
        except Exception as e:
            logger.error(
                f"Error in thread fetching announcements for course {local_course_id}: {e}",
                exc_info=True,
            )
            return None


def _extract_author_name(raw_announcement) -> str | None:
    """
    Extract author name from announcement data. (Synchronous helper)
    """
    author_dict = getattr(raw_announcement, "author", None)
    if author_dict and isinstance(author_dict, dict) and "display_name" in author_dict:
        return author_dict["display_name"]
    return getattr(raw_announcement, "user_name", None)


def _persist_announcements(
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    sync_service: "SyncService",
    valid_announcements: list[DBAnnouncement],
) -> int:
    """
    Persist announcements in a single transaction using batch operations.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        sync_service: The sync service instance.
        valid_announcements: List of validated announcement models.

    Returns:
        Number of announcements synced/updated.
    """
    if not valid_announcements:
        return 0

    processed_count = 0
    now_iso = datetime.now().isoformat()

    # 1. Fetch existing announcement IDs
    existing_map: dict[
        tuple[int, int], int
    ] = {}  # (canvas_announcement_id, course_id) -> local_id
    canvas_ids_in_batch = {a.canvas_announcement_id for a in valid_announcements}
    course_ids_in_batch = {a.course_id for a in valid_announcements}
    try:
        if canvas_ids_in_batch and course_ids_in_batch:
            canvas_phs = ",".join("?" * len(canvas_ids_in_batch))
            course_phs = ",".join("?" * len(course_ids_in_batch))
            sql = f"SELECT id, canvas_announcement_id, course_id FROM announcements WHERE canvas_announcement_id IN ({canvas_phs}) AND course_id IN ({course_phs})"
            params = list(canvas_ids_in_batch) + list(course_ids_in_batch)
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                existing_map[(row["canvas_announcement_id"], row["course_id"])] = row[
                    "id"
                ]
    except sqlite3.Error as e:
        logger.error(f"Failed to query existing announcements: {e}")
        raise

    # 2. Prepare data
    insert_data = []
    update_data = []
    for db_announcement in valid_announcements:
        item_dict = db_announcement.model_dump(exclude={"created_at", "updated_at"})
        item_dict["updated_at"] = now_iso
        # Handle aliases
        item_dict["content"] = item_dict.pop("message", db_announcement.content)
        item_dict["posted_by"] = item_dict.pop("author_name", db_announcement.posted_by)

        key = (db_announcement.canvas_announcement_id, db_announcement.course_id)
        if key in existing_map:
            item_dict["local_id"] = existing_map[key]
            update_data.append(item_dict)
        else:
            insert_tuple = (
                item_dict.get("course_id"),
                item_dict.get("canvas_announcement_id"),
                item_dict.get("title"),
                item_dict.get("content"),
                item_dict.get("posted_by"),
                item_dict.get("posted_at"),
                item_dict.get("updated_at"),
            )
            insert_data.append(insert_tuple)

    # 3. Batch insert
    if insert_data:
        cols = "course_id, canvas_announcement_id, title, content, posted_by, posted_at, updated_at"
        phs = ", ".join(["?"] * len(insert_data[0]))
        sql = f"INSERT INTO announcements ({cols}) VALUES ({phs})"
        try:
            cursor.executemany(sql, insert_data)
            processed_count += cursor.rowcount
            logger.debug(f"Batch inserted {cursor.rowcount} announcements.")
        except sqlite3.Error as e:
            logger.error(f"Batch announcement insert failed: {e}")
            raise

    # 4. Looped update
    update_count = 0
    if update_data:
        logger.debug(f"Updating {len(update_data)} announcements individually...")
        for item_dict in update_data:
            local_id = item_dict.pop("local_id")
            canvas_id = item_dict.get("canvas_announcement_id")
            course_id = item_dict.get("course_id")
            try:
                set_clause = ", ".join(
                    [
                        f"{k} = ?"
                        for k in item_dict
                        if k not in ["canvas_announcement_id", "course_id"]
                    ]
                )
                values = [
                    v
                    for k, v in item_dict.items()
                    if k not in ["canvas_announcement_id", "course_id"]
                ]
                values.append(local_id)
                sql = f"UPDATE announcements SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                update_count += cursor.rowcount
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to update announcement {canvas_id} (local ID {local_id}) in course {course_id}: {e}"
                )
    processed_count += update_count
    logger.debug(f"Updated {update_count} announcements.")

    return processed_count
