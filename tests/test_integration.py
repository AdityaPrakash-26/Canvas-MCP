"""
Integration tests for Canvas MCP server.

This test file covers all major code paths in the Canvas MCP server,
focusing on the SP25_CS_540_1 course (Canvas Course ID: 146127).
"""

import os
import sys
import unittest
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test database path
TEST_DB_PATH = Path(__file__).parent / "test_data" / "test_canvas_mcp.db"

# Set environment variable to use test database BEFORE importing server components
os.environ["CANVAS_MCP_TEST_DB"] = str(TEST_DB_PATH)
print(f"Test environment variable CANVAS_MCP_TEST_DB set to: {TEST_DB_PATH}")

# Import server components AFTER setting the environment variable
from init_db import create_database  # Import database creation function
from src.canvas_mcp.server import (
    extract_text_from_course_file,
    get_assignment_details,
    get_course_announcements,
    get_course_assignments,
    get_course_files,
    get_course_list,
    get_course_modules,
    get_syllabus,
    get_syllabus_file,
    get_upcoming_deadlines,
    search_course_content,
    sync_canvas_data,
)

# Import database utilities
from src.canvas_mcp.utils.db_manager import DatabaseManager


class TestCanvasMCPIntegration(unittest.TestCase):
    """Integration tests for Canvas MCP server."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Ensure test data directory exists
        os.makedirs(TEST_DB_PATH.parent, exist_ok=True)

        # Only create the database if it doesn't exist
        # This allows us to reuse the database across test runs
        if not TEST_DB_PATH.exists():
            print(f"Test database not found, will create: {TEST_DB_PATH}")
            # Initialize the test database using the correct path
            # Note: Environment variable was already set at module level
            print(f"Initializing test database at: {TEST_DB_PATH}")
            create_database(str(TEST_DB_PATH))
            print("Test database initialized.")
        else:
            print(f"Using existing test database: {TEST_DB_PATH}")

        # Create database manager specifically for test verification steps
        cls.db_manager = DatabaseManager(TEST_DB_PATH)

        # Store the target course code and ID
        cls.target_course_code = "SP25_CS_540_1"
        # Full Canvas ID with institution prefix
        cls.target_canvas_course_id = 65920000000146127

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

    def test_00_client_initialization(self):
        """Test that the canvas client is properly initialized with the test database."""
        # Import the global canvas_client from server to verify it's using the test database
        from src.canvas_mcp.server import DB_PATH, canvas_client

        # Verify the client is using the test database
        self.assertEqual(
            str(canvas_client.db_path),
            str(TEST_DB_PATH),
            "Canvas client is not using the test database",
        )

        # Verify the server's DB_PATH is also set to the test database
        self.assertEqual(
            str(DB_PATH),
            str(TEST_DB_PATH),
            "Server DB_PATH is not set to the test database",
        )

        print(
            f"Confirmed canvas_client is using test database: {canvas_client.db_path}"
        )
        print(f"Confirmed server DB_PATH is set to: {DB_PATH}")

    def test_01_sync_canvas_data(self):
        """Test synchronizing data from Canvas."""
        # Ensure Canvas API key is available
        self.assertTrue(
            os.environ.get("CANVAS_API_KEY"),
            "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests",
        )

        # Run the sync with Canvas API
        print("Running sync_canvas_data...")
        result = sync_canvas_data(force=True)
        print(f"Sync result: {result}")

        # Check that we got some data
        self.assertIsInstance(result, dict)
        # Check for potential error key first
        self.assertNotIn(
            "error", result, f"Sync failed with error: {result.get('error')}"
        )
        self.assertIn("courses", result)
        # Allow for 0 if the API key only has access to opted-out courses
        self.assertGreaterEqual(result["courses"], 0)
        if result["courses"] == 0:
            print(
                "Warning: 0 courses synced. Check API key permissions and term filters."
            )
        else:
            print(f"Synced {result['courses']} courses.")

        # Verify our target course exists after sync
        self.conn, self.cursor = (
            self.db_manager.connect()
        )  # Reconnect to get fresh data
        print(
            f"Verifying target course with Canvas ID: {self.__class__.target_canvas_course_id}"
        )
        self.cursor.execute(
            "SELECT id, course_code FROM courses WHERE canvas_course_id = ?",
            (self.__class__.target_canvas_course_id,),
        )
        course_data = self.cursor.fetchone()

        # The target course must exist
        self.assertIsNotNone(
            course_data,
            f"Target course with Canvas ID {self.__class__.target_canvas_course_id} not found after sync",
        )

        self.__class__.target_course_id = course_data["id"]
        # Update the code in case it changed during sync
        self.__class__.target_course_code = course_data["course_code"]
        print(
            f"Confirmed target course exists. Internal ID: {self.__class__.target_course_id}, Code: {self.__class__.target_course_code}"
        )
        self.conn.close()  # Close connection after verification

    def test_02_get_course_list(self):
        """Test getting the list of courses."""
        # Get course list
        courses = get_course_list()

        # Check that we got a list of courses
        self.assertIsInstance(courses, list)
        self.assertGreater(len(courses), 0, "No courses found in the database")

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

        # Ensure we found the target course
        self.assertIsNotNone(
            target_course,
            f"Target course {self.__class__.target_course_code} not found in course list",
        )

        # Store its internal ID
        self.__class__.target_course_id = target_course["id"]
        print(
            f"Found target course with internal ID: {self.__class__.target_course_id}"
        )

    def test_03_get_course_assignments(self):
        """Test getting assignments for a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get assignments
        assignments = get_course_assignments(self.__class__.target_course_id)

        # Check that we got a list of assignments
        self.assertIsInstance(assignments, list)
        self.assertGreater(
            len(assignments),
            0,
            f"No assignments found for course {self.__class__.target_course_id}",
        )
        print(
            f"Found {len(assignments)} assignments for course {self.__class__.target_course_id}"
        )

        # Print some assignment details for debugging
        print(f"First assignment: {assignments[0].get('title')}")

    def test_04_get_course_modules(self):
        """Test getting modules for a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get modules without items
        modules = get_course_modules(
            self.__class__.target_course_id, include_items=False
        )

        # Check that we got a list of modules
        self.assertIsInstance(modules, list)
        print(
            f"Found {len(modules)} modules for course {self.__class__.target_course_id}"
        )

        # If there are no modules, that's okay for this course
        if len(modules) == 0:
            print(
                "No modules found for this course, which is expected for some courses."
            )
            return

        # Get modules with items (only if we have modules)
        modules_with_items = get_course_modules(
            self.__class__.target_course_id, include_items=True
        )

        # Check that we got a list of modules with items
        self.assertIsInstance(modules_with_items, list)
        self.assertEqual(
            len(modules_with_items),
            len(modules),
            "Module count mismatch between calls with and without items",
        )

        # Check if any modules have items
        has_items = any(
            "items" in module and module["items"] for module in modules_with_items
        )
        print(f"Modules with items: {has_items}")

    def test_05_get_syllabus(self):
        """Test getting the syllabus for a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get syllabus in raw format
        syllabus_raw = get_syllabus(self.__class__.target_course_id, format="raw")

        # Check that we got a syllabus
        self.assertIsInstance(syllabus_raw, dict)
        self.assertIn("content", syllabus_raw)
        self.assertIn("content_type", syllabus_raw)
        self.assertNotEqual(syllabus_raw["content"], "", "Syllabus content is empty")

        # Get syllabus in parsed format
        syllabus_parsed = get_syllabus(self.__class__.target_course_id, format="parsed")

        # Check that we got a syllabus
        self.assertIsInstance(syllabus_parsed, dict)
        self.assertIn("content", syllabus_parsed)
        self.assertNotEqual(
            syllabus_parsed["content"], "", "Parsed syllabus content is empty"
        )

    def test_06_get_course_files(self):
        """Test getting files for a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get all files
        files = get_course_files(self.__class__.target_course_id)

        # Check that we got a list of files
        self.assertIsInstance(files, list)
        print(f"Found {len(files)} files for course {self.__class__.target_course_id}")

        # If there are no files, we can't continue with the test
        if len(files) == 0:
            print("No files found for this course, skipping file tests.")
            # Set a dummy URL for later tests to skip
            self.__class__.test_pdf_url = None
            return

        # Get PDF files
        pdf_files = get_course_files(self.__class__.target_course_id, file_type="pdf")

        # Check that we got a list of PDF files
        self.assertIsInstance(pdf_files, list)
        print(
            f"Found {len(pdf_files)} PDF files for course {self.__class__.target_course_id}"
        )

        # If there are no PDF files, we can't continue with the test
        if len(pdf_files) == 0:
            print("No PDF files found for this course, skipping PDF tests.")
            # Set a dummy URL for later tests to skip
            self.__class__.test_pdf_url = None
            return

        # Store a PDF file URL for later tests
        self.__class__.test_pdf_url = pdf_files[0].get("url")
        self.assertIsNotNone(
            self.__class__.test_pdf_url, "PDF file URL is required for later tests"
        )
        print(f"Found PDF file: {pdf_files[0].get('name')}")

    def test_07_extract_text_from_course_file(self):
        """Test extracting text from a course file."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Check if we have a PDF file URL from the previous test
        if (
            not hasattr(self.__class__, "test_pdf_url")
            or self.__class__.test_pdf_url is None
        ):
            print("No PDF file URL available, skipping text extraction test.")
            return

        # Extract text from the file
        result = extract_text_from_course_file(
            self.__class__.target_course_id,
            self.__class__.test_pdf_url,
            file_type="pdf",
        )

        # Check that we got a successful result
        self.assertIsInstance(result, dict)
        self.assertTrue(
            result.get("success"), f"Failed to extract text: {result.get('error')}"
        )

        # Check the text content
        self.assertIn("text", result)
        self.assertIsInstance(result["text"], str)
        self.assertGreater(len(result["text"]), 0, "Extracted text is empty")
        print(f"Extracted {result.get('text_length', 0)} characters of text")

    def test_08_get_assignment_details(self):
        """Test getting details for a specific assignment."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get assignments to find one to test
        assignments = get_course_assignments(self.__class__.target_course_id)

        # Ensure we have assignments
        self.assertGreater(
            len(assignments), 0, "No assignments found for target course"
        )

        # Get details for the first assignment
        assignment_name = assignments[0]["title"]
        result = get_assignment_details(
            self.__class__.target_course_id, assignment_name
        )

        # Check that we got a result
        self.assertIsInstance(result, dict)
        self.assertNotIn(
            "error", result, f"Error getting assignment details: {result.get('error')}"
        )
        self.assertIn("assignment", result)
        self.assertIn("course_code", result)
        self.assertIn("course_name", result)

        # Store the assignment name for later tests
        self.__class__.test_assignment_name = assignment_name
        print(f"Tested assignment details for: {assignment_name}")

    def test_09_search_course_content(self):
        """Test searching for content in a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Check if we have an assignment name from the previous test
        # If not, use a default search term that's likely to find something
        if (
            hasattr(self.__class__, "test_assignment_name")
            and self.__class__.test_assignment_name
        ):
            # Use part of the assignment name as search term
            search_term = self.__class__.test_assignment_name.split()[0]
        else:
            # Use a generic term that's likely to find something
            search_term = (
                "First"  # Most courses have something with "First" in the title
            )

        # Search for content
        results = search_course_content(search_term, self.__class__.target_course_id)

        # Check that we got a list of results
        self.assertIsInstance(results, list)
        self.assertGreater(
            len(results), 0, f"No results found for search term '{search_term}'"
        )
        print(f"Found {len(results)} results for search term '{search_term}'")

    def test_10_get_upcoming_deadlines(self):
        """Test getting upcoming deadlines."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get upcoming deadlines for all courses
        all_deadlines = get_upcoming_deadlines(days=30)

        # Check that we got a list of deadlines
        self.assertIsInstance(all_deadlines, list)
        self.assertGreater(
            len(all_deadlines), 0, "No upcoming deadlines found across all courses"
        )
        print(f"Found {len(all_deadlines)} upcoming deadlines across all courses")

        # Get upcoming deadlines for the target course
        course_deadlines = get_upcoming_deadlines(
            days=30, course_id=self.__class__.target_course_id
        )

        # Check that we got a list of deadlines
        self.assertIsInstance(course_deadlines, list)
        self.assertGreater(
            len(course_deadlines),
            0,
            f"No upcoming deadlines found for course {self.__class__.target_course_id}",
        )
        print(
            f"Found {len(course_deadlines)} upcoming deadlines for course {self.__class__.target_course_id}"
        )

    def test_11_get_course_announcements(self):
        """Test getting course announcements."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get announcements for the target course
        announcements = get_course_announcements(self.__class__.target_course_id)

        # Check that we got a list of announcements
        self.assertIsInstance(announcements, list)
        print(
            f"Found {len(announcements)} announcements for course {self.__class__.target_course_id}"
        )

        # It's okay if there are no announcements, but we should still get a list
        if len(announcements) > 0:
            # Check the structure of the first announcement
            first_announcement = announcements[0]
            self.assertIn("title", first_announcement)
            self.assertIn("content", first_announcement)
            self.assertIn("posted_at", first_announcement)
            print(f"First announcement: {first_announcement.get('title')}")

    def test_12_get_syllabus_file(self):
        """Test getting syllabus file for a course."""
        # Ensure we have the target course ID
        self.assertIsNotNone(
            self.__class__.target_course_id, "Target course ID is required"
        )

        # Get syllabus file for the target course
        result = get_syllabus_file(
            self.__class__.target_course_id, extract_content=False
        )

        # Check that we got a result
        self.assertIsInstance(result, dict)
        print(f"Syllabus file search result: {result.get('success', False)}")

        # It's okay if no syllabus file is found, but we should still get a valid result
        if result.get("success", False):
            # Check the structure of the result
            self.assertIn("syllabus_file", result)
            self.assertIn("all_syllabus_files", result)

            # Check the structure of the syllabus file
            syllabus_file = result["syllabus_file"]
            self.assertIn("name", syllabus_file)
            self.assertIn("url", syllabus_file)
            print(f"Found syllabus file: {syllabus_file.get('name')}")
        else:
            # If no syllabus file was found, check that we got an error message
            self.assertIn("error", result)
            print(f"No syllabus file found: {result.get('error')}")


if __name__ == "__main__":
    print("Starting Canvas MCP Integration Tests...")
    # Ensure API key is checked before running tests
    if not os.environ.get("CANVAS_API_KEY"):
        print("\nERROR: CANVAS_API_KEY environment variable not set.")
        print("Please set the CANVAS_API_KEY to run integration tests.")
        sys.exit(1)  # Exit if key is missing

    unittest.main()
