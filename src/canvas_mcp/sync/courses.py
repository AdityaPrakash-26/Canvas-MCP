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

# Configure logging
logger = logging.getLogger(__name__)


def sync_courses(
    sync_service, user_id: str | None = None, term_id: int | None = -1
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
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return []

    # Fetch Stage
    user = sync_service.api_adapter.get_current_user_raw()
    if not user:
        logger.error("Failed to get current user from Canvas API")
        return []

    # Use the provided user_id or get it from the current user
    if user_id is None:
        user_id = str(user.id)

    # Get courses from Canvas
    raw_courses = sync_service.api_adapter.get_courses_raw(user)
    if not raw_courses:
        logger.warning("No courses found in Canvas API")
        return []

    # Filter Stage
    filtered_courses = _filter_courses_by_term(raw_courses, term_id)
    if not filtered_courses:
        logger.warning("No courses found after term filtering")
        return []

    # Prepare/Validate Stage
    valid_courses = []
    canvas_course_ids = []  # Track Canvas course IDs for cleanup

    for raw_course in filtered_courses:
        try:
            # Normalize Canvas course ID by removing any prefix
            canvas_id = getattr(raw_course, "id", 0)
            # Store the original Canvas ID for tracking
            canvas_course_ids.append(canvas_id)

            # Get detailed course info if needed
            detailed_course = sync_service.api_adapter.get_course_raw(canvas_id)

            # Combine data for validation
            course_data = {
                "id": canvas_id,
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

    # Persist courses and syllabi
    conn, cursor = sync_service.db_manager.connect()
    try:
        # First, clean up courses that are no longer active or in the current term
        if canvas_course_ids:
            # Convert list to string for SQL IN clause
            canvas_ids_str = ", ".join([str(cid) for cid in canvas_course_ids])
            # Find courses in the database that are not in the current active set
            cursor.execute(
                f"SELECT id, canvas_course_id FROM courses WHERE canvas_course_id NOT IN ({canvas_ids_str})"
            )
            courses_to_remove = cursor.fetchall()

            if courses_to_remove:
                logger.info(
                    f"Removing {len(courses_to_remove)} courses that are no longer active or in the current term"
                )
                for course in courses_to_remove:
                    logger.info(
                        f"Removing course with ID {course['id']} (Canvas ID: {course['canvas_course_id']})"
                    )
                    cursor.execute("DELETE FROM courses WHERE id = ?", (course["id"],))

        # Now persist the current courses
        result = _persist_courses_and_syllabi(cursor, valid_courses)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        logger.error(f"Error persisting courses: {e}")
        return []
    finally:
        conn.close()


def _filter_courses_by_term(courses: list[Any], term_id: int | None = -1) -> list[Any]:
    """
    Filter courses by term ID.

    Args:
        courses: List of Canvas course objects
        term_id: Term ID to filter by (-1 for most recent term, None for no filtering)

    Returns:
        Filtered list of courses
    """
    # If term_id is None, don't filter by term
    if term_id is None:
        return courses

    # If term_id is -1, filter by the most recent term
    if term_id == -1:
        # Get all term IDs from courses
        term_ids = []
        for course in courses:
            term_id = getattr(course, "enrollment_term_id", None)
            if term_id is not None:
                term_ids.append(term_id)

        if not term_ids:
            logger.warning("No term IDs found in courses, returning all courses")
            return courses

        # Find the maximum term ID (most recent term)
        max_term_id = max(term_ids)
        logger.info(
            f"Filtering to only include the most recent term (ID: {max_term_id})"
        )

        # Filter courses by the most recent term
        return [
            course
            for course in courses
            if getattr(course, "enrollment_term_id", None) == max_term_id
        ]

    # If term_id is a specific value, filter by that term
    logger.info(f"Filtering to only include term with ID: {term_id}")
    return [
        course
        for course in courses
        if getattr(course, "enrollment_term_id", None) == term_id
    ]


def _persist_courses_and_syllabi(cursor, valid_courses) -> list[int]:
    """
    Persist courses and syllabi in a single transaction.

    Args:
        cursor: Database cursor
        valid_courses: List of validated course data tuples (DBCourse, syllabus_body)

    Returns:
        List of local course IDs that were synced
    """
    local_ids = []
    canvas_to_local_id = {}
    fetched_canvas_ids = set() # Keep track of canvas_ids from the current sync

    # Persist courses and syllabi first
    for db_course, syllabus_body in valid_courses:
        try:
            # Add the canvas_id to our set of fetched IDs
            fetched_canvas_ids.add(db_course.canvas_course_id)

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
            # Let the main sync function handle rollback on exception

    # After successfully upserting all current courses, handle deletions
    # Get all canvas_course_ids currently in the database
    cursor.execute("SELECT canvas_course_id FROM courses")
    db_canvas_ids = {row["canvas_course_id"] for row in cursor.fetchall()}

    # Determine which courses to remove (in DB but not in the fetched set)
    ids_to_remove = db_canvas_ids - fetched_canvas_ids

    if ids_to_remove:
        logger.info(
            f"Removing {len(ids_to_remove)} courses that are no longer active or in the current term/filter"
        )
        # Create placeholders for the IN clause
        placeholders = ", ".join(["?" for _ in ids_to_remove])
        cursor.execute(
            f"DELETE FROM courses WHERE canvas_course_id IN ({placeholders})",
            list(ids_to_remove),
        )
        # Log which courses are being removed
        for canvas_id in ids_to_remove:
             logger.info(f"Removing course with Canvas ID: {canvas_id}")

    return local_ids