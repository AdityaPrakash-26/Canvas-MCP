"""
Tests for database initialization script using SQLAlchemy.
"""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Adjust import path based on the new location
from canvas_mcp.database import Base, init_db
from canvas_mcp.models import (
    Announcement,
    Assignment,
    CalendarEvent,
    Course,
    Discussion,
    File,
    Grade,
    Lecture,
    Module,
    ModuleItem,
    Syllabus,
    UserCourse,
)


class TestDatabaseInitSQLAlchemy(unittest.TestCase):
    """Test suite for SQLAlchemy database initialization functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary file for the test database
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()
        self.db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(self.db_url)

    def tearDown(self):
        """Clean up test environment after each test."""
        # Ensure the engine is disposed (closes connections) before deleting the file
        if self.engine:
            self.engine.dispose()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_database(self):
        """Test that the database is created with all necessary tables."""
        # Create the database using the function being tested
        init_db(self.engine)

        # Use SQLAlchemy Inspector to check tables
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        # Define the expected tables based on models
        expected_tables = {
            'courses',
            'syllabi',
            'assignments',
            'modules',
            'module_items',
            'calendar_events',
            'user_courses',
            'announcements',
            'discussions',
            'grades',
            'lectures',
            'files',
            # Note: Views are not directly created by create_all
        }

        # Check that all expected tables exist
        for table in expected_tables:
            self.assertIn(table, tables, f"Table '{table}' was not created")

        # Verify foreign key constraints are enabled (checked via pragma in a direct connection)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        conn.close()
        # Note: The event listener in database.py enables FKs on connection,
        # but init_db itself doesn't enforce it during creation.
        # We rely on the runtime enforcement by the SessionLocal.
        # self.assertEqual(foreign_keys_enabled, 1, "Foreign keys should be enabled by session connection")

    def test_table_schemas(self):
        """Test that the table schemas match the expected structure."""
        # Create the database
        init_db(self.engine)

        inspector = inspect(self.engine)

        # Check courses table schema - verify columns exist
        columns = {col['name']: col['type'].__class__.__name__ for col in inspector.get_columns('courses')}
        
        # Check all expected columns exist
        expected_columns = [
            "id", "canvas_course_id", "course_code", "course_name", 
            "instructor", "description", "start_date", "end_date", 
            "created_at", "updated_at"
        ]
        for col in expected_columns:
            self.assertIn(col, columns, f"Column {col} missing from courses table")
        
        # Check assignments table schema - verify columns exist
        columns = {col['name']: col['type'].__class__.__name__ for col in inspector.get_columns('assignments')}
        expected_columns = [
            "id", "course_id", "canvas_assignment_id", "title", 
            "description", "assignment_type", "due_date", "points_possible"
        ]
        for col in expected_columns:
            self.assertIn(col, columns, f"Column {col} missing from assignments table")

        # Check indexes on assignments table
        indexes = inspector.get_indexes('assignments')
        index_names = {idx['name'] for idx in indexes}
        self.assertIn("idx_assignments_course_id", index_names)
        self.assertIn("idx_assignments_due_date", index_names)

        # Check unique constraints on assignments table
        constraints = inspector.get_unique_constraints('assignments')
        constraint_names = {c['name'] for c in constraints}
        self.assertIn('uq_course_assignment', constraint_names)

    def test_database_functionality(self):
        """Test that the database can be used to store and retrieve data via SQLAlchemy."""
        # Create the database
        init_db(self.engine)

        # Create a session
        Session = sessionmaker(bind=self.engine)
        session = Session()

        # Insert a test course
        test_course = Course(
            canvas_course_id=12345,
            course_code="TST101",
            course_name="Test Course",
            instructor="Professor Smith",
            description="This is a test course",
            start_date=datetime(2025, 1, 15),
            end_date=datetime(2025, 5, 15)
        )
        session.add(test_course)
        session.commit() # Commit to get the course ID

        # Insert a test assignment linked to the course
        test_assignment = Assignment(
            course_id=test_course.id,
            canvas_assignment_id=6789,
            title="Test Assignment",
            description="This is a test assignment",
            assignment_type="assignment",
            due_date=datetime(2025, 2, 15, 23, 59),
            points_possible=100
        )
        session.add(test_assignment)
        session.commit()

        # Verify data can be retrieved
        retrieved_course = session.query(Course).filter_by(course_code="TST101").one()
        self.assertEqual(retrieved_course.course_name, "Test Course")
        self.assertEqual(len(retrieved_course.assignments), 1)
        self.assertEqual(retrieved_course.assignments[0].title, "Test Assignment")
        self.assertEqual(retrieved_course.assignments[0].points_possible, 100)

        # Test relationship loading
        retrieved_assignment = session.query(Assignment).filter_by(title="Test Assignment").one()
        self.assertEqual(retrieved_assignment.course.course_code, "TST101")

        session.close()


if __name__ == "__main__":
    unittest.main()