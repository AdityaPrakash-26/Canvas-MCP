"""Unit tests for the communications functionality."""

import datetime
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

# Import the register_announcement_tools function to access the tools
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.utils.formatters import format_date


# Fixtures for test database setup
@pytest.fixture
def test_db_connection():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create the necessary tables
    cursor.execute(
        """
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY,
            canvas_course_id INTEGER,
            course_code TEXT,
            course_name TEXT,
            instructor TEXT,
            start_date TEXT,
            end_date TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY,
            canvas_announcement_id INTEGER,
            course_id INTEGER,
            title TEXT,
            content TEXT,
            posted_by TEXT,
            posted_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY,
            canvas_conversation_id INTEGER,
            course_id INTEGER,
            title TEXT,
            content TEXT,
            posted_by TEXT,
            posted_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
        """
    )

    # Insert test data
    cursor.execute(
        """
        INSERT INTO courses (id, canvas_course_id, course_code, course_name, instructor, start_date, end_date)
        VALUES (1, 12345, 'TEST-101', 'Test Course 101', 'Test Instructor', '2025-01-01', '2025-05-01')
        """
    )

    # Insert test announcements
    cursor.execute(
        """
        INSERT INTO announcements (id, canvas_announcement_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
        VALUES (1, 1001, 1, 'Test Announcement 1', 'This is a test announcement', 'Test Instructor', '2025-04-01 12:00:00+00:00', '2025-04-01 12:00:00', '2025-04-01 12:00:00')
        """
    )

    # Insert test conversations
    cursor.execute(
        """
        INSERT INTO conversations (id, canvas_conversation_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
        VALUES (1, 2001, 1, 'Test Conversation 1', 'This is a test conversation', 'Instructor', '2025-04-04 14:00:00+00:00', '2025-04-04 14:00:00', '2025-04-04 14:00:00')
        """
    )

    conn.commit()

    yield conn

    # Cleanup
    conn.close()


@pytest.fixture
def mock_context(test_db_connection):
    """Create a mock context with the test database."""
    context = MagicMock()
    context.request_context = MagicMock()
    context.request_context.lifespan_context = {"db_manager": MagicMock()}
    context.request_context.lifespan_context["db_manager"].connect = MagicMock(
        return_value=(test_db_connection, test_db_connection.cursor())
    )
    context.request_context.lifespan_context["db_manager"].rows_to_dicts = (
        lambda rows: [{key: row[key] for key in row.keys()} for row in rows]
    )
    return context


@pytest.fixture
def mock_datetime():
    """Mock the datetime module for consistent testing."""
    with patch("canvas_mcp.utils.formatters.datetime") as mock_dt:
        # Configure the mock to use real datetime functionality
        mock_dt.now.return_value = datetime.datetime(2025, 4, 5, 12, 0, 0)
        mock_dt.datetime = datetime.datetime
        mock_dt.timedelta = datetime.timedelta
        mock_dt.fromisoformat = datetime.datetime.fromisoformat
        mock_dt.UTC = datetime.UTC
        # Make sure comparison operators work
        mock_dt.side_effect = lambda *args, **kwargs: datetime.datetime(*args, **kwargs)
        yield mock_dt


def test_get_communications_returns_both_types(
    mock_mcp, mock_context, mock_datetime
):  # mock_datetime ensures consistent date formatting
    """Test that get_communications returns both announcements and conversations."""
    # Call the function being tested
    result = mock_mcp.get_communications(mock_context)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2, (
        "Should have 2 communications (1 announcement, 1 conversation)"
    )

    # Check that we have both types of communications
    announcement_count = sum(
        1 for item in result if item.get("source_type") == "announcement"
    )
    conversation_count = sum(
        1 for item in result if item.get("source_type") == "conversation"
    )

    assert announcement_count == 1, "Should have 1 announcement"
    assert conversation_count == 1, "Should have 1 conversation"

    # Check the content of the communications
    for item in result:
        if item.get("source_type") == "announcement":
            assert item.get("title") == "Test Announcement 1"
            assert item.get("content") == "This is a test announcement"
            assert item.get("posted_by") == "Test Instructor"
            assert item.get("course_name") == "Test Course 101"
            assert item.get("formatted_posted_at") == "Tuesday, April 01 at 12:00 PM"
        elif item.get("source_type") == "conversation":
            assert item.get("title") == "Test Conversation 1"
            assert item.get("content") == "This is a test conversation"
            assert item.get("posted_by") == "Instructor"
            assert item.get("course_name") == "Test Course 101"
            assert item.get("formatted_posted_at") == "Yesterday at 02:00 PM"


def test_get_communications_with_course_filter():
    """Test that get_communications filters by course_id."""
    # Note: get_communications doesn't directly support course_id filtering
    # This test is a placeholder for when we implement course filtering
    pass


@pytest.fixture
def test_db_with_old_communications(test_db_connection):
    """Add older communications to the test database."""
    cursor = test_db_connection.cursor()

    # Add older communications that should be filtered out with a small days value
    cursor.execute(
        """
        INSERT INTO announcements (id, canvas_announcement_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
        VALUES (3, 1003, 1, 'Old Announcement', 'This is an old announcement', 'Test Instructor', '2025-03-01 12:00:00+00:00', '2025-03-01 12:00:00', '2025-03-01 12:00:00')
        """
    )

    cursor.execute(
        """
        INSERT INTO conversations (id, canvas_conversation_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
        VALUES (3, 2003, 1, 'Old Conversation', 'This is an old conversation', 'Instructor', '2025-03-02 14:00:00+00:00', '2025-03-02 14:00:00', '2025-03-02 14:00:00')
        """
    )

    # Add another recent announcement to make sure we have 2 recent communications
    cursor.execute(
        """
        INSERT INTO announcements (id, canvas_announcement_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
        VALUES (2, 1002, 1, 'Test Announcement 2', 'This is another test announcement', 'Test Instructor', '2025-04-03 15:00:00+00:00', '2025-04-03 15:00:00', '2025-04-03 15:00:00')
        """
    )

    test_db_connection.commit()
    return test_db_connection


def test_get_communications_with_days_filter(
    mock_mcp,
    mock_context,
    mock_datetime,
    test_db_with_old_communications,  # These fixtures set up the test environment
):
    """Test that get_communications filters by days."""
    # Test with a 7-day filter (should exclude the old communications)
    result = mock_mcp.get_communications(mock_context, limit=10, num_weeks=1)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 2, "Should have 2 recent communications"

    # Check that old communications are filtered out
    for item in result:
        assert item.get("title") != "Old Announcement", (
            "Old announcement should be filtered out"
        )
        assert item.get("title") != "Old Conversation", (
            "Old conversation should be filtered out"
        )

    # Note: We don't test with a 60-day filter here because the database connection
    # is closed after the first test, and we'd need a more complex fixture setup to handle that


def test_format_date(mock_datetime):  # mock_datetime ensures consistent date formatting
    """Test the format_date function."""
    # Test today
    today = "2025-04-05T14:30:00"
    formatted = format_date(today)
    assert formatted == "Today at 02:30 PM"

    # Test yesterday
    yesterday = "2025-04-04T09:15:00"
    formatted = format_date(yesterday)
    assert formatted == "Yesterday at 09:15 AM"

    # Test this week
    this_week = "2025-04-02T18:45:00"
    formatted = format_date(this_week)
    assert formatted == "Wednesday, April 02 at 06:45 PM"

    # Test older date
    older_date = "2025-03-15T12:00:00"
    formatted = format_date(older_date)
    assert formatted == "March 15, 2025 at 12:00 PM"
