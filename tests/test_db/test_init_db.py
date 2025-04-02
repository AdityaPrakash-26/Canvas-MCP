"""
Tests for database initialization using SQLAlchemy.
"""
import os
import sqlite3
import tempfile
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from canvas_mcp.database import init_db
from canvas_mcp.models import Assignment, Course


@pytest.fixture
def temp_db_file():
    """Create a temporary database file for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    yield db_path
    
    # Clean up after test
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_create_database(temp_db_file):
    """Test that the database is created with all necessary tables."""
    # Create database engine for the temp file
    db_url = f"sqlite:///{temp_db_file}"
    engine = create_engine(db_url)
    
    # Create the database using the function being tested
    init_db(engine)
    
    # Use SQLAlchemy Inspector to check tables
    inspector = inspect(engine)
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
    }
    
    # Check that all expected tables exist
    for table in expected_tables:
        assert table in tables, f"Table '{table}' was not created"
    
    # Dispose of the engine to close connections
    engine.dispose()


def test_table_schemas(temp_db_file):
    """Test that the table schemas match the expected structure."""
    # Create database engine for the temp file
    db_url = f"sqlite:///{temp_db_file}"
    engine = create_engine(db_url)
    
    # Create the database
    init_db(engine)
    
    inspector = inspect(engine)
    
    # Check courses table schema - verify columns exist
    columns = {col['name']: col['type'].__class__.__name__ for col in inspector.get_columns('courses')}
    
    # Check all expected columns exist
    expected_columns = [
        "id", "canvas_course_id", "course_code", "course_name",
        "instructor", "description", "start_date", "end_date",
        "created_at", "updated_at"
    ]
    for col in expected_columns:
        assert col in columns, f"Column {col} missing from courses table"
    
    # Check assignments table schema - verify columns exist
    columns = {col['name']: col['type'].__class__.__name__ for col in inspector.get_columns('assignments')}
    expected_columns = [
        "id", "course_id", "canvas_assignment_id", "title",
        "description", "assignment_type", "due_date", "points_possible"
    ]
    for col in expected_columns:
        assert col in columns, f"Column {col} missing from assignments table"
    
    # Check indexes on assignments table
    indexes = inspector.get_indexes('assignments')
    index_names = {idx['name'] for idx in indexes}
    assert "idx_assignments_course_id" in index_names
    assert "idx_assignments_due_date" in index_names
    
    # Check unique constraints on assignments table
    constraints = inspector.get_unique_constraints('assignments')
    constraint_names = {c['name'] for c in constraints}
    assert 'uq_course_assignment' in constraint_names
    
    # Dispose of the engine to close connections
    engine.dispose()


def test_database_functionality(temp_db_file):
    """Test that the database can be used to store and retrieve data via SQLAlchemy."""
    # Create database engine for the temp file
    db_url = f"sqlite:///{temp_db_file}"
    engine = create_engine(db_url)
    
    # Create the database
    init_db(engine)
    
    # Create a session
    Session = sessionmaker(bind=engine)
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
    session.commit()  # Commit to get the course ID
    
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
    assert retrieved_course.course_name == "Test Course"
    assert len(retrieved_course.assignments) == 1
    assert retrieved_course.assignments[0].title == "Test Assignment"
    assert retrieved_course.assignments[0].points_possible == 100
    
    # Test relationship loading
    retrieved_assignment = session.query(Assignment).filter_by(title="Test Assignment").one()
    assert retrieved_assignment.course.course_code == "TST101"
    
    # Close the session
    session.close()
    
    # Dispose of the engine to close connections
    engine.dispose()
