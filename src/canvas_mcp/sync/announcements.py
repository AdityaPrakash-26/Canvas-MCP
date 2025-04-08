"""
Canvas Announcements Sync

This module provides functionality for synchronizing announcement data between
the Canvas API and the local database.
"""

import logging
from datetime import datetime

from canvas_mcp.models import DBAnnouncement

# Configure logging
logger = logging.getLogger(__name__)


def sync_announcements(sync_service, course_ids: list[int] | None = None) -> int:
    """
    Synchronize announcement data from Canvas to the local database.

    Args:
        course_ids: Optional list of local course IDs to sync

    Returns:
        Number of announcements synced
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return 0

    # Get courses to sync
    conn, cursor = sync_service.db_manager.connect()
    try:
        if course_ids is None:
            # Get all courses
            cursor.execute("SELECT * FROM courses")
            courses_to_sync = [dict(row) for row in cursor.fetchall()]
        else:
            # Get specific courses
            courses_to_sync = []
            for course_id in course_ids:
                cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
                course = cursor.fetchone()
                if course:
                    courses_to_sync.append(dict(course))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting courses to sync: {e}")
        return 0
    finally:
        conn.close()

    if not courses_to_sync:
        logger.warning("No courses found to sync announcements")
        return 0

    # Process each course
    announcement_count = 0

    for course in courses_to_sync:
        local_course_id = course["id"]
        canvas_course_id = course["canvas_course_id"]

        logger.info(
            f"Syncing announcements for course {canvas_course_id} (local ID: {local_course_id})"
        )

        # Fetch Stage
        canvas_course = sync_service.api_adapter.get_course_raw(canvas_course_id)
        if not canvas_course:
            logger.error(f"Failed to get course {canvas_course_id} from Canvas API")
            continue

        raw_announcements = sync_service.api_adapter.get_announcements_raw(
            canvas_course
        )
        if not raw_announcements:
            logger.info(f"No announcements found for course {canvas_course_id}")
            continue

        # Prepare/Validate Stage
        valid_announcements = []

        for raw_announcement in raw_announcements:
            try:
                # Prepare data for validation
                # Get author information from the author dictionary or fallback to user_name
                author_name = None
                author_dict = getattr(raw_announcement, "author", None)
                if author_dict and isinstance(author_dict, dict):
                    author_name = author_dict.get("display_name")

                if not author_name:
                    author_name = getattr(raw_announcement, "user_name", None)

                announcement_data = {
                    "id": raw_announcement.id,
                    "course_id": local_course_id,
                    "title": getattr(raw_announcement, "title", ""),
                    "message": getattr(raw_announcement, "message", None),
                    "author_name": author_name,
                    "posted_at": getattr(raw_announcement, "posted_at", None),
                }

                # Validate using Pydantic model
                db_announcement = DBAnnouncement.model_validate(announcement_data)
                valid_announcements.append(db_announcement)
            except Exception as e:
                logger.error(
                    f"Error validating announcement {getattr(raw_announcement, 'id', 'unknown')}: {e}"
                )

        # Persist announcements
        conn, cursor = sync_service.db_manager.connect()
        try:
            synced = _persist_announcements(
                sync_service, conn, cursor, local_course_id, valid_announcements
            )
            conn.commit()
            announcement_count += synced
        except Exception as e:
            conn.rollback()
            logger.error(f"Error persisting announcements: {e}")
        finally:
            conn.close()

        logger.info(f"Successfully synced announcements for course {canvas_course_id}")

    return announcement_count


def _persist_announcements(
    sync_service,
    conn,
    cursor,
    local_course_id: int,
    valid_announcements: list[DBAnnouncement],
) -> int:
    """
    Persist announcements in a single transaction.

    Args:
        conn: Database connection
        cursor: Database cursor
        local_course_id: Local course ID
        valid_announcements: List of validated announcement models

    Returns:
        Number of announcements synced
    """
    announcement_count = 0

    for db_announcement in valid_announcements:
        try:
            # Convert Pydantic model to dict
            announcement_dict = db_announcement.model_dump(
                exclude={"created_at", "updated_at"}
            )
            announcement_dict["updated_at"] = datetime.now().isoformat()

            # Check if announcement exists
            cursor.execute(
                "SELECT id FROM announcements WHERE course_id = ? AND canvas_announcement_id = ?",
                (local_course_id, db_announcement.canvas_announcement_id),
            )
            existing_announcement = cursor.fetchone()

            if existing_announcement:
                # Update existing announcement
                placeholders = ", ".join(
                    [f"{key} = ?" for key in announcement_dict.keys()]
                )
                query = f"UPDATE announcements SET {placeholders} WHERE course_id = ? AND canvas_announcement_id = ?"
                cursor.execute(
                    query,
                    list(announcement_dict.values())
                    + [local_course_id, db_announcement.canvas_announcement_id],
                )
            else:
                # Insert new announcement
                columns = ", ".join(announcement_dict.keys())
                placeholders = ", ".join(["?" for _ in announcement_dict.keys()])
                query = f"INSERT INTO announcements ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(announcement_dict.values()))

            announcement_count += 1
        except Exception as e:
            logger.error(
                f"Error persisting announcement {db_announcement.canvas_announcement_id}: {e}"
            )
            # The decorator will handle rollback

    return announcement_count
