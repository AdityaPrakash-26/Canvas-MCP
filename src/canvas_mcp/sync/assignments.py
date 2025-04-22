"""
Canvas Assignments Sync

This module provides functionality for synchronizing assignment data between
the Canvas API and the local database asynchronously.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

from canvas_mcp.models import DBAssignment
from canvas_mcp.sync.all import (
    _get_assignment_type,  # Keep using the helper from all.py
)
from canvas_mcp.utils.db_manager import run_db_persist_in_thread
from canvas_mcp.utils.formatters import convert_html_to_markdown

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService

# Configure logging
logger = logging.getLogger(__name__)


async def sync_assignments(
    sync_service: "SyncService", course_ids: list[int] | None = None
) -> int:
    """
    Synchronize assignment data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        course_ids: List of local course IDs to sync assignments for.

    Returns:
        Number of assignments synced/updated.
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available for assignment sync")
        return 0
    if not course_ids:
        logger.warning("No course IDs provided for assignment sync.")
        return 0

    # Get course mapping (canvas_id -> local_id)
    # This could be fetched once in sync_all and passed down if performance is critical
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
        logger.error(f"Failed to fetch course mapping for assignments: {e}")
        return 0
    finally:
        conn_map.close()

    if not courses_to_sync:
        logger.warning("No matching courses found in DB for assignment sync.")
        return 0

    # --- Parallel Fetch Stage ---
    tasks = []
    course_context = []  # Store (local_id, canvas_id) for context

    logger.info(
        f"Creating tasks to fetch assignments for {len(courses_to_sync)} courses..."
    )
    for canvas_course_id, local_course_id in courses_to_sync.items():
        task = asyncio.create_task(
            _fetch_assignments_for_course(
                sync_service, canvas_course_id, local_course_id
            )
        )
        tasks.append(task)
        course_context.append((local_course_id, canvas_course_id))

    logger.info(f"Gathering assignment data for {len(tasks)} tasks...")
    results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Finished gathering assignment data.")

    # --- Process & Validate Stage ---
    all_valid_assignments: list[DBAssignment] = []
    total_raw_count = 0
    for i, result in enumerate(results_or_exceptions):
        local_course_id, canvas_course_id = course_context[i]
        if isinstance(result, Exception):
            logger.error(
                f"Failed fetching assignments for course {local_course_id} (Canvas ID: {canvas_course_id}): {result}"
            )
            continue
        if result is None:  # Handle cases where _fetch returns None on error
            logger.warning(f"No assignment data returned for course {local_course_id}")
            continue

        raw_assignments = result
        total_raw_count += len(raw_assignments)

        for raw_assignment in raw_assignments:
            try:
                # Convert submission_types to string
                submission_types = getattr(raw_assignment, "submission_types", [])
                if isinstance(submission_types, list):
                    submission_types = ",".join(submission_types)

                # Determine assignment type using the helper
                assignment_type = _get_assignment_type(sync_service, raw_assignment)

                # Convert HTML description to Markdown
                description = getattr(raw_assignment, "description", None)
                if description:
                    description = convert_html_to_markdown(
                        description
                    )  # Keep HTML conversion

                # Prepare data for validation
                assignment_data = {
                    "id": raw_assignment.id,  # Alias for canvas_assignment_id
                    "course_id": local_course_id,
                    "name": getattr(
                        raw_assignment, "name", "Untitled Assignment"
                    ),  # Alias for title
                    "description": description,
                    "assignment_type": assignment_type,
                    "due_at": getattr(
                        raw_assignment, "due_at", None
                    ),  # Alias for due_date
                    "unlock_at": getattr(
                        raw_assignment, "unlock_at", None
                    ),  # Alias for available_from
                    "lock_at": getattr(
                        raw_assignment, "lock_at", None
                    ),  # Alias for available_until
                    "points_possible": getattr(raw_assignment, "points_possible", None),
                    "submission_types": submission_types,
                    "source_type": "canvas",  # Assuming all synced are from canvas
                }

                # Validate using Pydantic model
                db_assignment = DBAssignment.model_validate(assignment_data)
                all_valid_assignments.append(db_assignment)
            except Exception as e:
                logger.error(
                    f"Validation error for assignment {getattr(raw_assignment, 'id', 'N/A')} in course {local_course_id}: {e}",
                    exc_info=True,
                )

    logger.info(
        f"Processed {total_raw_count} raw assignments, {len(all_valid_assignments)} valid assignments found."
    )

    # --- Persist Stage ---
    persisted_count = await run_db_persist_in_thread(
        sync_service.db_manager,
        _persist_assignments,  # The synchronous persistence function
        sync_service,  # Pass sync_service instance
        all_valid_assignments,  # Pass the list of validated Pydantic models
    )

    logger.info(
        f"Finished assignment sync. Persisted/updated {persisted_count} assignments."
    )
    return persisted_count


