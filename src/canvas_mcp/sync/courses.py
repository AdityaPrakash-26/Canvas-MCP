"""
Canvas Courses Sync

This module provides functionality for synchronizing course data between
the Canvas API and the local database asynchronously.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

from canvas_mcp.models import DBCourse, DBSyllabus
from canvas_mcp.utils.content_utils import detect_content_type
from canvas_mcp.utils.db_manager import run_db_persist_in_thread
from canvas_mcp.utils.formatters import convert_html_to_markdown

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService

# Configure logging
logger = logging.getLogger(__name__)


async def sync_courses(
    sync_service: "SyncService", user_id: str | None = None, term_id: int | None = -1
) -> list[int]:
    """
    Synchronize course data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        user_id: Optional user ID to filter courses.
        term_id: Optional term ID to filter courses
                 (default is -1, which selects only the most recent term).

    Returns:
        List of local course IDs that were synced/updated.
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available for course sync")
        return []

    # Fetch Stage (Run blocking API calls in threads)
    logger.info("Fetching current user from Canvas API...")
    user = await asyncio.to_thread(sync_service.api_adapter.get_current_user_raw)
    if not user:
        logger.error("Failed to get current user from Canvas API")
        return []

    # Use the provided user_id or get it from the current user
    canvas_user_id = str(user.id) if user_id is None else user_id
    logger.info(f"Fetching courses for user {canvas_user_id}...")

    # Fetch courses with pagination
    raw_courses = await asyncio.to_thread(
        sync_service.api_adapter.get_courses_raw, user, per_page=100
    )
    if not raw_courses:
        logger.warning("No courses found in Canvas API for user")
        return []
    logger.info(f"Fetched {len(raw_courses)} raw courses from Canvas.")

    # Filter Stage (Synchronous logic)
    filtered_courses = _filter_courses_by_term(raw_courses, term_id)
    if not filtered_courses:
        logger.warning("No courses found after term filtering")
        # Run cleanup even if no courses match the filter
        await run_db_persist_in_thread(
            sync_service.db_manager,
            _persist_courses_and_syllabi,
            sync_service,
            [],  # Pass empty list to trigger cleanup
        )
        return []
    logger.info(
        f"Filtered down to {len(filtered_courses)} courses for the target term."
    )

    # Prepare/Validate Stage (Fetch details concurrently)
    logger.info("Fetching detailed course info and syllabi concurrently...")
    tasks = []
    for raw_course in filtered_courses:
        canvas_id = getattr(raw_course, "id", 0)
        if canvas_id:
            tasks.append(
                asyncio.create_task(_fetch_course_details(sync_service, raw_course))
            )

    results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

    valid_courses_data: list[tuple[DBCourse, str | None]] = []
    for i, result in enumerate(results_or_exceptions):
        original_raw_course = filtered_courses[i]  # Assuming order is preserved
        if isinstance(result, Exception):
            logger.error(
                f"Failed fetching details for course {getattr(original_raw_course, 'id', 'N/A')}: {result}"
            )
            continue
        if result:  # result is (db_course, syllabus_body) or None
            valid_courses_data.append(result)

    if not valid_courses_data:
        logger.warning("No valid courses found after fetching details and validation")
        # Run cleanup even if validation fails for all
        await run_db_persist_in_thread(
            sync_service.db_manager,
            _persist_courses_and_syllabi,
            sync_service,
            [],  # Pass empty list to trigger cleanup
        )
        return []
    logger.info(f"Validated {len(valid_courses_data)} courses.")

    # Persist courses and syllabi using the helper
    # Pass the validated data (list of tuples) directly
    persisted_count = await run_db_persist_in_thread(
        sync_service.db_manager,
        _persist_courses_and_syllabi,
        sync_service,
        valid_courses_data,  # Pass the list of tuples
    )

    # The persistence function now returns the list of local IDs
    # We assume run_db_persist_in_thread is modified or _persist_... returns the IDs
    # For now, let's assume persisted_count holds the list of local_ids
    if isinstance(persisted_count, list):
        logger.info(
            f"Persisted/updated {len(persisted_count)} courses and their syllabi."
        )
        return persisted_count
    else:
        logger.error(
            f"Persistence function did not return a list of IDs. Got: {persisted_count}"
        )
        # Fallback: return IDs from the validated data (might be inaccurate if persistence failed partially)
        return [vc[0].canvas_course_id for vc in valid_courses_data]


