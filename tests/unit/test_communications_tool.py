"""Unit tests for the communications tools.

These tests verify that the communications tools correctly interact with the database.
Note: The announcements feature is being deprecated in favor of the unified communications feature.
"""

import datetime
from unittest.mock import patch

import pytest

from canvas_mcp.utils.formatters import format_date


def test_get_communications_empty(
    mock_mcp, mock_context, clean_db
):  # clean_db ensures empty database
    """Test the get_communications tool with an empty database."""
    # Call the get_communications tool
    result = mock_mcp.get_communications(mock_context)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_communications_with_data(
    mock_mcp, mock_context, synced_course_ids
):  # synced_course_ids ensures data exists
    """Test the get_communications tool with data in the database."""
    # Call the get_communications tool
    result = mock_mcp.get_communications(mock_context)

    # Verify the result
    assert isinstance(result, list)

    # Call the get_communications tool with a limit
    result_limited = mock_mcp.get_communications(mock_context, limit=5)

    # Verify the result
    assert isinstance(result_limited, list)
    assert len(result_limited) <= 5

    # Call the get_communications tool with num_weeks parameter
    result_weeks = mock_mcp.get_communications(mock_context, num_weeks=4)

    # Verify the result
    assert isinstance(result_weeks, list)


@pytest.mark.skip("Requires database setup with test data")
def test_get_communications_with_test_data(mock_mcp, mock_context, db_manager):
    """Test the get_communications function with specific test data."""
    # Create test data in the database
    conn, cursor = db_manager.connect()

    try:
        # Create a test course
        cursor.execute(
            """
            INSERT INTO courses (canvas_course_id, course_code, course_name, instructor, start_date, end_date)
            VALUES (12345, 'TEST-101', 'Test Course 101', 'Test Instructor', '2025-01-01', '2025-05-01')
            """
        )
        course_id = cursor.lastrowid

        # Create a test announcement
        cursor.execute(
            """
            INSERT INTO announcements (canvas_announcement_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
            VALUES (1001, ?, 'Test Announcement', 'This is a test announcement', 'Test Instructor', '2025-04-01 12:00:00+00:00', '2025-04-01 12:00:00', '2025-04-01 12:00:00')
            """,
            (course_id,),
        )

        # Check if conversations table exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='conversations';
            """
        )
        conversations_table_exists = cursor.fetchone() is not None

        if conversations_table_exists:
            # Create a test conversation
            cursor.execute(
                """
                INSERT INTO conversations (canvas_conversation_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
                VALUES (2001, ?, 'Test Conversation', 'This is a test conversation', 'Instructor', '2025-04-02 14:00:00+00:00', '2025-04-02 14:00:00', '2025-04-02 14:00:00')
                """,
                (course_id,),
            )

        conn.commit()

        # Mock the datetime module for consistent testing
        with patch("canvas_mcp.utils.formatters.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.datetime(2025, 4, 5, 12, 0, 0)
            mock_dt.datetime = datetime.datetime
            mock_dt.timedelta = datetime.timedelta
            mock_dt.fromisoformat = datetime.datetime.fromisoformat

            # Call the get_communications function
            result = mock_mcp.get_communications(mock_context)

            # Verify the result
            assert isinstance(result, list)

            if conversations_table_exists:
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
            else:
                assert len(result) == 1, "Should have 1 announcement"
    finally:
        conn.close()


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
