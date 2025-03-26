"""
Tests for the MCP server implementation.
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Import the modules to test
from canvas_mcp.server import (
    get_upcoming_deadlines,
    get_course_list,
    get_course_assignments,
    get_course_modules,
    get_syllabus,
    get_course_announcements,
    search_course_content,
    opt_out_course,
    db_connect,
    row_to_dict
)


class TestMCPServer(unittest.TestCase):
    """Test suite for MCP server functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create a test database schema
        self._create_test_database()
        
        # Mock the db_connect function to use our test database
        self.db_connect_patch = patch('canvas_mcp.server.db_connect')
        self.mock_db_connect = self.db_connect_patch.start()
        
        # Make db_connect return a connection to our test database
        def mock_db_connect_impl():
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            return conn, cursor
        
        self.mock_db_connect.side_effect = mock_db_connect_impl
        
        # Verify our mock is working
        conn, cursor = mock_db_connect_impl()
        cursor.execute("SELECT * FROM courses")
        courses = cursor.fetchall()
        print(f"Found {len(courses)} courses in test database")
        
        cursor.execute("SELECT * FROM assignments")
        assignments = cursor.fetchall()
        print(f"Found {len(assignments)} assignments in test database")
        
        cursor.execute("SELECT * FROM modules")
        modules = cursor.fetchall()
        print(f"Found {len(modules)} modules in test database")
        
        conn.close()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        self.db_connect_patch.stop()
        
        # Remove the test database
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_database(self):
        """Create a test database with sample data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create necessary tables
        cursor.execute("""
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
        
        cursor.execute("""
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
        
        cursor.execute("""
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
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)
        
        cursor.execute("""
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
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)
        
        cursor.execute("""
        CREATE TABLE module_items (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            canvas_item_id INTEGER,
            title TEXT NOT NULL,
            item_type TEXT NOT NULL,
            content_id INTEGER,
            position INTEGER,
            url TEXT,
            page_url TEXT,
            content_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
        )
        """)
        
        cursor.execute("""
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
        
        cursor.execute("""
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
        
        # Insert sample data
        # Courses
        cursor.execute(
            """
            INSERT INTO courses (
                id, canvas_course_id, course_code, course_name, instructor, 
                description, start_date, end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                12345,
                "CS101",
                "Introduction to Computer Science",
                "Professor Smith",
                "An introduction to computer science concepts",
                "2025-01-15T00:00:00Z",
                "2025-05-15T00:00:00Z"
            )
        )
        
        cursor.execute(
            """
            INSERT INTO courses (
                id, canvas_course_id, course_code, course_name, instructor, 
                description, start_date, end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                67890,
                "MATH200",
                "Calculus II",
                "Professor Johnson",
                "Advanced calculus topics",
                "2025-01-15T00:00:00Z",
                "2025-05-15T00:00:00Z"
            )
        )
        
        # Syllabi
        cursor.execute(
            """
            INSERT INTO syllabi (
                id, course_id, content, parsed_content, is_parsed
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                "<p>This is the CS101 syllabus</p>",
                "This is the CS101 syllabus in plain text format.",
                True
            )
        )
        
        cursor.execute(
            """
            INSERT INTO syllabi (
                id, course_id, content, parsed_content, is_parsed
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                2,
                2,
                "<p>This is the MATH200 syllabus</p>",
                "This is the MATH200 syllabus in plain text format.",
                True
            )
        )
        
        # Assignments
        cursor.execute(
            """
            INSERT INTO assignments (
                id, course_id, canvas_assignment_id, title, description,
                assignment_type, due_date, points_possible
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                101,
                "Programming Assignment 1",
                "Write a simple program in Python",
                "assignment",
                "2025-02-01T23:59:00Z",
                100
            )
        )
        
        cursor.execute(
            """
            INSERT INTO assignments (
                id, course_id, canvas_assignment_id, title, description,
                assignment_type, due_date, points_possible
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                1,
                102,
                "Midterm Exam",
                "Covers material from weeks 1-7",
                "exam",
                "2025-03-01T10:00:00Z",
                200
            )
        )
        
        cursor.execute(
            """
            INSERT INTO assignments (
                id, course_id, canvas_assignment_id, title, description,
                assignment_type, due_date, points_possible
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                2,
                201,
                "Calculus Problem Set 1",
                "Problems 1-20 from Chapter 3",
                "assignment",
                "2025-02-05T23:59:00Z",
                50
            )
        )
        
        # Modules
        cursor.execute(
            """
            INSERT INTO modules (
                id, course_id, canvas_module_id, name, description, position
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                101,
                "Week 1: Introduction",
                "Introduction to the course and basic concepts",
                1
            )
        )
        
        cursor.execute(
            """
            INSERT INTO modules (
                id, course_id, canvas_module_id, name, description, position
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                1,
                102,
                "Week 2: Variables and Data Types",
                "Understanding variables and data types in programming",
                2
            )
        )
        
        # Module Items
        cursor.execute(
            """
            INSERT INTO module_items (
                id, module_id, canvas_item_id, title, item_type, position
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                1001,
                "Introduction Lecture",
                "Page",
                1
            )
        )
        
        cursor.execute(
            """
            INSERT INTO module_items (
                id, module_id, canvas_item_id, title, item_type, position
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                1,
                1002,
                "Getting Started with Python",
                "Assignment",
                2
            )
        )
        
        # Announcements
        cursor.execute(
            """
            INSERT INTO announcements (
                id, course_id, canvas_announcement_id, title, content,
                posted_by, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                2001,
                "Welcome to CS101",
                "Welcome to Introduction to Computer Science. Please read the syllabus.",
                "Professor Smith",
                "2025-01-10T09:00:00Z"
            )
        )
        
        cursor.execute(
            """
            INSERT INTO announcements (
                id, course_id, canvas_announcement_id, title, content,
                posted_by, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                1,
                2002,
                "Office Hours Updated",
                "My office hours have been moved to Thursdays 2-4pm.",
                "Professor Smith",
                "2025-01-15T14:30:00Z"
            )
        )
        
        conn.commit()
        conn.close()
    
    def test_get_upcoming_deadlines(self):
        """Test that upcoming deadlines are correctly retrieved."""
        # Call the function
        deadlines = get_upcoming_deadlines(days=30)
        
        # Verify the result
        self.assertEqual(len(deadlines), 3)
        
        # Verify the deadlines are in chronological order
        self.assertEqual(deadlines[0]['assignment_title'], "Programming Assignment 1")
        self.assertEqual(deadlines[1]['assignment_title'], "Calculus Problem Set 1")
        self.assertEqual(deadlines[2]['assignment_title'], "Midterm Exam")
        
        # Test with course filter
        deadlines = get_upcoming_deadlines(days=30, course_id=1)
        self.assertEqual(len(deadlines), 2)
        self.assertEqual(deadlines[0]['course_code'], "CS101")
        self.assertEqual(deadlines[1]['course_code'], "CS101")
    
    def test_get_course_list(self):
        """Test that course list is correctly retrieved."""
        # Call the function
        courses = get_course_list()
        
        # Verify the result
        self.assertEqual(len(courses), 2)
        self.assertEqual(courses[0]['course_code'], "CS101")
        self.assertEqual(courses[1]['course_code'], "MATH200")
    
    def test_get_course_assignments(self):
        """Test that course assignments are correctly retrieved."""
        # Call the function for CS101
        assignments = get_course_assignments(1)
        
        # Verify the result
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0]['title'], "Programming Assignment 1")
        self.assertEqual(assignments[1]['title'], "Midterm Exam")
        
        # Call the function for MATH200
        assignments = get_course_assignments(2)
        
        # Verify the result
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]['title'], "Calculus Problem Set 1")
    
    def test_get_course_modules(self):
        """Test that course modules are correctly retrieved."""
        # Call the function without items
        modules = get_course_modules(1)
        
        # Verify the result
        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0]['name'], "Week 1: Introduction")
        self.assertEqual(modules[1]['name'], "Week 2: Variables and Data Types")
        
        # Call the function with items
        modules = get_course_modules(1, include_items=True)
        
        # Verify the result
        self.assertEqual(len(modules), 2)
        self.assertEqual(len(modules[0]['items']), 2)
        self.assertEqual(modules[0]['items'][0]['title'], "Introduction Lecture")
        self.assertEqual(modules[0]['items'][1]['title'], "Getting Started with Python")
    
    def test_get_syllabus(self):
        """Test that syllabus content is correctly retrieved."""
        # Call the function with raw format
        syllabus = get_syllabus(1, format="raw")
        
        # Verify the result
        self.assertEqual(syllabus['course_code'], "CS101")
        self.assertEqual(syllabus['content'], "<p>This is the CS101 syllabus</p>")
        
        # Call the function with parsed format
        syllabus = get_syllabus(1, format="parsed")
        
        # Verify the result
        self.assertEqual(syllabus['course_code'], "CS101")
        self.assertEqual(syllabus['content'], "This is the CS101 syllabus in plain text format.")
    
    def test_get_course_announcements(self):
        """Test that course announcements are correctly retrieved."""
        # Call the function
        announcements = get_course_announcements(1)
        
        # Verify the result
        self.assertEqual(len(announcements), 2)
        self.assertEqual(announcements[0]['title'], "Office Hours Updated")
        self.assertEqual(announcements[1]['title'], "Welcome to CS101")
        
        # Test with limit
        announcements = get_course_announcements(1, limit=1)
        
        # Verify the result
        self.assertEqual(len(announcements), 1)
        self.assertEqual(announcements[0]['title'], "Office Hours Updated")
    
    def test_search_course_content(self):
        """Test that course content search works correctly."""
        # Search across all courses
        results = search_course_content("Python")
        
        # Verify the result
        self.assertEqual(len(results), 2)  # Should find in assignment description and module item
        
        # Search in a specific course
        results = search_course_content("Python", course_id=1)
        
        # Verify the result
        self.assertEqual(len(results), 2)
        
        # Search with no matches
        results = search_course_content("nonexistent term")
        
        # Verify the result
        self.assertEqual(len(results), 0)
    
    def test_opt_out_course(self):
        """Test that course opt-out functionality works correctly."""
        # Opt out a course
        result = opt_out_course(1, "test_user", opt_out=True)
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["course_id"], 1)
        self.assertEqual(result["user_id"], "test_user")
        self.assertTrue(result["opted_out"])
        
        # Verify in database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_courses WHERE user_id = ? AND course_id = ?", 
                      ("test_user", 1))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["indexing_opt_out"], 1)  # True in SQLite
        
        conn.close()
        
        # Test opting back in
        result = opt_out_course(1, "test_user", opt_out=False)
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["course_id"], 1)
        self.assertFalse(result["opted_out"])
        
        # Verify in database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_courses WHERE user_id = ? AND course_id = ?", 
                      ("test_user", 1))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["indexing_opt_out"], 0)  # False in SQLite
        
        conn.close()
    
    def test_row_to_dict(self):
        """Test the row_to_dict helper function."""
        # Create a mock SQLite Row
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        cursor.execute("INSERT INTO test VALUES (1, 'Test')")
        
        cursor.execute("SELECT * FROM test")
        row = cursor.fetchone()
        
        # Call the function
        result = row_to_dict(row)
        
        # Verify the result
        self.assertEqual(result, {"id": 1, "name": "Test"})
        
        # Test with None
        result = row_to_dict(None)
        
        # Verify the result
        self.assertEqual(result, {})
        
        conn.close()


if __name__ == "__main__":
    unittest.main()
