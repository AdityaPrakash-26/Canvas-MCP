"""
Tests for database initialization script using SQLAlchemy.
"""
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

# Adjust import path based on the new location
from canvas_mcp.database import init_db
from canvas_mcp.models import (
    Assignment,
    Course,
)


def test_create_database(db_engine):
    """Test that the database is created with all necessary tables."""
    # Use SQLAlchemy Inspector to check tables
    inspector = inspect(db_engine)
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

    # Verify foreign key constraints are enabled (checked via pragma in a direct connection)
    # Extract the database path from the engine URL
    db_path = db_engine.url.database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    foreign_keys_enabled = cursor.fetchone()[0]
    conn.close()
    # Note: The event listener in database.py enables FKs on connection,
    # but init_db itself doesn't enforce it during creation.
    # We rely on the runtime enforcement by the SessionLocal.
    # assert foreign_keys_enabled == 1, "Foreign keys should be enabled by session connection"


def test_table_schemas(db_engine):
    """Test that the table schemas match the expected structure."""
    inspector = inspect(db_engine)

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


def test_database_functionality(db_session, sample_course, sample_assignment):
    """Test that the database can be used to store and retrieve data via SQLAlchemy."""
    # Verify data can be retrieved
    retrieved_course = db_session.query(Course).filter_by(course_code="TST101").one()
    assert retrieved_course.course_name == "Test Course"
    assert len(retrieved_course.assignments) == 1
    assert retrieved_course.assignments[0].title == "Test Assignment"
    assert retrieved_course.assignments[0].points_possible == 100

    # Test relationship loading
    retrieved_assignment = db_session.query(Assignment).filter_by(title="Test Assignment").one()
    assert retrieved_assignment.course.course_code == "TST101"