async def _fetch_course_details(
    sync_service: "SyncService", raw_course: Any
) -> tuple[DBCourse, str | None] | None:
    """Fetches detailed course info and syllabus body asynchronously."""
    canvas_id = getattr(raw_course, "id", 0)
    if not canvas_id:
        return None

    async with sync_service.api_semaphore:  # Use semaphore for API calls
        try:
            # Fetch detailed course info in a thread
            detailed_course = await asyncio.to_thread(
                sync_service.api_adapter.get_course_raw, canvas_id
            )

            # Combine data for validation
            course_data = {
                "id": canvas_id,  # Alias for canvas_course_id
                "course_code": getattr(raw_course, "course_code", ""),
                "name": getattr(raw_course, "name", ""),  # Alias for course_name
                "instructor": getattr(detailed_course, "teacher_name", None)
                if detailed_course
                else None,
                "description": getattr(detailed_course, "description", None)
                if detailed_course
                else None,
                "start_at": getattr(
                    raw_course, "start_at", None
                ),  # Alias for start_date
                "end_at": getattr(raw_course, "end_at", None),  # Alias for end_date
            }

            # Validate using Pydantic model
            db_course = DBCourse.model_validate(course_data)

            # Get syllabus body if available
            syllabus_body = (
                getattr(detailed_course, "syllabus_body", None)
                if detailed_course
                else None
            )

            return db_course, syllabus_body
        except Exception as e:
            logger.error(
                f"Error validating/fetching details for course {canvas_id}: {e}",
                exc_info=True,
            )
            return None


def _filter_courses_by_term(courses: list[Any], term_id: int | None = -1) -> list[Any]:
    """
    Filter courses by term ID. (Remains Synchronous - pure logic)

    Args:
        courses: List of Canvas course objects
        term_id: Term ID to filter by (-1 for most recent term, None for no filtering)

    Returns:
        Filtered list of courses
    """
    if term_id is None:
        logger.info("No term filtering applied.")
        return courses

    active_courses = [c for c in courses if hasattr(c, "enrollment_term_id")]

    if not active_courses:
        logger.warning("No courses with term IDs found.")
        return []

    if term_id == -1:
        try:
            max_term_id = max(c.enrollment_term_id for c in active_courses)
            logger.info(f"Filtering courses by most recent term (ID: {max_term_id})")
            return [
                c
                for c in active_courses
                if getattr(c, "enrollment_term_id", None) == max_term_id
            ]
        except Exception as e:
            logger.error(
                f"Error determining most recent term: {e}. Returning all courses with terms."
            )
            return active_courses
    else:
        logger.info(f"Filtering courses by specific term ID: {term_id}")
        return [
            c
            for c in active_courses
            if getattr(c, "enrollment_term_id", None) == term_id
        ]


