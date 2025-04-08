# Minimal canvas_client.py for testing
import sqlite3
from datetime import datetime

from canvasapi import Canvas


class CanvasClient:
    """
    Client for interacting with the Canvas LMS API and syncing data to the local database.
    """

    @staticmethod
    def detect_content_type(content):
        return "html"

    @staticmethod
    def extract_pdf_links(content):
        return []

    def __init__(self, db_path, api_key=None, api_url=None):
        """
        Initialize the Canvas client.
        """
        self.api_key = api_key
        self.api_url = api_url or "https://canvas.instructure.com"
        self.db_path = db_path

        # Initialize Canvas API
        self.canvas = Canvas(self.api_url, self.api_key)

    def connect_db(self):
        """
        Connect to the SQLite database.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    def sync_courses(self, user_id=None, term_id=None):
        """
        Synchronize course data from Canvas to the local database.
        """
        # Get current user and courses
        user = self.canvas.get_current_user()
        courses = list(user.get_courses())

        # Apply term filtering
        if term_id is not None:
            if term_id == -1:
                # Get most recent term
                term_ids = [
                    getattr(course, "enrollment_term_id", 0) for course in courses
                ]
                term_ids = [t for t in term_ids if t is not None]
                if term_ids:
                    max_term_id = max(term_ids)
                    print(f"Filtering to most recent term (ID: {max_term_id})")
                    courses = [
                        course
                        for course in courses
                        if getattr(course, "enrollment_term_id", None) == max_term_id
                    ]
            else:
                # Filter for specific term
                courses = [
                    course
                    for course in courses
                    if getattr(course, "enrollment_term_id", None) == term_id
                ]

        # Create database schema if needed
        self._ensure_db_schema()

        # Connect to database
        conn, cursor = self.connect_db()

        course_ids = []
        print(f"Processing {len(courses)} courses...")
        for course in courses:
            # Get course data
            self.canvas.get_course(course.id)

            # Insert into database
            cursor.execute(
                "SELECT id FROM courses WHERE canvas_course_id = ?", (course.id,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing course
                print(f"Updating course {course.name} ({course.course_code})")
                cursor.execute(
                    "UPDATE courses SET course_name = ?, course_code = ?, updated_at = ? WHERE id = ?",
                    (
                        course.name,
                        getattr(course, "course_code", ""),
                        datetime.now().isoformat(),
                        existing["id"],
                    ),
                )
                course_id = existing["id"]
            else:
                # Insert new course
                print(
                    f"Adding course {course.name} ({getattr(course, 'course_code', '')})"
                )
                cursor.execute(
                    "INSERT INTO courses (canvas_course_id, course_name, course_code, updated_at) VALUES (?, ?, ?, ?)",
                    (
                        course.id,
                        course.name,
                        getattr(course, "course_code", ""),
                        datetime.now().isoformat(),
                    ),
                )
                course_id = cursor.lastrowid

            course_ids.append(course_id)

        conn.commit()
        conn.close()

        return course_ids

    def _ensure_db_schema(self):
        """Create database schema if it doesn't exist."""
        conn, cursor = self.connect_db()

        # Create courses table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            canvas_course_id INTEGER UNIQUE NOT NULL,
            course_code TEXT,
            course_name TEXT NOT NULL,
            instructor TEXT,
            description TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create syllabi table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS syllabi (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            content TEXT,
            content_type TEXT DEFAULT 'html',
            parsed_content TEXT,
            is_parsed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """)

        conn.commit()
        conn.close()
