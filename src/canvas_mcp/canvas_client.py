"""
Canvas API client for synchronizing data with the local database.
"""
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

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
    
    def __init__(self, db_path: str, api_key: Optional[str] = None, api_url: Optional[str] = None):
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
    
    def connect_db(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        Connect to the SQLite database.
        
        Returns:
            Tuple of (connection, cursor)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor
    
    def sync_courses(self, user_id: Optional[str] = None) -> List[int]:
        """
        Synchronize course data from Canvas to the local database.
        
        Args:
            user_id: Optional user ID to filter courses
        
        Returns:
            List of local course IDs that were synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")
        
        # Get current user if not specified
        if user_id is None:
            user = self.canvas.get_current_user()
            user_id = str(user.id)
        
        # Get courses from Canvas
        courses = self.canvas.get_user(user_id).get_courses()
        
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
            
            # Insert or update course in database
            cursor.execute(
                """
                INSERT INTO courses (
                    canvas_course_id, course_code, course_name, 
                    instructor, description, start_date, end_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (canvas_course_id) DO UPDATE SET
                    course_code = excluded.course_code,
                    course_name = excluded.course_name,
                    instructor = excluded.instructor,
                    description = excluded.description,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    updated_at = excluded.updated_at
                RETURNING id
                """,
                (
                    course.id,
                    getattr(course, "course_code", ""),
                    course.name,
                    getattr(detailed_course, "teacher", None),
                    getattr(detailed_course, "description", None),
                    getattr(detailed_course, "start_at", None),
                    getattr(detailed_course, "end_at", None),
                    datetime.now().isoformat()
                )
            )
            
            local_course_id = cursor.fetchone()[0]
            course_ids.append(local_course_id)
            
            # Store or update syllabus
            if hasattr(detailed_course, "syllabus_body") and detailed_course.syllabus_body:
                cursor.execute(
                    """
                    INSERT INTO syllabi (course_id, content, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT (course_id) DO UPDATE SET
                        content = excluded.content,
                        updated_at = excluded.updated_at
                    """,
                    (local_course_id, detailed_course.syllabus_body, datetime.now().isoformat())
                )
        
        conn.commit()
        conn.close()
        
        return course_ids
    
    def sync_assignments(self, course_ids: Optional[List[int]] = None) -> int:
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
                    # Insert or update assignment in database
                    cursor.execute(
                        """
                        INSERT INTO assignments (
                            course_id, canvas_assignment_id, title, description,
                            assignment_type, due_date, available_from, available_until,
                            points_possible, submission_types, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (course_id, canvas_assignment_id) DO UPDATE SET
                            title = excluded.title,
                            description = excluded.description,
                            assignment_type = excluded.assignment_type,
                            due_date = excluded.due_date,
                            available_from = excluded.available_from,
                            available_until = excluded.available_until,
                            points_possible = excluded.points_possible,
                            submission_types = excluded.submission_types,
                            updated_at = excluded.updated_at
                        RETURNING id
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
                            ",".join(getattr(assignment, "submission_types", [])),
                            datetime.now().isoformat()
                        )
                    )
                    
                    assignment_id = cursor.fetchone()[0]
                    assignment_count += 1
                    
                    # Add to calendar events
                    if hasattr(assignment, "due_at") and assignment.due_at:
                        cursor.execute(
                            """
                            INSERT INTO calendar_events (
                                course_id, title, description, event_type,
                                source_type, source_id, event_date, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT (course_id, source_type, source_id) DO UPDATE SET
                                title = excluded.title,
                                description = excluded.description,
                                event_date = excluded.event_date,
                                updated_at = excluded.updated_at
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
    
    def sync_modules(self, course_ids: Optional[List[int]] = None) -> int:
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
                    # Insert or update module in database
                    cursor.execute(
                        """
                        INSERT INTO modules (
                            course_id, canvas_module_id, name, description,
                            unlock_date, position, require_sequential_progress, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (course_id, canvas_module_id) DO UPDATE SET
                            name = excluded.name,
                            description = excluded.description,
                            unlock_date = excluded.unlock_date,
                            position = excluded.position,
                            require_sequential_progress = excluded.require_sequential_progress,
                            updated_at = excluded.updated_at
                        RETURNING id
                        """,
                        (
                            local_course_id,
                            module.id,
                            module.name,
                            getattr(module, "description", None),
                            getattr(module, "unlock_at", None),
                            getattr(module, "position", None),
                            getattr(module, "require_sequential_progress", False),
                            datetime.now().isoformat()
                        )
                    )
                    
                    local_module_id = cursor.fetchone()[0]
                    module_count += 1
                    
                    # Get module items
                    try:
                        items = module.get_module_items()
                        for item in items:
                            # Insert or update module item in database
                            cursor.execute(
                                """
                                INSERT INTO module_items (
                                    module_id, canvas_item_id, title, item_type,
                                    position, url, page_url, content_details, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT (module_id, canvas_item_id) DO UPDATE SET
                                    title = excluded.title,
                                    item_type = excluded.item_type,
                                    position = excluded.position,
                                    url = excluded.url,
                                    page_url = excluded.page_url,
                                    content_details = excluded.content_details,
                                    updated_at = excluded.updated_at
                                """,
                                (
                                    local_module_id,
                                    item.id,
                                    getattr(item, "title", None),
                                    getattr(item, "type", None),
                                    getattr(item, "position", None),
                                    getattr(item, "external_url", None),
                                    getattr(item, "page_url", None),
                                    str(item) if hasattr(item, "__dict__") else None,
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
    
    def sync_announcements(self, course_ids: Optional[List[int]] = None) -> int:
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
                    # Insert or update announcement in database
                    cursor.execute(
                        """
                        INSERT INTO announcements (
                            course_id, canvas_announcement_id, title, content,
                            posted_by, posted_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (course_id, canvas_announcement_id) DO UPDATE SET
                            title = excluded.title,
                            content = excluded.content,
                            posted_by = excluded.posted_by,
                            posted_at = excluded.posted_at,
                            updated_at = excluded.updated_at
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
    
    def sync_all(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        Synchronize all data from Canvas to the local database.
        
        Args:
            user_id: Optional user ID to filter courses
        
        Returns:
            Dictionary with counts of synced items
        """
        # First sync courses
        course_ids = self.sync_courses(user_id)
        
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
