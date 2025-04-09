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
        sync_service: The sync service instance
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
        courses_to_sync = _get_courses_to_sync(cursor, course_ids)
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

        # Fetch course and announcements
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

        # Process announcements
        valid_announcements = []
        for raw_announcement in raw_announcements:
            try:
                # Extract author name
                author_name = _extract_author_name(raw_announcement)

                # Create announcement data
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
                    f"Error processing announcement {getattr(raw_announcement, 'id', 'unknown')}: {e}"
                )

        # Persist announcements
        if valid_announcements:
            conn, cursor = sync_service.db_manager.connect()
            try:
                synced = _persist_announcements(cursor, valid_announcements)
                conn.commit()
                announcement_count += synced
                logger.info(
                    f"Synced {synced} announcements for course {canvas_course_id}"
                )
            except Exception as e:
                conn.rollback()
                logger.error(f"Error persisting announcements: {e}")
            finally:
                conn.close()

    return announcement_count


def _get_courses_to_sync(cursor, course_ids: list[int] | None = None) -> list[dict]:
    """
    Get courses to sync from the database.

    Args:
        cursor: Database cursor
        course_ids: Optional list of local course IDs to sync

    Returns:
        List of course dictionaries
    """
    if course_ids is None:
        # Get all courses
        cursor.execute("SELECT * FROM courses")
        return [dict(row) for row in cursor.fetchall()]
    else:
        # Get specific courses
        courses_to_sync = []
        for course_id in course_ids:
            cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
            course = cursor.fetchone()
            if course:
                courses_to_sync.append(dict(course))
        return courses_to_sync


def _extract_author_name(raw_announcement) -> str | None:
    """
    Extract author name from announcement data.

    Args:
        raw_announcement: Raw announcement object from Canvas API

    Returns:
        Author name or None if not found
    """
    # Try to get from author dictionary first
    author_dict = getattr(raw_announcement, "author", None)
    if author_dict and isinstance(author_dict, dict) and "display_name" in author_dict:
        return author_dict["display_name"]

    # Fall back to user_name
    return getattr(raw_announcement, "user_name", None)


def _persist_announcements(cursor, valid_announcements: list[DBAnnouncement]) -> int:
    """
    Persist announcements in a single transaction.

    Args:
        cursor: Database cursor
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
                (db_announcement.course_id, db_announcement.canvas_announcement_id),
            )
            existing_announcement = cursor.fetchone()

            if existing_announcement:
                # Update existing announcement
                placeholders = ", ".join([f"{k} = ?" for k in announcement_dict.keys()])
                values = list(announcement_dict.values())

                cursor.execute(
                    f"UPDATE announcements SET {placeholders} WHERE course_id = ? AND canvas_announcement_id = ?",
                    values
                    + [
                        db_announcement.course_id,
                        db_announcement.canvas_announcement_id,
                    ],
                )
            else:
                # Insert new announcement
                columns = ", ".join(announcement_dict.keys())
                placeholders = ", ".join(["?" for _ in announcement_dict.keys()])

                cursor.execute(
                    f"INSERT INTO announcements ({columns}) VALUES ({placeholders})",
                    list(announcement_dict.values()),
                )

            announcement_count += 1
        except Exception as e:
            logger.error(
                f"Error persisting announcement {db_announcement.canvas_announcement_id}: {e}"
            )

    return announcement_count
