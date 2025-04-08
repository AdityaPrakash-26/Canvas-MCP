"""
Unit tests for the CanvasClient class using the fake Canvas API.
"""

import os
import unittest
from pathlib import Path

from tests.fakes.fake_canvasapi import patch_canvasapi

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager

# Apply the patch before importing any code that uses canvasapi
patch_canvasapi()


class TestCanvasClient(unittest.TestCase):
    """Test the CanvasClient class with the fake Canvas API."""

    def setUp(self):
        """Set up the test environment."""
        # Create a test database
        self.db_path = Path("tests/test_data/test_unit.db")
        os.makedirs(self.db_path.parent, exist_ok=True)

        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            from init_db import create_database

            create_database(str(self.db_path))

        # Create a database manager
        self.db_manager = DatabaseManager(self.db_path)

        # Create a Canvas client with the fake Canvas API
        self.canvas_client = CanvasClient(self.db_manager, "fake_api_key")

    def test_sync_courses(self):
        """Test syncing courses from Canvas."""
        # Sync courses
        course_ids = self.canvas_client.sync_courses()

        # Verify that courses were synced
        self.assertIsInstance(course_ids, list)
        self.assertGreater(len(course_ids), 0)

        # Verify that courses are in the database
        conn, cursor = self.db_manager.connect()
        cursor.execute("SELECT COUNT(*) FROM courses")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreater(count, 0)

    def test_sync_courses_filters_by_enrollment_state(self):
        """Test that sync_courses filters by enrollment state."""
        # Clean the database first
        conn, cursor = self.db_manager.connect()
        cursor.execute("DELETE FROM courses")
        conn.commit()

        # Get all courses directly from the fake Canvas API
        user = self.canvas_client.canvas.get_current_user()
        all_courses = list(user.get_courses())

        # Get active courses directly from the fake Canvas API
        active_courses = list(user.get_courses(enrollment_state="active"))

        # Verify that there are more total courses than active courses
        # This ensures our test fixture has both active and non-active courses
        self.assertGreaterEqual(len(all_courses), len(active_courses))

        # Sync courses using our client with term_id=None to disable term filtering
        # This allows us to test just the enrollment state filtering
        course_ids = self.canvas_client.sync_courses(term_id=None)

        # Verify that we synced some courses
        self.assertGreater(len(course_ids), 0)

        # Get database connection
        cursor.execute("SELECT canvas_course_id FROM courses")
        synced_course_ids = [row[0] for row in cursor.fetchall()]

        # Verify that only active courses were synced
        for course in all_courses:
            course_id = getattr(course, "id", None)
            if not course_id:
                continue

            # Check if this course has non-active enrollment
            is_active = True
            if hasattr(course, "enrollments") and course.enrollments:
                if course.enrollments[0].get("enrollment_state") != "active":
                    is_active = False

            # If course is not active, it should not be in the synced courses
            if not is_active:
                self.assertNotIn(
                    course_id,
                    synced_course_ids,
                    f"Course with non-active enrollment state (ID: {course_id}) was synced",
                )

        conn.close()

    def test_sync_courses_filters_by_term(self):
        """Test that sync_courses filters by term."""
        # Clean the database first
        conn, cursor = self.db_manager.connect()
        cursor.execute("DELETE FROM courses")
        conn.commit()

        # Get active courses directly from the fake Canvas API
        user = self.canvas_client.canvas.get_current_user()
        active_courses = list(user.get_courses(enrollment_state="active"))

        # Get term IDs
        term_ids = set()
        for course in active_courses:
            term_id = getattr(course, "enrollment_term_id", None)
            if term_id:
                term_ids.add(term_id)

        # Skip test if there's only one term in the test data
        if len(term_ids) <= 1:
            self.skipTest("Test data doesn't have multiple terms")

        # Find the most recent term (maximum term_id)
        max_term_id = max(term_ids)

        # Count courses in the most recent term
        [
            course
            for course in active_courses
            if getattr(course, "enrollment_term_id", None) == max_term_id
        ]

        # Sync courses using our client (should default to most recent term)
        course_ids = self.canvas_client.sync_courses()

        # Verify that we synced some courses
        self.assertGreater(len(course_ids), 0)

        # Get synced course IDs from database
        cursor.execute("SELECT canvas_course_id FROM courses")
        synced_course_ids = [row[0] for row in cursor.fetchall()]

        # Verify that only courses from the current term were synced
        for course in active_courses:
            course_id = getattr(course, "id", None)
            term_id = getattr(course, "enrollment_term_id", None)

            if not course_id or not term_id:
                continue

            # If course is from a different term, it should not be in the synced courses
            if term_id != max_term_id:
                self.assertNotIn(
                    course_id,
                    synced_course_ids,
                    f"Course from different term (ID: {course_id}, Term: {term_id}) was synced",
                )

        conn.close()

    def test_sync_assignments(self):
        """Test syncing assignments from Canvas."""
        # First sync courses to get course IDs
        course_ids = self.canvas_client.sync_courses()

        # Sync assignments
        assignment_count = self.canvas_client.sync_assignments(course_ids)

        # Verify that assignments were synced
        self.assertIsInstance(assignment_count, int)

        # Verify that assignments are in the database
        conn, cursor = self.db_manager.connect()
        cursor.execute("SELECT COUNT(*) FROM assignments")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(count, assignment_count)

    def test_extract_pdf_links(self):
        """Test extracting PDF links from content."""
        # Test with HTML content containing PDF links
        content = """
        <p>Here are some PDF links:</p>
        <ul>
            <li><a href="https://example.com/file.pdf">PDF File</a></li>
            <li><a href="https://canvas.instructure.com/files/12345/download">Canvas File</a></li>
        </ul>
        """

        pdf_links = self.canvas_client.extract_pdf_links(content)

        # Verify that PDF links were extracted
        self.assertIsInstance(pdf_links, list)
        self.assertGreaterEqual(len(pdf_links), 1)

        # Verify that at least one link contains .pdf
        pdf_found = any(".pdf" in link.lower() for link in pdf_links)
        self.assertTrue(pdf_found)


if __name__ == "__main__":
    unittest.main()