def _persist_courses_and_syllabi(
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    sync_service: "SyncService",  # Added sync_service param
    valid_courses_data: list[tuple[DBCourse, str | None]],
) -> list[int]:  # Return list of local IDs
    """
    Persist courses and syllabi in a single transaction using batch operations.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        sync_service: The sync service instance (unused here but part of signature).
        valid_courses_data: List of validated course data tuples (DBCourse, syllabus_body).

    Returns:
        List of local course IDs that were synced/updated.
    """
    synced_local_ids = []
    now_iso = datetime.now().isoformat()
    active_canvas_course_ids = {vc[0].canvas_course_id for vc in valid_courses_data}

    # 1. Cleanup: Remove courses from DB not present in the active set from Canvas
    try:
        cursor.execute("SELECT id, canvas_course_id FROM courses")
        db_courses = cursor.fetchall()
        db_canvas_ids = {row["canvas_course_id"] for row in db_courses}

        ids_to_remove = db_canvas_ids - active_canvas_course_ids
        if ids_to_remove:
            logger.info(
                f"Removing {len(ids_to_remove)} courses no longer active or in the current term filter."
            )
            placeholders = ", ".join("?" * len(ids_to_remove))
            cursor.execute(
                f"DELETE FROM courses WHERE canvas_course_id IN ({placeholders})",
                list(ids_to_remove),
            )
            logger.info(f"Removed courses with Canvas IDs: {ids_to_remove}")
            # Note: Related data (assignments, modules, etc.) should cascade delete due to FOREIGN KEY ON DELETE CASCADE.
    except sqlite3.Error as e:
        logger.error(f"Error during course cleanup: {e}")
        raise  # Propagate error to trigger rollback

    if not valid_courses_data:
        logger.info("No valid courses to persist.")
        return []  # Return empty list if only cleanup happened

    # 2. Fetch existing courses for update/insert separation
    existing_courses_map: dict[int, int] = {}  # canvas_course_id -> local_id
    try:
        placeholders = ", ".join("?" * len(active_canvas_course_ids))
        cursor.execute(
            f"SELECT id, canvas_course_id FROM courses WHERE canvas_course_id IN ({placeholders})",
            list(active_canvas_course_ids),
        )
        for row in cursor.fetchall():
            existing_courses_map[row["canvas_course_id"]] = row["id"]
    except sqlite3.Error as e:
        logger.error(f"Failed to query existing courses: {e}")
        raise

    # 3. Prepare data for batch insert/update
    courses_to_insert_data = []
    courses_to_update_data = []
    canvas_to_local_id_map = {}  # Map for syllabus linking

    for db_course, syllabus_body in valid_courses_data:
        course_dict = db_course.model_dump(exclude={"created_at", "updated_at"})
        course_dict["updated_at"] = now_iso

        if db_course.canvas_course_id in existing_courses_map:
            local_id = existing_courses_map[db_course.canvas_course_id]
            course_dict["local_id"] = local_id  # Add local_id for update WHERE clause
            courses_to_update_data.append(course_dict)
            canvas_to_local_id_map[db_course.canvas_course_id] = local_id
            synced_local_ids.append(local_id)
        else:
            # Prepare tuple for INSERT (ensure order matches columns)
            insert_tuple = (
                course_dict.get("canvas_course_id"),
                course_dict.get("course_code"),
                course_dict.get("course_name"),
                course_dict.get("instructor"),
                course_dict.get("description"),
                course_dict.get("start_date"),
                course_dict.get("end_date"),
                None,  # term_id - currently not handled in model/sync
                None,  # syllabus_body - handled separately
                course_dict.get("updated_at"),
            )
            courses_to_insert_data.append(insert_tuple)
            # We'll get the local_id after insert for syllabus linking

        # Prepare syllabus data (if exists)
        if syllabus_body is not None:
            content_type = detect_content_type(syllabus_body)
            # We'll decide insert/update after checking syllabi table
            # For simplicity now, assume we check later or use INSERT OR REPLACE logic

    # 4. Execute batch course insert
    inserted_local_ids = {}  # canvas_id -> new_local_id
    if courses_to_insert_data:
        cols = "canvas_course_id, course_code, course_name, instructor, description, start_date, end_date, term_id, syllabus_body, updated_at"
        phs = ", ".join(["?"] * len(courses_to_insert_data[0]))
        sql = f"INSERT INTO courses ({cols}) VALUES ({phs})"
        try:
            cursor.executemany(sql, courses_to_insert_data)

            # Re‑query to fetch the reliable (id, canvas_course_id) pairs
            inserted_canvas_ids = [row[0] for row in courses_to_insert_data]
            phs = ",".join("?" * len(inserted_canvas_ids))
            cursor.execute(
                f"SELECT id, canvas_course_id FROM courses "
                f"WHERE canvas_course_id IN ({phs})",
                inserted_canvas_ids,
            )
            rows = cursor.fetchall()

            inserted_count = len(rows)
            logger.debug(f"Batch inserted {inserted_count} courses.")

            for row in rows:
                canvas_id = row["canvas_course_id"]
                local_id = row["id"]
                inserted_local_ids[canvas_id] = local_id
                canvas_to_local_id_map[canvas_id] = local_id
                synced_local_ids.append(local_id)
        except sqlite3.Error as e:
            logger.error(f"Batch course insert failed: {e}")
            raise

    # 5. Execute looped course update
    update_count = 0
    if courses_to_update_data:
        logger.debug(f"Updating {len(courses_to_update_data)} courses individually...")
        for item_dict in courses_to_update_data:
            local_id = item_dict.pop(
                "local_id"
            )  # Remove local_id before creating SET clause
            try:
                set_clause = ", ".join([f"{k} = ?" for k in item_dict])
                values = list(item_dict.values()) + [local_id]
                sql = f"UPDATE courses SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                update_count += cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Failed to update course {local_id}: {e}")
                # Decide whether to continue or raise

    logger.debug(f"Updated {update_count} courses.")

    # 6. Persist Syllabi (Simplified: Using INSERT OR REPLACE for now)
    # A full batch approach would require fetching existing syllabus IDs first.
    syllabi_to_persist = []
    for db_course, syllabus_body in valid_courses_data:
        if syllabus_body is not None:
            local_course_id = canvas_to_local_id_map.get(db_course.canvas_course_id)
            if local_course_id:
                content_type = detect_content_type(syllabus_body)
                syllabi_to_persist.append(
                    (
                        local_course_id,
                        syllabus_body,
                        content_type,
                        None,  # parsed_content
                        False,  # is_parsed
                        now_iso,  # updated_at
                    )
                )

    if syllabi_to_persist:
        logger.debug(
            f"Persisting {len(syllabi_to_persist)} syllabi using INSERT OR REPLACE..."
        )
        # Using INSERT OR REPLACE simplifies logic but might have performance implications
        # It deletes the old row and inserts a new one if a conflict occurs (based on course_id UNIQUE constraint if added)
        # Assuming course_id is unique in syllabi table.
        sql = """
            INSERT OR REPLACE INTO syllabi (course_id, content, content_type, parsed_content, is_parsed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            cursor.executemany(sql, syllabi_to_persist)
            logger.debug(f"Persisted {cursor.rowcount} syllabi.")
        except sqlite3.Error as e:
            logger.error(f"Syllabus persistence failed: {e}")
            raise

    return synced_local_ids  # Return the list of local IDs processed


def _md(text: str | None) -> str | None:
    return convert_html_to_markdown(text) if text else text
