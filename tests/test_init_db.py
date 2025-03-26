"""
Tests for database initialization script.
"""
import os
import sqlite3
import tempfile
import unittest

# Import the module to test
from init_db import create_database, create_tables, create_views


class TestDatabaseInit(unittest.TestCase):
    """Test suite for database initialization functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary file for the test database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Close any open connections and remove the test database
        os.unlink(self.db_path)
    
    def test_create_database(self):
        """Test that the database is created with all necessary tables and views."""
        # Create the database using the function being tested
        create_database(self.db_path)
        
        # Connect to the created database
        conn = sqlite3.connect(self.db_path)
        # Enable foreign keys in the test connection too
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Check that all expected tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(row[0] for row in cursor.fetchall())
        
        # Define the expected tables
        expected_tables = {
            'courses',
            'syllabi',
            'assignments',
            'modules',
            'module_items',
            'calendar_events',
            'user_courses',
            'discussions',
            'announcements',
            'grades',
            'lectures',
            'files'
        }
        
        # Check that all expected tables exist
        for table in expected_tables:
            self.assertIn(table, tables, f"Table '{table}' was not created")
        
        # Check that all expected views were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = set(row[0] for row in cursor.fetchall())
        
        # Define the expected views
        expected_views = {
            'upcoming_deadlines',
            'course_summary'
        }
        
        # Check that all expected views exist
        for view in expected_views:
            self.assertIn(view, views, f"View '{view}' was not created")
        
        # Verify foreign key constraints are enabled
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        self.assertEqual(foreign_keys_enabled, 1, "Foreign keys should be enabled")
        
        conn.close()
    
    def test_table_schemas(self):
        """Test that the table schemas match the expected structure."""
        # Create the database
        create_database(self.db_path)
        
        # Connect to the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check courses table schema
        cursor.execute("PRAGMA table_info(courses)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Verify key columns exist with correct types
        self.assertEqual(columns["id"], "INTEGER")
        self.assertEqual(columns["canvas_course_id"], "INTEGER")
        self.assertEqual(columns["course_code"], "TEXT")
        self.assertEqual(columns["course_name"], "TEXT")
        self.assertEqual(columns["instructor"], "TEXT")
        self.assertEqual(columns["description"], "TEXT")
        self.assertEqual(columns["start_date"], "TIMESTAMP")
        self.assertEqual(columns["end_date"], "TIMESTAMP")
        self.assertEqual(columns["created_at"], "TIMESTAMP")
        self.assertEqual(columns["updated_at"], "TIMESTAMP")
        
        # Check assignments table schema
        cursor.execute("PRAGMA table_info(assignments)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Verify key columns exist with correct types
        self.assertEqual(columns["id"], "INTEGER")
        self.assertEqual(columns["course_id"], "INTEGER")
        self.assertEqual(columns["canvas_assignment_id"], "INTEGER")
        self.assertEqual(columns["title"], "TEXT")
        self.assertEqual(columns["description"], "TEXT")
        self.assertEqual(columns["assignment_type"], "TEXT")
        self.assertEqual(columns["due_date"], "TIMESTAMP")
        self.assertEqual(columns["points_possible"], "REAL")
        
        # Check indexes on assignments table
        cursor.execute("PRAGMA index_list(assignments)")
        indexes = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Verify indexes exist
        self.assertIn("idx_assignments_course_id", indexes.keys())
        self.assertIn("idx_assignments_due_date", indexes.keys())
        
        conn.close()
    
    def test_view_definitions(self):
        """Test that views are defined correctly."""
        # Create the database
        create_database(self.db_path)
        
        # Connect to the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check upcoming_deadlines view definition
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='upcoming_deadlines'")
        view_sql = cursor.fetchone()[0]
        
        # Verify it contains key parts
        self.assertIn("assignments a", view_sql)
        self.assertIn("courses c", view_sql)
        self.assertIn("a.due_date", view_sql)
        self.assertIn("ORDER BY", view_sql)
        
        # Check course_summary view definition
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='course_summary'")
        view_sql = cursor.fetchone()[0]
        
        # Verify it contains key parts
        self.assertIn("courses c", view_sql)
        self.assertIn("COUNT(DISTINCT", view_sql)
        self.assertIn("assignments a", view_sql)
        self.assertIn("modules m", view_sql)
        
        conn.close()
    
    def test_database_functionality(self):
        """Test that the database can be used to store and retrieve data."""
        # Create the database
        create_database(self.db_path)
        
        # Connect to the database
        conn = sqlite3.connect(self.db_path)
        # Enable foreign keys in the test connection
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Insert a test course
        cursor.execute(
            """
            INSERT INTO courses (
                canvas_course_id, course_code, course_name, instructor,
                description, start_date, end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                12345,
                "TST101",
                "Test Course",
                "Professor Smith",
                "This is a test course",
                "2025-01-15T00:00:00Z",
                "2025-05-15T00:00:00Z"
            )
        )
        
        # Get the course ID
        course_id = cursor.lastrowid
        
        # Insert a test assignment
        cursor.execute(
            """
            INSERT INTO assignments (
                course_id, canvas_assignment_id, title, description,
                assignment_type, due_date, points_possible
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                course_id,
                6789,
                "Test Assignment",
                "This is a test assignment",
                "assignment",
                "2025-02-15T23:59:00Z",
                100
            )
        )
        
        # Verify data can be retrieved via the views
        cursor.execute("SELECT * FROM upcoming_deadlines")
        deadlines = cursor.fetchall()
        self.assertEqual(len(deadlines), 1)
        
        deadline = deadlines[0]
        self.assertEqual(deadline["course_code"], "TST101")
        self.assertEqual(deadline["assignment_title"], "Test Assignment")
        self.assertEqual(deadline["points_possible"], 100)
        
        # Verify course summary view
        cursor.execute("SELECT * FROM course_summary")
        summaries = cursor.fetchall()
        self.assertEqual(len(summaries), 1)
        
        summary = summaries[0]
        self.assertEqual(summary["course_code"], "TST101")
        self.assertEqual(summary["assignment_count"], 1)
        self.assertEqual(summary["next_assignment"], "Test Assignment")
        
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
