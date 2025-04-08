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


def test_get_communications_with_test_data(
    mock_mcp, mock_context, setup_communications_data, mock_datetime
):
    """Test the get_communications function with synced test data."""
    # Call the get_communications function
    result = mock_mcp.get_communications(mock_context)

    # Verify the result
    assert isinstance(result, list)

    # We should have communications from the fixtures
    assert len(result) > 0, "Should have communications from fixtures"

    # Check that we have both types of communications
    announcement_count = sum(
        1 for item in result if item.get("source_type") == "announcement"
    )
    conversation_count = sum(
        1 for item in result if item.get("source_type") == "conversation"
    )

    # We should have at least one of each type
    assert announcement_count > 0, "Should have at least one announcement"
    assert conversation_count > 0, "Should have at least one conversation"

    # Check that communications have the expected fields
    for item in result:
        assert "title" in item, "Communication should have a title"
        assert "content" in item, "Communication should have content"
        assert "posted_by" in item, "Communication should have a posted_by field"
        assert "course_name" in item, "Communication should have a course_name"
        assert "formatted_posted_at" in item, (
            "Communication should have a formatted date"
        )


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
