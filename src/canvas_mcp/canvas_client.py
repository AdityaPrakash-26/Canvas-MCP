"""
Canvas API client for synchronizing data with the local database.
"""
import os
import sqlite3
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

# Make Canvas available for patching in tests
try:
    from canvasapi import Canvas
except ImportError:
    # Create a dummy Canvas class for tests to patch
    class Canvas:
        def __init__(self, api_url, api_key):
            self.api_url = api_url
            self.api_key = api_key


class CanvasClient:
    """
    Client for interacting with the Canvas LMS API and syncing data to the local database.
    """

    def __init__(self, db_path: str, api_key: str | None = None, api_url: str | None = None):
        """
        Initialize the Canvas client.

        Args:
            db_path: Path to the SQLite database
            api_key: Canvas API key (if None, will look for CANVAS_API_KEY in environment)
            api_url: Canvas API URL (if None, will use default Canvas URL)
        """
        # Load environment variables if api_key not provided
        if api_key is None:
            load_dotenv()
            api_key = os.environ.get("CANVAS_API_KEY")

        self.api_key = api_key
        self.api_url = api_url or "https://canvas.instructure.com"
        self.db_path = db_path

        # Import canvasapi here to avoid making it a hard dependency
        try:
            from canvasapi import Canvas
            self.canvas = Canvas(self.api_url, self.api_key)
        except ImportError:
            self.canvas = None
            print("Warning: canvasapi module not found. Some features will be limited.")

    def connect_db(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        Connect to the SQLite database.

        Returns:
            Tuple of (connection, cursor)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    def sync_courses(self, user_id: str | None = None, term_id: int | None = None) -> list[int]:
        """
        Synchronize course data from Canvas to the local database.

        Args:
            user_id: Optional user ID to filter courses
            term_id: Optional term ID to filter courses
                     (use -1 to select only the most recent term)

        Returns:
            List of local course IDs that were synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Get current user if not specified
        if user_id is None:
            user = self.canvas.get_current_user()
            user_id = str(user.id)
        else:
            user = self.canvas.get_current_user()  # Always use current user for authentication

        # Get courses from Canvas directly using the user object
        # This fixes the authentication issue reported in integration testing
        courses = list(user.get_courses())

        # Apply term filtering if requested
        if term_id is not None:
            if term_id == -1:
                # Get the most recent term (maximum term_id)
                term_ids = [getattr(course, 'enrollment_term_id', 0) for course in courses]
                if term_ids:
                    max_term_id = max(filter(lambda x: x is not None, term_ids), default=None)
                    if max_term_id is not None:
                        print(f"Filtering to only include the most recent term (ID: {max_term_id})")
                        courses = [
                            course for course in courses 
                            if getattr(course, 'enrollment_term_id', None) == max_term_id
                        ]
            else:
                # Filter for the specific term requested
                courses = [
                    course for course in courses 
                    if getattr(course, 'enrollment_term_id', None) == term_id
                ]

        # Connect to database
        conn, cursor = self.connect_db()

        course_ids = []
        for course in courses:
            # Check if user has opted out of this course
            cursor.execute(
                "SELECT indexing_opt_out FROM user_courses WHERE user_id = ? AND course_id = ?",
                (user_id, course.id)
            )
            row = cursor.fetchone()
            if row and row["indexing_opt_out"]:
                print(f"Skipping opted-out course: {course.name}")
                continue

            # Get detailed course information
            detailed_course = self.canvas.get_course(course.id)

            # Properly convert all MagicMock attributes to appropriate types for SQLite
            course_id = int(course.id) if hasattr(course, "id") else None
            course_code = str(getattr(course, "course_code", "")) if getattr(course, "course_code", None) is not None else ""
            course_name = str(course.name) if hasattr(course, "name") else ""
            instructor = str(getattr(detailed_course, "teacher", "")) if getattr(detailed_course, "teacher", None) is not None else None
            description = str(getattr(detailed_course, "description", "")) if getattr(detailed_course, "description", None) is not None else None
            start_date = str(getattr(detailed_course, "start_at", "")) if getattr(detailed_course, "start_at", None) is not None else None
            end_date = str(getattr(detailed_course, "end_at", "")) if getattr(detailed_course, "end_at", None) is not None else None

            # Check if course exists
            cursor.execute(
                "SELECT id FROM courses WHERE canvas_course_id = ?",
                (course_id,)
            )
            existing_course = cursor.fetchone()

            if existing_course:
                # Update existing course
                cursor.execute(
                    """
                    UPDATE courses SET
                        course_code = ?,
                        course_name = ?,
                        instructor = ?,
                        description = ?,
                        start_date = ?,
                        end_date = ?,
                        updated_at = ?
                    WHERE canvas_course_id = ?
                    """,
                    (
                        course_code,
                        course_name,
                        instructor,
                        description,
                        start_date,
                        end_date,
                        datetime.now().isoformat(),
                        course_id
                    )
                )
                local_course_id = existing_course["id"]
            else:
                # Insert new course
                cursor.execute(
                    """
                    INSERT INTO courses (
                        canvas_course_id, course_code, course_name,
                        instructor, description, start_date, end_date, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        course_code,
                        course_name,
                        instructor,
                        description,
                        start_date,
                        end_date,
                        datetime.now().isoformat()
                    )
                )
                local_course_id = cursor.lastrowid
            course_ids.append(local_course_id)

            # Store or update syllabus
            if hasattr(detailed_course, "syllabus_body") and detailed_course.syllabus_body:
                # Check if syllabus exists
                cursor.execute(
                    "SELECT id FROM syllabi WHERE course_id = ?",
                    (local_course_id,)
                )
                existing_syllabus = cursor.fetchone()

                if existing_syllabus:
                    # Update existing syllabus
                    cursor.execute(
                        """
                        UPDATE syllabi SET
                            content = ?,
                            updated_at = ?
                        WHERE course_id = ?
                        """,
                        (detailed_course.syllabus_body, datetime.now().isoformat(), local_course_id)
                    )
                else:
                    # Insert new syllabus
                    cursor.execute(
                        """
                        INSERT INTO syllabi (course_id, content, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (local_course_id, detailed_course.syllabus_body, datetime.now().isoformat())
                    )

        conn.commit()
        conn.close()

        return course_ids

    def sync_assignments(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize assignment data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of assignments synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        assignment_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get assignments for the course
                assignments = canvas_course.get_assignments()

                for assignment in assignments:
                    # Convert submission_types to string
                    submission_types = ",".join(getattr(assignment, "submission_types", []))
                    
                    # Check if assignment exists
                    cursor.execute(
                        "SELECT id FROM assignments WHERE course_id = ? AND canvas_assignment_id = ?",
                        (local_course_id, assignment.id)
                    )
                    existing_assignment = cursor.fetchone()

                    if existing_assignment:
                        # Update existing assignment
                        cursor.execute(
                            """
                            UPDATE assignments SET
                                title = ?,
                                description = ?,
                                assignment_type = ?,
                                due_date = ?,
                                available_from = ?,
                                available_until = ?,
                                points_possible = ?,
                                submission_types = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                assignment.name,
                                getattr(assignment, "description", None),
                                self._get_assignment_type(assignment),
                                getattr(assignment, "due_at", None),
                                getattr(assignment, "unlock_at", None),
                                getattr(assignment, "lock_at", None),
                                getattr(assignment, "points_possible", None),
                                submission_types,
                                datetime.now().isoformat(),
                                existing_assignment["id"]
                            )
                        )
                        assignment_id = existing_assignment["id"]
                    else:
                        # Insert new assignment
                        cursor.execute(
                            """
                            INSERT INTO assignments (
                                course_id, canvas_assignment_id, title, description,
                                assignment_type, due_date, available_from, available_until,
                                points_possible, submission_types, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                assignment.id,
                                assignment.name,
                                getattr(assignment, "description", None),
                                self._get_assignment_type(assignment),
                                getattr(assignment, "due_at", None),
                                getattr(assignment, "unlock_at", None),
                                getattr(assignment, "lock_at", None),
                                getattr(assignment, "points_possible", None),
                                submission_types,
                                datetime.now().isoformat()
                            )
                        )
                        assignment_id = cursor.lastrowid
                    assignment_count += 1

                    # Add to calendar events
                    if hasattr(assignment, "due_at") and assignment.due_at:
                        # Check if calendar event exists
                        cursor.execute(
                            """
                            SELECT id FROM calendar_events 
                            WHERE course_id = ? AND source_type = ? AND source_id = ?
                            """,
                            (local_course_id, "assignment", assignment_id)
                        )
                        existing_event = cursor.fetchone()

                        if existing_event:
                            # Update existing event
                            cursor.execute(
                                """
                                UPDATE calendar_events SET
                                    title = ?,
                                    description = ?,
                                    event_date = ?,
                                    updated_at = ?
                                WHERE id = ?
                                """,
                                (
                                    assignment.name,
                                    f"Due date for assignment: {assignment.name}",
                                    assignment.due_at,
                                    datetime.now().isoformat(),
                                    existing_event["id"]
                                )
                            )
                        else:
                            # Insert new event
                            cursor.execute(
                                """
                                INSERT INTO calendar_events (
                                    course_id, title, description, event_type,
                                    source_type, source_id, event_date, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    local_course_id,
                                    assignment.name,
                                    f"Due date for assignment: {assignment.name}",
                                    self._get_assignment_type(assignment),
                                    "assignment",
                                    assignment_id,
                                    assignment.due_at,
                                    datetime.now().isoformat()
                                )
                            )
            except Exception as e:
                print(f"Error syncing assignments for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return assignment_count

    def sync_modules(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize module data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of modules synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        module_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get modules for the course
                modules = canvas_course.get_modules()

                for module in modules:
                    # Convert boolean attribute to integer for SQLite
                    require_sequential_progress = 1 if getattr(module, "require_sequential_progress", False) else 0

                    # Properly convert all MagicMock attributes to appropriate types for SQLite
                    module_id = int(module.id) if hasattr(module, "id") else None
                    module_name = str(module.name) if hasattr(module, "name") else ""
                    module_description = str(getattr(module, "description", "")) if getattr(module, "description", None) is not None else None
                    module_unlock_at = str(getattr(module, "unlock_at", "")) if getattr(module, "unlock_at", None) is not None else None
                    module_position = int(getattr(module, "position", 0)) if getattr(module, "position", None) is not None else None

                    # Check if module exists
                    cursor.execute(
                        "SELECT id FROM modules WHERE course_id = ? AND canvas_module_id = ?",
                        (local_course_id, module_id)
                    )
                    existing_module = cursor.fetchone()

                    if existing_module:
                        # Update existing module
                        cursor.execute(
                            """
                            UPDATE modules SET
                                name = ?,
                                description = ?,
                                unlock_date = ?,
                                position = ?,
                                require_sequential_progress = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                module_name,
                                module_description,
                                module_unlock_at,
                                module_position,
                                require_sequential_progress,
                                datetime.now().isoformat(),
                                existing_module["id"]
                            )
                        )
                        local_module_id = existing_module["id"]
                    else:
                        # Insert new module
                        cursor.execute(
                            """
                            INSERT INTO modules (
                                course_id, canvas_module_id, name, description,
                                unlock_date, position, require_sequential_progress, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                module_id,
                                module_name,
                                module_description,
                                module_unlock_at,
                                module_position,
                                require_sequential_progress,
                                datetime.now().isoformat()
                            )
                        )
                        local_module_id = cursor.lastrowid
                    module_count += 1

                    # Get module items
                    try:
                        items = module.get_module_items()
                        for item in items:
                            # Properly convert all MagicMock attributes to appropriate types for SQLite
                            item_id = int(item.id) if hasattr(item, "id") else None
                            item_title = str(getattr(item, "title", "")) if getattr(item, "title", None) is not None else None
                            item_type = str(getattr(item, "type", "")) if getattr(item, "type", None) is not None else None
                            item_position = int(getattr(item, "position", 0)) if getattr(item, "position", None) is not None else None
                            item_url = str(getattr(item, "external_url", "")) if getattr(item, "external_url", None) is not None else None
                            item_page_url = str(getattr(item, "page_url", "")) if getattr(item, "page_url", None) is not None else None
                            
                            # Convert the content_details to a string representation
                            content_details = str(item) if hasattr(item, "__dict__") else None
                            
                            # Check if module item exists
                            cursor.execute(
                                "SELECT id FROM module_items WHERE module_id = ? AND canvas_item_id = ?",
                                (local_module_id, item_id)
                            )
                            existing_item = cursor.fetchone()

                            if existing_item:
                                # Update existing item
                                cursor.execute(
                                    """
                                    UPDATE module_items SET
                                        title = ?,
                                        item_type = ?,
                                        position = ?,
                                        url = ?,
                                        page_url = ?,
                                        content_details = ?,
                                        updated_at = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        item_title,
                                        item_type,
                                        item_position,
                                        item_url,
                                        item_page_url,
                                        content_details,
                                        datetime.now().isoformat(),
                                        existing_item["id"]
                                    )
                                )
                            else:
                                # Insert new item
                                cursor.execute(
                                    """
                                    INSERT INTO module_items (
                                        module_id, canvas_item_id, title, item_type,
                                        position, url, page_url, content_details, updated_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        local_module_id,
                                        item_id,
                                        item_title,
                                        item_type,
                                        item_position,
                                        item_url,
                                        item_page_url,
                                        content_details,
                                        datetime.now().isoformat()
                                    )
                                )
                    except Exception as e:
                        print(f"Error syncing module items for module {module.id}: {e}")
            except Exception as e:
                print(f"Error syncing modules for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return module_count

    def sync_announcements(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize announcement data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of announcements synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        announcement_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get announcements for the course
                announcements = canvas_course.get_discussion_topics(only_announcements=True)

                for announcement in announcements:
                    # Check if announcement exists
                    cursor.execute(
                        "SELECT id FROM announcements WHERE course_id = ? AND canvas_announcement_id = ?",
                        (local_course_id, announcement.id)
                    )
                    existing_announcement = cursor.fetchone()

                    if existing_announcement:
                        # Update existing announcement
                        cursor.execute(
                            """
                            UPDATE announcements SET
                                title = ?,
                                content = ?,
                                posted_by = ?,
                                posted_at = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                announcement.title,
                                getattr(announcement, "message", None),
                                getattr(announcement, "author_name", None),
                                getattr(announcement, "posted_at", None),
                                datetime.now().isoformat(),
                                existing_announcement["id"]
                            )
                        )
                    else:
                        # Insert new announcement
                        cursor.execute(
                            """
                            INSERT INTO announcements (
                                course_id, canvas_announcement_id, title, content,
                                posted_by, posted_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                announcement.id,
                                announcement.title,
                                getattr(announcement, "message", None),
                                getattr(announcement, "author_name", None),
                                getattr(announcement, "posted_at", None),
                                datetime.now().isoformat()
                            )
                        )

                    announcement_count += 1
            except Exception as e:
                print(f"Error syncing announcements for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return announcement_count

    def sync_all(self, user_id: str | None = None, term_id: int | None = -1) -> dict[str, int]:
        """
        Synchronize all data from Canvas to the local database.

        Args:
            user_id: Optional user ID to filter courses
            term_id: Optional term ID to filter courses
                     (default is -1, which only selects the most recent term)

        Returns:
            Dictionary with counts of synced items
        """
        # First sync courses
        course_ids = self.sync_courses(user_id, term_id)

        # Then sync other data
        assignment_count = self.sync_assignments(course_ids)
        module_count = self.sync_modules(course_ids)
        announcement_count = self.sync_announcements(course_ids)

        return {
            "courses": len(course_ids),
            "assignments": assignment_count,
            "modules": module_count,
            "announcements": announcement_count
        }

    def _get_assignment_type(self, assignment: Any) -> str:
        """
        Determine the type of an assignment.

        Args:
            assignment: Canvas assignment object

        Returns:
            Assignment type string
        """
        if not hasattr(assignment, "submission_types"):
            return "assignment"

        if "online_quiz" in assignment.submission_types:
            return "quiz"
        elif "discussion_topic" in assignment.submission_types:
            return "discussion"
        elif any(t in assignment.name.lower() for t in ["exam", "midterm", "final"]):
            return "exam"
        else:
            return "assignment"
