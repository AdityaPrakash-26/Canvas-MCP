"""
Tests for Canvas API client and database integration.
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Import from the canvas_mcp package
from canvas_mcp.canvas_client import CanvasClient


class TestCanvasClient(unittest.TestCase):
    """Test suite for the Canvas client functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Create test database schema
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Create minimal schema for testing
        self._create_test_schema()

        # Set up the client with mock Canvas API
        self.api_key = "test_api_key"
        self.api_url = "https://test.instructure.com"

        # Patch the Canvas class to avoid actual API calls
        self.canvas_patch = patch('canvas_mcp.canvas_client.Canvas')
        self.mock_canvas_class = self.canvas_patch.start()
        self.mock_canvas = self.mock_canvas_class.return_value

        # Initialize the client
        self.client = CanvasClient(self.db_path, self.api_key, self.api_url)
        self.client.canvas = self.mock_canvas  # Use the mocked Canvas instance

    def tearDown(self):
        """Clean up test environment after each test."""
        self.canvas_patch.stop()
        self.conn.close()
        os.unlink(self.db_path)

    def _create_test_schema(self):
        """Create a minimal test database schema."""
        # Create courses table
        self.cursor.execute("""
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY,
            canvas_course_id INTEGER UNIQUE NOT NULL,
            course_code TEXT NOT NULL,
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
        self.cursor.execute("""
        CREATE TABLE syllabi (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            content TEXT,
            parsed_content TEXT,
            is_parsed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)

        # Create assignments table
        self.cursor.execute("""
        CREATE TABLE assignments (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_assignment_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            assignment_type TEXT,
            due_date TIMESTAMP,
            available_from TIMESTAMP,
            available_until TIMESTAMP,
            points_possible REAL,
            submission_types TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE (course_id, canvas_assignment_id)
        )
        """)

        # Create modules table
        self.cursor.execute("""
        CREATE TABLE modules (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_module_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            unlock_date TIMESTAMP,
            position INTEGER,
            require_sequential_progress BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE (course_id, canvas_module_id)
        )
        """)

        # Create calendar_events table
        self.cursor.execute("""
        CREATE TABLE calendar_events (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            event_type TEXT NOT NULL,
            source_type TEXT,
            source_id INTEGER,
            event_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP,
            all_day BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)

        # Create user_courses table for opt-out functionality
        self.cursor.execute("""
        CREATE TABLE user_courses (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            indexing_opt_out BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE (user_id, course_id)
        )
        """)

        # Create announcements table
        self.cursor.execute("""
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_announcement_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            posted_by TEXT,
            posted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)

        self.conn.commit()

    def test_connect_db(self):
        """Test that the database connection is successful."""
        conn, cursor = self.client.connect_db()
        self.assertIsInstance(conn, sqlite3.Connection)
        self.assertIsInstance(cursor, sqlite3.Cursor)
        conn.close()

    def test_sync_courses(self):
        """Test syncing courses from Canvas to the database."""
        # Mock user and courses
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        self.mock_canvas.get_current_user.return_value = mock_user

        # Create mock courses
        mock_course1 = MagicMock()
        mock_course1.id = 12345
        mock_course1.name = "Test Course 1"
        mock_course1.course_code = "TST101"

        mock_course2 = MagicMock()
        mock_course2.id = 67890
        mock_course2.name = "Test Course 2"
        mock_course2.course_code = "TST102"

        # Mock Canvas API responses - now user directly gets courses
        self.mock_canvas.get_current_user.return_value.get_courses = MagicMock(
            return_value=[mock_course1, mock_course2]
        )

        # Mock detailed course info
        mock_detailed_course1 = MagicMock()
        mock_detailed_course1.teacher = "Test Instructor"
        mock_detailed_course1.description = "Course description"
        mock_detailed_course1.start_at = "2025-01-10T00:00:00Z"
        mock_detailed_course1.end_at = "2025-05-10T00:00:00Z"
        mock_detailed_course1.syllabus_body = "<p>This is the syllabus content</p>"

        mock_detailed_course2 = MagicMock()
        mock_detailed_course2.teacher = "Another Instructor"
        mock_detailed_course2.description = "Another description"
        mock_detailed_course2.start_at = "2025-01-15T00:00:00Z"
        mock_detailed_course2.end_at = "2025-05-15T00:00:00Z"
        mock_detailed_course2.syllabus_body = "<p>Another syllabus content</p>"

        # Configure mock to return detailed courses
        def get_course_side_effect(course_id):
            if course_id == 12345:
                return mock_detailed_course1
            elif course_id == 67890:
                return mock_detailed_course2
            else:
                raise ValueError(f"Unknown course ID: {course_id}")

        self.mock_canvas.get_course.side_effect = get_course_side_effect

        # Run the sync
        course_ids = self.client.sync_courses()

        # Verify courses were added to database
        conn, cursor = self.client.connect_db()
        cursor.execute("SELECT * FROM courses")
        courses = cursor.fetchall()
        self.assertEqual(len(courses), 2)

        # Verify syllabus content was saved
        cursor.execute("SELECT * FROM syllabi")
        syllabi = cursor.fetchall()
        self.assertEqual(len(syllabi), 2)

        conn.close()

        # Verify the API was called with expected parameters
        self.mock_canvas.get_current_user.assert_called()
        self.mock_canvas.get_current_user.return_value.get_courses.assert_called_once()
        self.assertEqual(self.mock_canvas.get_course.call_count, 2)

        # Verify correct return value
        self.assertEqual(len(course_ids), 2)

    def test_sync_courses_with_term_filter(self):
        """Test syncing courses with term filtering."""
        # Mock user and courses with term IDs
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        self.mock_canvas.get_current_user.return_value = mock_user

        # Create mock courses with different enrollment term IDs
        mock_course1 = MagicMock()
        mock_course1.id = 12345
        mock_course1.name = "Term 1 Course"
        mock_course1.course_code = "TST101"
        mock_course1.enrollment_term_id = 1

        mock_course2 = MagicMock()
        mock_course2.id = 67890
        mock_course2.name = "Term 2 Course"
        mock_course2.course_code = "TST102"
        mock_course2.enrollment_term_id = 2

        mock_course3 = MagicMock()
        mock_course3.id = 13579
        mock_course3.name = "Term 3 Course"
        mock_course3.course_code = "TST103"
        mock_course3.enrollment_term_id = 3  # Latest term

        # Mock Canvas API responses
        self.mock_canvas.get_current_user.return_value.get_courses = MagicMock(
            return_value=[mock_course1, mock_course2, mock_course3]
        )

        # Mock detailed course info
        mock_detailed_course1 = MagicMock()
        mock_detailed_course1.teacher = "Test Instructor"
        mock_detailed_course1.description = "Course description"

        mock_detailed_course2 = MagicMock()
        mock_detailed_course2.teacher = "Another Instructor"
        mock_detailed_course2.description = "Another description"

        mock_detailed_course3 = MagicMock()
        mock_detailed_course3.teacher = "Latest Instructor"
        mock_detailed_course3.description = "Latest description"

        # Configure mock to return detailed courses
        def get_course_side_effect(course_id):
            if course_id == 12345:
                return mock_detailed_course1
            elif course_id == 67890:
                return mock_detailed_course2
            elif course_id == 13579:
                return mock_detailed_course3
            else:
                raise ValueError(f"Unknown course ID: {course_id}")

        self.mock_canvas.get_course.side_effect = get_course_side_effect

        # Test case 1: Filter for specific term (term_id=2)
        self.client.sync_courses(term_id=2)

        # Verify only term 2 course was added
        conn, cursor = self.client.connect_db()
        cursor.execute("SELECT * FROM courses")
        courses = cursor.fetchall()
        self.assertEqual(len(courses), 1)

        # Reset database for next test
        cursor.execute("DELETE FROM courses")
        cursor.execute("DELETE FROM syllabi")
        conn.commit()

        # Test case 2: Filter for latest term (term_id=-1)
        self.client.sync_courses(term_id=-1)

        # Verify only term 3 course (latest) was added
        cursor.execute("SELECT * FROM courses")
        courses = cursor.fetchall()
        self.assertEqual(len(courses), 1)

        # Verify it's the correct course (term 3)
        cursor.execute("SELECT canvas_course_id FROM courses")
        canvas_id = cursor.fetchone()[0]
        self.assertEqual(canvas_id, 13579)  # The ID of the term 3 course

        conn.close()

    def test_sync_assignments(self):
        """Test syncing assignments from Canvas to the database."""
        # First create a course in the database
        conn, cursor = self.client.connect_db()
        cursor.execute(
            "INSERT INTO courses (canvas_course_id, course_code, course_name) VALUES (?, ?, ?)",
            (12345, "TST101", "Test Course")
        )
        conn.commit()

        # Get the local course ID
        cursor.execute("SELECT id FROM courses WHERE canvas_course_id = ?", (12345,))
        local_course_id = cursor.fetchone()[0]
        conn.close()

        # Mock Canvas API course and assignments
        mock_course = MagicMock()

        # Create mock assignments
        mock_assignment1 = MagicMock()
        mock_assignment1.id = 9876
        mock_assignment1.name = "Assignment 1"
        mock_assignment1.description = "Description for assignment 1"
        mock_assignment1.due_at = "2025-02-15T23:59:00Z"
        mock_assignment1.unlock_at = "2025-02-01T00:00:00Z"
        mock_assignment1.lock_at = "2025-02-16T23:59:00Z"
        mock_assignment1.points_possible = 100
        mock_assignment1.submission_types = ["online_text_entry", "online_upload"]

        mock_assignment2 = MagicMock()
        mock_assignment2.id = 5432
        mock_assignment2.name = "Quiz 1"
        mock_assignment2.description = "Description for quiz 1"
        mock_assignment2.due_at = "2025-03-01T23:59:00Z"
        mock_assignment2.unlock_at = "2025-02-20T00:00:00Z"
        mock_assignment2.lock_at = "2025-03-02T23:59:00Z"
        mock_assignment2.points_possible = 50
        mock_assignment2.submission_types = ["online_quiz"]

        # Set up mock returns
        self.mock_canvas.get_course.return_value = mock_course
        mock_course.get_assignments.return_value = [mock_assignment1, mock_assignment2]

        # Run the sync
        course_ids = [local_course_id]
        assignment_count = self.client.sync_assignments(course_ids)

        # Verify assignments were added to database
        conn, cursor = self.client.connect_db()
        cursor.execute("SELECT * FROM assignments")
        assignments = cursor.fetchall()
        self.assertEqual(len(assignments), 2)

        # Verify calendar events were created
        cursor.execute("SELECT * FROM calendar_events")
        events = cursor.fetchall()
        self.assertEqual(len(events), 2)

        conn.close()

        # Verify correct return value
        self.assertEqual(assignment_count, 2)

    def test_sync_modules(self):
        """Test syncing modules from Canvas to the database."""
        # First create a course in the database
        conn, cursor = self.client.connect_db()
        cursor.execute(
            "INSERT INTO courses (canvas_course_id, course_code, course_name) VALUES (?, ?, ?)",
            (12345, "TST101", "Test Course")
        )
        conn.commit()

        # Get the local course ID
        cursor.execute("SELECT id FROM courses WHERE canvas_course_id = ?", (12345,))
        local_course_id = cursor.fetchone()[0]
        conn.close()

        # Mock Canvas API course and modules
        mock_course = MagicMock()

        # Create mock modules
        mock_module1 = MagicMock()
        mock_module1.id = 1111
        mock_module1.name = "Module 1"
        mock_module1.position = 1

        mock_module2 = MagicMock()
        mock_module2.id = 2222
        mock_module2.name = "Module 2"
        mock_module2.position = 2

        # Mock module items
        mock_item1 = MagicMock()
        mock_item1.id = 101
        mock_item1.title = "Item 1"
        mock_item1.type = "Assignment"
        mock_item1.position = 1

        mock_item2 = MagicMock()
        mock_item2.id = 102
        mock_item2.title = "Item 2"
        mock_item2.type = "Page"
        mock_item2.position = 2

        # Set up mock returns
        self.mock_canvas.get_course.return_value = mock_course
        mock_course.get_modules.return_value = [mock_module1, mock_module2]

        # Create a table for module items
        conn, cursor = self.client.connect_db()
        cursor.execute("""
        CREATE TABLE module_items (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            canvas_item_id INTEGER,
            title TEXT NOT NULL,
            item_type TEXT NOT NULL,
            position INTEGER,
            url TEXT,
            page_url TEXT,
            content_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        conn.close()

        # Mock get_module_items method
        mock_module1.get_module_items = MagicMock(return_value=[mock_item1, mock_item2])
        mock_module2.get_module_items = MagicMock(return_value=[])

        # Run the sync
        course_ids = [local_course_id]
        module_count = self.client.sync_modules(course_ids)

        # Verify modules were added to database
        conn, cursor = self.client.connect_db()
        cursor.execute("SELECT * FROM modules")
        modules = cursor.fetchall()
        self.assertEqual(len(modules), 2)

        # Verify correct return value
        self.assertEqual(module_count, 2)

        conn.close()

    def test_sync_announcements(self):
        """Test syncing announcements from Canvas to the database."""
        # First create a course in the database
        conn, cursor = self.client.connect_db()
        cursor.execute(
            "INSERT INTO courses (canvas_course_id, course_code, course_name) VALUES (?, ?, ?)",
            (12345, "TST101", "Test Course")
        )
        conn.commit()

        # Get the local course ID
        cursor.execute("SELECT id FROM courses WHERE canvas_course_id = ?", (12345,))
        local_course_id = cursor.fetchone()[0]
        conn.close()

        # Mock Canvas API course and announcements
        mock_course = MagicMock()

        # Create mock announcements
        mock_announcement1 = MagicMock()
        mock_announcement1.id = 3333
        mock_announcement1.title = "Announcement 1"
        mock_announcement1.message = "This is the first announcement"
        mock_announcement1.posted_at = "2025-01-15T10:00:00Z"
        mock_announcement1.author_name = "Professor Smith"

        mock_announcement2 = MagicMock()
        mock_announcement2.id = 4444
        mock_announcement2.title = "Announcement 2"
        mock_announcement2.message = "This is the second announcement"
        mock_announcement2.posted_at = "2025-01-20T14:30:00Z"
        mock_announcement2.author_name = "Professor Smith"

        # Set up mock returns
        self.mock_canvas.get_course.return_value = mock_course
        mock_course.get_discussion_topics.return_value = [mock_announcement1, mock_announcement2]

        # Run the sync
        course_ids = [local_course_id]
        announcement_count = self.client.sync_announcements(course_ids)

        # Verify announcements were added to database
        conn, cursor = self.client.connect_db()
        cursor.execute("SELECT * FROM announcements")
        announcements = cursor.fetchall()
        self.assertEqual(len(announcements), 2)

        # Verify correct return value
        self.assertEqual(announcement_count, 2)

        conn.close()

    def test_sync_all(self):
        """Test syncing all data from Canvas to the database."""
        # Mock all necessary Canvas API responses
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        self.mock_canvas.get_current_user.return_value = mock_user

        # Create mock courses
        mock_course = MagicMock()
        mock_course.id = 12345
        mock_course.name = "Test Course"
        mock_course.course_code = "TST101"

        # Mock get_courses directly on user now
        self.mock_canvas.get_current_user.return_value.get_courses = MagicMock(
            return_value=[mock_course]
        )

        # Mock detailed course
        mock_detailed_course = MagicMock()
        mock_detailed_course.teacher = "Test Instructor"
        mock_detailed_course.description = "Course description"
        mock_detailed_course.start_at = "2025-01-10T00:00:00Z"
        mock_detailed_course.end_at = "2025-05-10T00:00:00Z"
        mock_detailed_course.syllabus_body = "<p>This is the syllabus content</p>"

        self.mock_canvas.get_course.return_value = mock_detailed_course

        # Mock assignments
        mock_assignment = MagicMock()
        mock_assignment.id = 9876
        mock_assignment.name = "Assignment 1"
        mock_assignment.description = "Description for assignment 1"
        mock_assignment.due_at = "2025-02-15T23:59:00Z"
        mock_assignment.unlock_at = "2025-02-01T00:00:00Z"
        mock_assignment.lock_at = "2025-02-16T23:59:00Z"
        mock_assignment.points_possible = 100
        mock_assignment.submission_types = ["online_text_entry", "online_upload"]

        mock_detailed_course.get_assignments.return_value = [mock_assignment]

        # Mock modules
        mock_module = MagicMock()
        mock_module.id = 1111
        mock_module.name = "Module 1"
        mock_module.position = 1
        mock_module.get_module_items = MagicMock(return_value=[])

        mock_detailed_course.get_modules.return_value = [mock_module]

        # Mock announcements
        mock_announcement = MagicMock()
        mock_announcement.id = 3333
        mock_announcement.title = "Announcement 1"
        mock_announcement.message = "This is an announcement"
        mock_announcement.posted_at = "2025-01-15T10:00:00Z"
        mock_announcement.author_name = "Professor Smith"

        mock_detailed_course.get_discussion_topics.return_value = [mock_announcement]

        # Run the sync_all method
        result = self.client.sync_all()

        # Verify data was added to database
        conn, cursor = self.client.connect_db()

        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]
        self.assertEqual(course_count, 1)

        cursor.execute("SELECT COUNT(*) FROM syllabi")
        syllabi_count = cursor.fetchone()[0]
        self.assertEqual(syllabi_count, 1)

        # Create module_items table if needed for testing
        try:
            cursor.execute("""
            CREATE TABLE module_items (
                id INTEGER PRIMARY KEY,
                module_id INTEGER NOT NULL,
                canvas_item_id INTEGER,
                title TEXT NOT NULL,
                item_type TEXT NOT NULL,
                position INTEGER,
                url TEXT,
                page_url TEXT,
                content_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
            """)
            conn.commit()
        except sqlite3.OperationalError:
            # Table already exists
            pass

        # Verify the result
        self.assertEqual(result["courses"], 1)
        self.assertEqual(result["assignments"], 1)
        self.assertEqual(result["modules"], 1)
        self.assertEqual(result["announcements"], 1)

        conn.close()

    def test_sync_all_with_term_filter(self):
        """Test syncing all data with term filtering."""
        # Mock user and courses with term IDs
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        self.mock_canvas.get_current_user.return_value = mock_user

        # Create mock courses with different enrollment term IDs
        mock_course1 = MagicMock()
        mock_course1.id = 12345
        mock_course1.name = "Term 1 Course"
        mock_course1.course_code = "TST101"
        mock_course1.enrollment_term_id = 1

        mock_course2 = MagicMock()
        mock_course2.id = 67890
        mock_course2.name = "Term 2 Course"
        mock_course2.course_code = "TST102"
        mock_course2.enrollment_term_id = 2

        # Mock Canvas API responses
        self.mock_canvas.get_current_user.return_value.get_courses = MagicMock(
            return_value=[mock_course1, mock_course2]
        )

        # Mock detailed course info
        mock_detailed_course1 = MagicMock()
        mock_detailed_course1.teacher = "Test Instructor"
        mock_detailed_course1.description = "Course description"
        mock_detailed_course1.syllabus_body = "<p>Syllabus content</p>"
        mock_detailed_course1.get_assignments = MagicMock(return_value=[])
        mock_detailed_course1.get_modules = MagicMock(return_value=[])
        mock_detailed_course1.get_discussion_topics = MagicMock(return_value=[])

        mock_detailed_course2 = MagicMock()
        mock_detailed_course2.teacher = "Term 2 Instructor"
        mock_detailed_course2.description = "Term 2 description"
        mock_detailed_course2.syllabus_body = "<p>Term 2 syllabus</p>"

        # Set up mock assignment, module, and announcement for term 2 course only
        mock_assignment = MagicMock()
        mock_assignment.id = 9876
        mock_assignment.name = "Assignment 1"
        mock_assignment.due_at = "2025-02-15T23:59:00Z"
        mock_assignment.submission_types = ["online_text_entry"]

        mock_module = MagicMock()
        mock_module.id = 1111
        mock_module.name = "Module 1"
        mock_module.position = 1
        mock_module.get_module_items = MagicMock(return_value=[])

        mock_announcement = MagicMock()
        mock_announcement.id = 3333
        mock_announcement.title = "Announcement 1"
        mock_announcement.message = "This is an announcement"

        # Add the mocks to the second course
        mock_detailed_course2.get_assignments = MagicMock(return_value=[mock_assignment])
        mock_detailed_course2.get_modules = MagicMock(return_value=[mock_module])
        mock_detailed_course2.get_discussion_topics = MagicMock(return_value=[mock_announcement])

        # Configure mock to return detailed courses
        def get_course_side_effect(course_id):
            if course_id == 12345:
                return mock_detailed_course1
            elif course_id == 67890:
                return mock_detailed_course2
            else:
                raise ValueError(f"Unknown course ID: {course_id}")

        self.mock_canvas.get_course.side_effect = get_course_side_effect

        # Run sync_all with term_id=2 filter - should only include term 2 course
        result = self.client.sync_all(term_id=2)

        # Verify only term 2 data was synced
        conn, cursor = self.client.connect_db()

        # Should have 1 course
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]
        self.assertEqual(course_count, 1)

        # Verify it's the correct course (term 2)
        cursor.execute("SELECT canvas_course_id FROM courses")
        canvas_id = cursor.fetchone()[0]
        self.assertEqual(canvas_id, 67890)  # The ID of the term 2 course

        # Verify the counts in the returned result
        self.assertEqual(result["courses"], 1)  # Only 1 course
        self.assertEqual(result["assignments"], 1)  # Only term 2's assignment
        self.assertEqual(result["modules"], 1)  # Only term 2's module
        self.assertEqual(result["announcements"], 1)  # Only term 2's announcement

        conn.close()


if __name__ == "__main__":
    unittest.main()