async def _fetch_assignments_for_course(
    sync_service: "SyncService", canvas_course_id: int, local_course_id: int
) -> list[Any] | None:
    """Helper async function to wrap the threaded API call with semaphore."""
    async with sync_service.api_semaphore:  # Limit concurrency here
        logger.debug(
            f"Semaphore acquired for fetching assignments: course {local_course_id}"
        )
        try:
            # Run the blocking API call in a thread
            raw_assignments = await asyncio.to_thread(
                sync_service.api_adapter.get_assignments_raw_by_id,  # Use the _by_id adapter method
                canvas_course_id,
                per_page=100,  # Include pagination
            )
            logger.debug(
                f"Fetched {len(raw_assignments)} assignments for course {local_course_id}"
            )
            return raw_assignments
        except Exception as e:
            logger.error(
                f"Error in thread fetching assignments for course {local_course_id}: {e}",
                exc_info=True,
            )
            return None  # Return None on error to be handled by gather loop
        # Semaphore released automatically


def _persist_assignments(
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    sync_service: "SyncService",  # Added sync_service param
    valid_assignments: list[DBAssignment],
) -> int:
    """
    Persist assignments and related calendar events in a single transaction using batch operations.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        sync_service: The sync service instance.
        valid_assignments: List of validated assignment models.

    Returns:
        Number of assignments synced/updated.
    """
    if not valid_assignments:
        return 0

    processed_assignment_count = 0
    now_iso = datetime.now().isoformat()

    # --- Assignment Persistence ---

    # 1. Fetch existing assignment IDs efficiently
    existing_assignments_map: dict[
        tuple[int, int], int
    ] = {}  # (canvas_assignment_id, course_id) -> local_assignment_id
    canvas_ids_in_batch = {a.canvas_assignment_id for a in valid_assignments}
    course_ids_in_batch = {
        a.course_id for a in valid_assignments
    }  # Should usually be just one course_id if called per course, but handle multiple

    try:
        if canvas_ids_in_batch and course_ids_in_batch:
            canvas_placeholders = ",".join("?" * len(canvas_ids_in_batch))
            course_placeholders = ",".join("?" * len(course_ids_in_batch))
            sql = f"""
                SELECT id, canvas_assignment_id, course_id
                FROM assignments
                WHERE canvas_assignment_id IN ({canvas_placeholders}) AND course_id IN ({course_placeholders})
            """
            params = list(canvas_ids_in_batch) + list(course_ids_in_batch)
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                existing_assignments_map[
                    (row["canvas_assignment_id"], row["course_id"])
                ] = row["id"]
    except sqlite3.Error as e:
        logger.error(f"Failed to query existing assignments: {e}")
        raise  # Propagate error to trigger rollback

    # 2. Prepare data for batch insert and update
    assignments_to_insert_data = []
    assignments_to_update_data = []
    assignment_local_id_map = {}  # canvas_id -> local_id (needed for calendar events)

    for db_assignment in valid_assignments:
        assignment_dict = db_assignment.model_dump(exclude={"created_at", "updated_at"})
        assignment_dict["updated_at"] = now_iso
        # Use aliases from model for DB columns if needed, e.g., name -> title
        assignment_dict["title"] = assignment_dict.pop("name", db_assignment.title)
        assignment_dict["due_date"] = assignment_dict.pop(
            "due_at", db_assignment.due_date
        )
        assignment_dict["available_from"] = assignment_dict.pop(
            "unlock_at", db_assignment.available_from
        )
        assignment_dict["available_until"] = assignment_dict.pop(
            "lock_at", db_assignment.available_until
        )

        key = (db_assignment.canvas_assignment_id, db_assignment.course_id)
        if key in existing_assignments_map:
            local_id = existing_assignments_map[key]
            assignment_dict["local_id"] = (
                local_id  # Add local_id for update WHERE clause
            )
            assignments_to_update_data.append(assignment_dict)
            assignment_local_id_map[db_assignment.canvas_assignment_id] = local_id
        else:
            # Prepare tuple for INSERT (ensure order matches columns)
            insert_tuple = (
                assignment_dict.get("course_id"),
                assignment_dict.get("canvas_assignment_id"),
                assignment_dict.get("title"),
                assignment_dict.get("description"),
                assignment_dict.get("due_date"),
                assignment_dict.get("points_possible"),
                assignment_dict.get("assignment_type"),
                assignment_dict.get("submission_types"),
                assignment_dict.get("source_type"),
                assignment_dict.get("available_from"),
                assignment_dict.get("available_until"),
                assignment_dict.get("updated_at"),
            )
            assignments_to_insert_data.append(insert_tuple)
            # We'll map canvas_id to local_id after insert

    # 3. Execute batch assignment insert
    inserted_assignment_ids = {}  # canvas_id -> new_local_id
    if assignments_to_insert_data:
        cols = "course_id, canvas_assignment_id, title, description, due_date, points_possible, assignment_type, submission_types, source_type, available_from, available_until, updated_at"
        phs = ", ".join(["?"] * len(assignments_to_insert_data[0]))
        sql = f"INSERT INTO assignments ({cols}) VALUES ({phs})"
        try:
            cursor.executemany(sql, assignments_to_insert_data)
            inserted_count = cursor.rowcount
            processed_assignment_count += inserted_count
            logger.debug(f"Batch inserted {inserted_count} assignments.")
            # Get local IDs for newly inserted assignments
            last_row_id = cursor.lastrowid
            first_new_id = last_row_id - inserted_count + 1
            for i, data_tuple in enumerate(assignments_to_insert_data):
                canvas_id = data_tuple[1]  # canvas_assignment_id is the second element
                new_local_id = first_new_id + i
                inserted_assignment_ids[canvas_id] = new_local_id
                assignment_local_id_map[canvas_id] = (
                    new_local_id  # Add to map for calendar events
                )
        except sqlite3.IntegrityError as e:
            # Handle potential unique constraint violations if UNIQUE index is added
            logger.warning(
                f"Integrity error during batch assignment insert (likely duplicate): {e}"
            )
            # Need more robust handling here - potentially retry individually or skip duplicates
            # For now, we log and continue, which might lead to inaccurate counts.
        except sqlite3.Error as e:
            logger.error(f"Batch assignment insert failed: {e}")
            raise  # Trigger rollback

    # 4. Execute looped assignment update
    update_count = 0
    if assignments_to_update_data:
        logger.debug(
            f"Updating {len(assignments_to_update_data)} assignments individually..."
        )
        for item_dict in assignments_to_update_data:
            local_id = item_dict.pop("local_id")
            canvas_id = item_dict.get("canvas_assignment_id")  # Keep for logging
            course_id = item_dict.get("course_id")
            try:
                set_clause = ", ".join(
                    [
                        f"{k} = ?"
                        for k in item_dict
                        if k not in ["canvas_assignment_id", "course_id"]
                    ]
                )
                values = [
                    v
                    for k, v in item_dict.items()
                    if k not in ["canvas_assignment_id", "course_id"]
                ]
                values.append(local_id)  # For WHERE clause

                sql = f"UPDATE assignments SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                update_count += cursor.rowcount
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to update assignment {canvas_id} (local ID {local_id}) in course {course_id}: {e}"
                )
                # Decide whether to continue or raise

    processed_assignment_count += update_count
    logger.debug(f"Updated {update_count} assignments.")

    # --- Calendar Event Persistence (Simplified: INSERT OR REPLACE) ---
    # A full batch approach would query existing events first.

    events_to_persist = []
    for db_assignment in valid_assignments:
        local_assignment_id = assignment_local_id_map.get(
            db_assignment.canvas_assignment_id
        )
        if db_assignment.due_date and local_assignment_id:
            event_data = (
                db_assignment.course_id,
                db_assignment.title,
                f"Due date for assignment: {db_assignment.title}",
                db_assignment.assignment_type or "assignment",
                "assignment",
                local_assignment_id,
                db_assignment.due_date.isoformat(),
                now_iso,  # updated_at
            )
            events_to_persist.append(event_data)

    if events_to_persist:
        logger.debug(
            f"Persisting {len(events_to_persist)} calendar events using INSERT OR REPLACE..."
        )
        # Using source_type and source_id as the unique key for replacement
        sql = """
            INSERT OR REPLACE INTO calendar_events
            (course_id, title, description, event_type, source_type, source_id, event_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor.executemany(sql, events_to_persist)
            logger.debug(f"Persisted {cursor.rowcount} calendar events.")
        except sqlite3.Error as e:
            logger.error(f"Calendar event persistence failed: {e}")
            # Decide if this should rollback the whole transaction
            raise  # For now, rollback

    return processed_assignment_count
