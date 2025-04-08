"""
Canvas Assignments Sync

This module provides functionality for synchronizing assignment data between
the Canvas API and the local database.
"""

import logging
from datetime import datetime

from canvas_mcp.models import DBAssignment
from canvas_mcp.sync.all import _get_assignment_type

# Configure logging
logger = logging.getLogger(__name__)


def sync_assignments(sync_service, course_ids: list[int] | None = None) -> int:
    """
    Synchronize assignment data from Canvas to the local database.

    Args:
        course_ids: Optional list of local course IDs to sync

    Returns:
        Number of assignments synced
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return 0

    # Get courses to sync
    conn, cursor = sync_service.db_manager.connect()
    try:
        courses_to_sync = _get_courses_to_sync(sync_service, conn, cursor, course_ids)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting courses to sync: {e}")
        return 0
    finally:
        conn.close()

    if not courses_to_sync:
        logger.warning("No courses found to sync assignments")
        return 0

    # Process each course
    assignment_count = 0

    for course in courses_to_sync:
        local_course_id = course["id"]
        canvas_course_id = course["canvas_course_id"]

        logger.info(
            f"Syncing assignments for course {canvas_course_id} (local ID: {local_course_id})"
        )

        # Fetch Stage
        canvas_course = sync_service.api_adapter.get_course_raw(canvas_course_id)
        if not canvas_course:
            logger.error(f"Failed to get course {canvas_course_id} from Canvas API")
            continue

        raw_assignments = sync_service.api_adapter.get_assignments_raw(canvas_course)
        if not raw_assignments:
            logger.info(f"No assignments found for course {canvas_course_id}")
            continue

        # Prepare/Validate Stage
        valid_assignments = []

        for raw_assignment in raw_assignments:
            try:
                # Convert submission_types to string
                submission_types = getattr(raw_assignment, "submission_types", [])
                if isinstance(submission_types, list):
                    submission_types = ",".join(submission_types)

                # Determine assignment type
                assignment_type = _get_assignment_type(sync_service, raw_assignment)

                # Prepare data for validation
                assignment_data = {
                    "id": raw_assignment.id,
                    "course_id": local_course_id,
                    "name": raw_assignment.name,
                    "description": getattr(raw_assignment, "description", None),
                    "assignment_type": assignment_type,
                    "due_at": getattr(raw_assignment, "due_at", None),
                    "unlock_at": getattr(raw_assignment, "unlock_at", None),
                    "lock_at": getattr(raw_assignment, "lock_at", None),
                    "points_possible": getattr(raw_assignment, "points_possible", None),
                    "submission_types": submission_types,
                }

                # Validate using Pydantic model
                db_assignment = DBAssignment.model_validate(assignment_data)
                valid_assignments.append(db_assignment)
            except Exception as e:
                logger.error(
                    f"Error validating assignment {getattr(raw_assignment, 'id', 'unknown')}: {e}"
                )

        # Persist assignments
        conn, cursor = sync_service.db_manager.connect()
        try:
            synced = _persist_assignments(
                sync_service, conn, cursor, local_course_id, valid_assignments
            )
            conn.commit()
            assignment_count += synced
        except Exception as e:
            conn.rollback()
            logger.error(f"Error persisting assignments: {e}")
        finally:
            conn.close()

        logger.info(f"Successfully synced assignments for course {canvas_course_id}")

    return assignment_count


def _get_courses_to_sync(
    sync_service, conn, cursor, course_ids: list[int] | None = None
) -> list[dict]:
    """
    Get courses to sync from the database.

    Args:
        conn: Database connection
        cursor: Database cursor
        course_ids: Optional list of local course IDs to sync

    Returns:
        List of courses to sync
    """
    courses_to_sync = []

    if course_ids is None:
        # Get all courses
        cursor.execute("SELECT * FROM courses")
        courses_to_sync = [dict(row) for row in cursor.fetchall()]
    else:
        # Get specific courses
        for course_id in course_ids:
            cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
            course = cursor.fetchone()
            if course:
                courses_to_sync.append(dict(course))

    return courses_to_sync


def _persist_assignments(
    sync_service,
    conn,
    cursor,
    local_course_id: int,
    valid_assignments: list[DBAssignment],
) -> int:
    """
    Persist assignments in a single transaction.

    Args:
        conn: Database connection
        cursor: Database cursor
        local_course_id: Local course ID
        valid_assignments: List of validated assignment models

    Returns:
        Number of assignments synced
    """
    assignment_count = 0

    for db_assignment in valid_assignments:
        try:
            # Convert Pydantic model to dict
            assignment_dict = db_assignment.model_dump(
                exclude={"created_at", "updated_at"}
            )
            assignment_dict["updated_at"] = datetime.now().isoformat()

            # Check for duplicate canvas_assignment_id in another course
            cursor.execute(
                "SELECT course_id FROM assignments WHERE canvas_assignment_id = ? AND course_id != ?",
                (db_assignment.canvas_assignment_id, local_course_id),
            )
            existing = cursor.fetchone()

            if existing:
                logger.warning(
                    f"Assignment ID {db_assignment.canvas_assignment_id} already exists in course {existing['course_id']}"
                )
                # Generate a unique ID by appending the course ID
                modified_canvas_id = int(
                    f"{db_assignment.canvas_assignment_id}{local_course_id}"
                )
                logger.info(
                    f"Using modified canvas_assignment_id: {modified_canvas_id}"
                )
                assignment_dict["canvas_assignment_id"] = modified_canvas_id

            # Check if assignment exists
            cursor.execute(
                "SELECT id FROM assignments WHERE course_id = ? AND canvas_assignment_id = ?",
                (local_course_id, assignment_dict["canvas_assignment_id"]),
            )
            existing_assignment = cursor.fetchone()

            if existing_assignment:
                # Update existing assignment
                placeholders = ", ".join(
                    [f"{key} = ?" for key in assignment_dict.keys()]
                )
                query = f"UPDATE assignments SET {placeholders} WHERE course_id = ? AND canvas_assignment_id = ?"
                cursor.execute(
                    query,
                    list(assignment_dict.values())
                    + [local_course_id, assignment_dict["canvas_assignment_id"]],
                )
                local_assignment_id = existing_assignment["id"]
            else:
                # Insert new assignment
                columns = ", ".join(assignment_dict.keys())
                placeholders = ", ".join(["?" for _ in assignment_dict.keys()])
                query = f"INSERT INTO assignments ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(assignment_dict.values()))
                local_assignment_id = cursor.lastrowid

            # Add to calendar events if due date exists
            if db_assignment.due_date:
                # Check if calendar event exists
                cursor.execute(
                    "SELECT id FROM calendar_events WHERE source_type = 'assignment' AND source_id = ?",
                    (local_assignment_id,),
                )
                existing_event = cursor.fetchone()

                calendar_dict = {
                    "course_id": local_course_id,
                    "title": db_assignment.title,
                    "description": f"Due date for assignment: {db_assignment.title}",
                    "event_type": db_assignment.assignment_type or "assignment",
                    "source_type": "assignment",
                    "source_id": local_assignment_id,
                    "event_date": db_assignment.due_date.isoformat()
                    if db_assignment.due_date
                    else None,
                    "updated_at": datetime.now().isoformat(),
                }

                if existing_event:
                    # Update existing calendar event
                    placeholders = ", ".join(
                        [f"{key} = ?" for key in calendar_dict.keys()]
                    )
                    query = f"UPDATE calendar_events SET {placeholders} WHERE source_type = 'assignment' AND source_id = ?"
                    cursor.execute(
                        query, list(calendar_dict.values()) + [local_assignment_id]
                    )
                else:
                    # Insert new calendar event
                    columns = ", ".join(calendar_dict.keys())
                    placeholders = ", ".join(["?" for _ in calendar_dict.keys()])
                    query = f"INSERT INTO calendar_events ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(calendar_dict.values()))

            assignment_count += 1
        except Exception as e:
            logger.error(
                f"Error persisting assignment {db_assignment.canvas_assignment_id}: {e}"
            )
            # The decorator will handle rollback

    return assignment_count
