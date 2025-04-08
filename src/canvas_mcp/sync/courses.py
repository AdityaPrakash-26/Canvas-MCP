"""
Canvas Courses Sync

This module provides functionality for synchronizing course data between
the Canvas API and the local database.
"""

import logging
from datetime import datetime
from typing import Any

from canvas_mcp.models import DBCourse
from canvas_mcp.utils.content_utils import detect_content_type
from canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)


def sync_courses(
    self, user_id: str | None = None, term_id: int | None = -1
) -> list[int]:
    """
    Synchronize course data from Canvas to the local database.

    Args:
        user_id: Optional user ID to filter courses
        term_id: Optional term ID to filter courses
                 (default is -1, which selects only the most recent term)

    Returns:
        List of local course IDs that were synced
    """
    if not self.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return []

    # Fetch Stage
    user = self.api_adapter.get_current_user_raw()
    if not user:
        logger.error("Failed to get current user from Canvas API")
        return []

    # Use the provided user_id or get it from the current user
    if user_id is None:
        user_id = str(user.id)

    # Get courses from Canvas
    raw_courses = self.api_adapter.get_courses_raw(user)
    if not raw_courses:
        logger.warning("No courses found in Canvas API")
        return []

    # Filter Stage
    filtered_courses = self._filter_courses_by_term(raw_courses, term_id)
    if not filtered_courses:
        logger.warning("No courses found after term filtering")
        return []

    # Prepare/Validate Stage
    valid_courses = []
    for raw_course in filtered_courses:
        try:
            # Get detailed course info if needed
            detailed_course = self.api_adapter.get_course_raw(raw_course.id)

            # Combine data for validation
            course_data = {
                "id": raw_course.id,
                "course_code": getattr(raw_course, "course_code", ""),
                "name": getattr(raw_course, "name", ""),
                "instructor": getattr(detailed_course, "teacher_name", None)
                if detailed_course
                else None,
                "description": getattr(detailed_course, "description", None)
                if detailed_course
                else None,
                "start_at": getattr(raw_course, "start_at", None),
                "end_at": getattr(raw_course, "end_at", None),
            }

            # Validate using Pydantic model
            db_course = DBCourse.model_validate(course_data)

            # Get syllabus body if available
            syllabus_body = (
                getattr(detailed_course, "syllabus_body", None)
                if detailed_course
                else None
            )

            valid_courses.append((db_course, syllabus_body))
        except Exception as e:
            logger.error(
                f"Error validating course {getattr(raw_course, 'id', 'unknown')}: {e}"
            )

    if not valid_courses:
        logger.warning("No valid courses found after validation")
        return []

    # Persist courses and syllabi using the with_connection decorator
    return self._persist_courses_and_syllabi(valid_courses)


def _filter_courses_by_term(
    self, courses: list[Any], term_id: int | None = -1
) -> list[Any]:
    """
    Filter courses by term ID.

    Args:
        courses: List of Canvas course objects
        term_id: Term ID to filter by (-1 for most recent term)

    Returns:
        Filtered list of courses
    """
    if term_id is None or term_id != -1:
        return courses

    # Get the most recent term (maximum term_id)
    term_ids = [getattr(course, "enrollment_term_id", 0) for course in courses]
    if not term_ids:
        return courses

    max_term_id = max(filter(lambda x: x is not None, term_ids), default=None)
    if max_term_id is None:
        return courses

    logger.info(f"Filtering to only include the most recent term (ID: {max_term_id})")
    return [
        course
        for course in courses
        if getattr(course, "enrollment_term_id", None) == max_term_id
    ]


def _persist_courses_and_syllabi(self, conn, cursor, valid_courses) -> list[int]:
    """
    Persist courses and syllabi in a single transaction.

    Args:
        conn: Database connection
        cursor: Database cursor
        valid_courses: List of validated course data tuples (DBCourse, syllabus_body)

    Returns:
        List of local course IDs that were synced
    """
    local_ids = []
    canvas_to_local_id = {}

    # Persist courses
    for db_course, syllabus_body in valid_courses:
        try:
            # Convert Pydantic model to dict
            course_dict = db_course.model_dump(exclude={"created_at", "updated_at"})
            course_dict["updated_at"] = datetime.now().isoformat()

            # Check if course exists
            cursor.execute(
                "SELECT id FROM courses WHERE canvas_course_id = ?",
                (db_course.canvas_course_id,),
            )
            existing_course = cursor.fetchone()

            if existing_course:
                # Update existing course
                placeholders = ", ".join([f"{key} = ?" for key in course_dict.keys()])
                query = f"UPDATE courses SET {placeholders} WHERE canvas_course_id = ?"
                cursor.execute(
                    query, list(course_dict.values()) + [db_course.canvas_course_id]
                )
                local_id = existing_course["id"]
            else:
                # Insert new course
                columns = ", ".join(course_dict.keys())
                placeholders = ", ".join(["?" for _ in course_dict.keys()])
                query = f"INSERT INTO courses ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(course_dict.values()))
                local_id = cursor.lastrowid

            local_ids.append(local_id)
            canvas_to_local_id[db_course.canvas_course_id] = local_id

            # Persist syllabus in the same transaction
            if syllabus_body is not None:
                content_type = detect_content_type(syllabus_body)

                # Check if syllabus exists
                cursor.execute(
                    "SELECT id FROM syllabi WHERE course_id = ?", (local_id,)
                )
                existing_syllabus = cursor.fetchone()

                syllabus_dict = {
                    "course_id": local_id,
                    "content": syllabus_body,
                    "content_type": content_type,
                    "is_parsed": False,
                    "updated_at": datetime.now().isoformat(),
                }

                if existing_syllabus:
                    # Update existing syllabus
                    placeholders = ", ".join(
                        [f"{key} = ?" for key in syllabus_dict.keys()]
                    )
                    query = f"UPDATE syllabi SET {placeholders} WHERE course_id = ?"
                    cursor.execute(query, list(syllabus_dict.values()) + [local_id])
                else:
                    # Insert new syllabus
                    columns = ", ".join(syllabus_dict.keys())
                    placeholders = ", ".join(["?" for _ in syllabus_dict.keys()])
                    query = f"INSERT INTO syllabi ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(syllabus_dict.values()))
        except Exception as e:
            logger.error(f"Error persisting course {db_course.canvas_course_id}: {e}")
            # The decorator will handle rollback

    return local_ids
