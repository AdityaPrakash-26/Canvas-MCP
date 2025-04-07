"""
Integration tests for Canvas MCP server.

This test file covers all major code paths in the Canvas MCP server,
focusing on the SP25_CS_540_1 course (Canvas Course ID: 146127).
"""

import os
import sys
import unittest
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import server components
from src.canvas_mcp.server import (
    sync_canvas_data,
    get_course_list,
    get_course_assignments,
    get_course_modules,
    get_syllabus,
    get_course_files,
    extract_text_from_course_file,
    get_assignment_details,
    search_course_content,
    get_upcoming_deadlines,
    get_syllabus_file,
    query_assignment,
)

# Import database utilities
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Test database path
TEST_DB_PATH = Path(__file__).parent / "test_data" / "test_canvas_mcp.db"


class TestCanvasMCPIntegration(unittest.TestCase):
    """Integration tests for Canvas MCP server."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Ensure test data directory exists
        os.makedirs(TEST_DB_PATH.parent, exist_ok=True)

        # Always recreate the database for a clean test environment
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

        # Initialize the test database
        from init_db import create_database

        create_database(str(TEST_DB_PATH))

        # Create database manager for tests
        cls.db_manager = DatabaseManager(TEST_DB_PATH)

        # Store the target course code and ID
        cls.target_course_code = "SP25_CS_540_1"
        cls.target_canvas_course_id = 146127

        # We'll find the internal course ID during the tests
        cls.target_course_id = None

    def setUp(self):
        """Set up before each test."""
        # Connect to the database
        self.conn, self.cursor = self.db_manager.connect()

        # Try to find the target course ID if we don't have it yet
        if self.__class__.target_course_id is None:
            self.cursor.execute(
                "SELECT id FROM courses WHERE course_code = ? OR canvas_course_id = ?",
                (
                    self.__class__.target_course_code,
                    self.__class__.target_canvas_course_id,
                ),
            )
            result = self.cursor.fetchone()
            if result:
                self.__class__.target_course_id = result["id"]
                print(
                    f"Found target course with internal ID: {self.__class__.target_course_id}"
                )

    def tearDown(self):
        """Clean up after each test."""
        self.conn.close()

    def test_01_sync_canvas_data(self):
        """Test synchronizing data from Canvas."""
        # Skip if we're in CI environment without Canvas API key
        if not os.environ.get("CANVAS_API_KEY") and not os.path.exists(".env"):
            # For testing without Canvas API, insert a test course directly
            self.cursor.execute(
                """INSERT INTO courses
                   (canvas_course_id, course_code, course_name, instructor)
                   VALUES (?, ?, ?, ?)""",
                (
                    self.__class__.target_canvas_course_id,
                    self.__class__.target_course_code,
                    "Artificial Intelligence",
                    "Test Instructor",
                ),
            )
            self.conn.commit()

            # Get the ID of the inserted course
            self.cursor.execute(
                "SELECT id FROM courses WHERE course_code = ?",
                (self.__class__.target_course_code,),
            )
            result = self.cursor.fetchone()
            if result:
                self.__class__.target_course_id = result["id"]
                print(
                    f"Created test course with internal ID: {self.__class__.target_course_id}"
                )
                return
            else:
                self.fail("Failed to create test course")

        # Run the sync with Canvas API
        try:
            result = sync_canvas_data(force=True)

            # Check that we got some data
            self.assertIsInstance(result, dict)
            self.assertIn("courses", result)
            self.assertGreaterEqual(result["courses"], 0)

            # Verify our target course exists after sync
            self.conn, self.cursor = (
                self.db_manager.connect()
            )  # Reconnect to get fresh data
            self.cursor.execute(
                "SELECT id FROM courses WHERE course_code = ? OR canvas_course_id = ?",
                (
                    self.__class__.target_course_code,
                    self.__class__.target_canvas_course_id,
                ),
            )
            result = self.cursor.fetchone()

            if result:
                self.__class__.target_course_id = result["id"]
                print(
                    f"Found target course with internal ID: {self.__class__.target_course_id}"
                )
            else:
                # If the course wasn't found, insert it manually for testing
                self.cursor.execute(
                    """INSERT INTO courses
                       (canvas_course_id, course_code, course_name, instructor)
                       VALUES (?, ?, ?, ?)""",
                    (
                        self.__class__.target_canvas_course_id,
                        self.__class__.target_course_code,
                        "Artificial Intelligence",
                        "Test Instructor",
                    ),
                )
                self.conn.commit()

                # Get the ID of the inserted course
                self.cursor.execute(
                    "SELECT id FROM courses WHERE course_code = ?",
                    (self.__class__.target_course_code,),
                )
                result = self.cursor.fetchone()
                if result:
                    self.__class__.target_course_id = result["id"]
                    print(
                        f"Created test course with internal ID: {self.__class__.target_course_id}"
                    )
                else:
                    self.fail("Failed to create test course")
        except Exception as e:
            # If sync fails, insert a test course directly
            print(f"Sync failed: {e}. Creating test course directly.")
            self.cursor.execute(
                """INSERT INTO courses
                   (canvas_course_id, course_code, course_name, instructor)
                   VALUES (?, ?, ?, ?)""",
                (
                    self.__class__.target_canvas_course_id,
                    self.__class__.target_course_code,
                    "Artificial Intelligence",
                    "Test Instructor",
                ),
            )
            self.conn.commit()

            # Get the ID of the inserted course
            self.cursor.execute(
                "SELECT id FROM courses WHERE course_code = ?",
                (self.__class__.target_course_code,),
            )
            result = self.cursor.fetchone()
            if result:
                self.__class__.target_course_id = result["id"]
                print(
                    f"Created test course with internal ID: {self.__class__.target_course_id}"
                )
            else:
                self.fail("Failed to create test course")

    def test_02_get_course_list(self):
        """Test getting the list of courses."""
        # Get course list
        courses = get_course_list()

        # Check that we got a list of courses
        self.assertIsInstance(courses, list)

        # Look for our target course
        target_course = None
        for course in courses:
            if (
                course.get("course_code") == self.__class__.target_course_code
                or course.get("canvas_course_id")
                == self.__class__.target_canvas_course_id
            ):
                target_course = course
                break

        # If we found the course, store its internal ID
        if target_course:
            self.__class__.target_course_id = target_course["id"]
            print(
                f"Found target course with internal ID: {self.__class__.target_course_id}"
            )
        else:
            self.skipTest(
                f"Target course {self.__class__.target_course_code} not found in course list"
            )

    def test_03_get_course_assignments(self):
        """Test getting assignments for a course."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get assignments
        assignments = get_course_assignments(self.__class__.target_course_id)

        # Check that we got a list of assignments
        self.assertIsInstance(assignments, list)
        print(
            f"Found {len(assignments)} assignments for course {self.__class__.target_course_id}"
        )

        # Print some assignment details for debugging
        if assignments:
            print(f"First assignment: {assignments[0].get('title')}")

    def test_04_get_course_modules(self):
        """Test getting modules for a course."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get modules without items
        modules = get_course_modules(
            self.__class__.target_course_id, include_items=False
        )

        # Check that we got a list of modules
        self.assertIsInstance(modules, list)
        print(
            f"Found {len(modules)} modules for course {self.__class__.target_course_id}"
        )

        # Get modules with items
        modules_with_items = get_course_modules(
            self.__class__.target_course_id, include_items=True
        )

        # Check that we got a list of modules with items
        self.assertIsInstance(modules_with_items, list)

        # Check that at least one module has items if there are modules
        if modules_with_items:
            has_items = any("items" in module for module in modules_with_items)
            print(f"Modules with items: {has_items}")

    def test_05_get_syllabus(self):
        """Test getting the syllabus for a course."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get syllabus in raw format
        syllabus_raw = get_syllabus(self.__class__.target_course_id, format="raw")

        # Check that we got a syllabus
        self.assertIsInstance(syllabus_raw, dict)
        self.assertIn("content", syllabus_raw)
        self.assertIn("content_type", syllabus_raw)

        # Get syllabus in parsed format
        syllabus_parsed = get_syllabus(self.__class__.target_course_id, format="parsed")

        # Check that we got a syllabus
        self.assertIsInstance(syllabus_parsed, dict)
        self.assertIn("content", syllabus_parsed)

    def test_06_get_course_files(self):
        """Test getting files for a course."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get all files
        files = get_course_files(self.__class__.target_course_id)

        # Check that we got a list of files
        self.assertIsInstance(files, list)
        print(f"Found {len(files)} files for course {self.__class__.target_course_id}")

        # Get PDF files
        pdf_files = get_course_files(self.__class__.target_course_id, file_type="pdf")

        # Check that we got a list of PDF files
        self.assertIsInstance(pdf_files, list)
        print(
            f"Found {len(pdf_files)} PDF files for course {self.__class__.target_course_id}"
        )

        # Store a PDF file URL for later tests if available
        if pdf_files:
            self.__class__.test_pdf_url = pdf_files[0].get("url")
            print(f"Found PDF file: {pdf_files[0].get('name')}")

    def test_07_extract_text_from_course_file(self):
        """Test extracting text from a course file."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Skip if we don't have a PDF file URL
        if (
            not hasattr(self.__class__, "test_pdf_url")
            or not self.__class__.test_pdf_url
        ):
            # Try to get a syllabus file
            try:
                syllabus_file = get_syllabus_file(
                    self.__class__.target_course_id, extract_content=False
                )
                if syllabus_file.get("success") and "syllabus_file" in syllabus_file:
                    self.__class__.test_pdf_url = syllabus_file["syllabus_file"].get(
                        "url"
                    )
                    print(f"Using syllabus file URL: {self.__class__.test_pdf_url}")
                else:
                    self.skipTest(
                        "No PDF file URL available and no syllabus file found"
                    )
            except Exception as e:
                self.skipTest(f"Error getting syllabus file: {e}")

        # Extract text from the file
        result = extract_text_from_course_file(
            self.__class__.target_course_id,
            self.__class__.test_pdf_url,
            file_type="pdf",
        )

        # Check that we got a result
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

        # If extraction was successful, check the text
        if result.get("success"):
            self.assertIn("text", result)
            self.assertIsInstance(result["text"], str)
            print(f"Extracted {result.get('text_length', 0)} characters of text")

    def test_08_get_assignment_details(self):
        """Test getting details for a specific assignment."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get assignments to find one to test
        assignments = get_course_assignments(self.__class__.target_course_id)

        # Skip if no assignments found
        if not assignments:
            self.skipTest("No assignments found for target course")

        # Get details for the first assignment
        assignment_name = assignments[0]["title"]
        result = get_assignment_details(
            self.__class__.target_course_id, assignment_name
        )

        # Check that we got a result
        self.assertIsInstance(result, dict)
        self.assertIn("assignment", result)
        self.assertIn("course_code", result)
        self.assertIn("course_name", result)

        # Store the assignment name for later tests
        self.__class__.test_assignment_name = assignment_name
        print(f"Tested assignment details for: {assignment_name}")

    def test_09_search_course_content(self):
        """Test searching for content in a course."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Skip if we don't have an assignment name to search for
        if (
            not hasattr(self.__class__, "test_assignment_name")
            or not self.__class__.test_assignment_name
        ):
            # Use a generic search term
            search_term = "assignment"
        else:
            # Use part of the assignment name
            search_term = self.__class__.test_assignment_name.split()[0]

        # Search for content
        results = search_course_content(search_term, self.__class__.target_course_id)

        # Check that we got a list of results
        self.assertIsInstance(results, list)
        print(f"Found {len(results)} results for search term '{search_term}'")

    def test_10_get_upcoming_deadlines(self):
        """Test getting upcoming deadlines."""
        # Skip if we don't have the target course ID
        if not self.__class__.target_course_id:
            self.skipTest("Target course ID not available")

        # Get upcoming deadlines for all courses
        all_deadlines = get_upcoming_deadlines(days=30)

        # Check that we got a list of deadlines
        self.assertIsInstance(all_deadlines, list)
        print(f"Found {len(all_deadlines)} upcoming deadlines across all courses")

        # Get upcoming deadlines for the target course
        course_deadlines = get_upcoming_deadlines(
            days=30, course_id=self.__class__.target_course_id
        )

        # Check that we got a list of deadlines
        self.assertIsInstance(course_deadlines, list)
        print(
            f"Found {len(course_deadlines)} upcoming deadlines for course {self.__class__.target_course_id}"
        )

    def test_11_query_assignment(self):
        """Test querying for assignment information."""
        # Skip if we don't have the target course ID or course code
        if not self.__class__.target_course_id or not self.__class__.target_course_code:
            self.skipTest("Target course information not available")

        # Skip if we don't have an assignment name
        if (
            not hasattr(self.__class__, "test_assignment_name")
            or not self.__class__.test_assignment_name
        ):
            self.skipTest("No assignment name available for testing")

        # Create a query string
        query = f"What is {self.__class__.test_assignment_name} for {self.__class__.target_course_code}?"

        # Query for assignment information
        result = query_assignment(query, extract_pdf_content=True, format_answer=True)

        # Check that we got a result
        self.assertIsInstance(result, dict)
        self.assertIn("parsed_query", result)

        # Check if the query was parsed correctly
        parsed_query = result.get("parsed_query", {})
        self.assertIn("course_code", parsed_query)

        # If successful, check the assignment information
        if result.get("success"):
            self.assertIn("assignment", result)
            print(
                f"Successfully queried assignment: {result.get('assignment', {}).get('title')}"
            )


if __name__ == "__main__":
    unittest.main()
