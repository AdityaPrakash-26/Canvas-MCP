"""Unit tests for the communications functionality."""

import datetime
from unittest.mock import patch

import pytest

from canvas_mcp.sync.announcements import sync_announcements
from canvas_mcp.sync.conversations import sync_conversations
from canvas_mcp.utils.formatters import format_date


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
    mock_mcp, mock_context, mock_datetime, setup_communications_data
):  # mock_datetime ensures consistent date formatting
    """Test that get_communications returns both announcements and conversations."""
    # Call the function being tested
    result = mock_mcp.get_communications(mock_context)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) > 0, "Should have at least one communication"

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


def test_get_communications_with_course_filter():
    """Test that get_communications filters by course_id."""
    # Note: get_communications doesn't directly support course_id filtering
    # This test is a placeholder for when we implement course filtering
    pass


@pytest.fixture
def setup_communications_data(mock_mcp, mock_context, clean_db, sync_service):
    """Set up communications data for testing using the fixtures."""
    # First sync courses to have course data available
    course_ids = sync_service.sync_courses()

    # Then sync announcements and conversations
    sync_announcements(sync_service, course_ids)
    sync_conversations(sync_service)

    return course_ids


def test_get_communications_with_days_filter(
    mock_mcp,
    mock_context,
    mock_datetime,
    setup_communications_data,  # This fixture sets up the test environment
):
    """Test that get_communications filters by days."""
    # Get all communications first
    all_results = mock_mcp.get_communications(
        mock_context, num_weeks=8
    )  # Longer timeframe

    # Now get communications with a shorter timeframe
    recent_results = mock_mcp.get_communications(mock_context, num_weeks=1)  # 1 week

    # Verify the results
    assert isinstance(all_results, list)
    assert isinstance(recent_results, list)

    # We should have fewer or equal communications with the shorter timeframe
    assert len(recent_results) <= len(all_results), (
        "Recent results should be fewer than all results"
    )

    # If we have different counts, verify that the filtering is working
    if len(recent_results) < len(all_results):
        # Get the titles of recent communications
        recent_titles = [item.get("title") for item in recent_results]

        # Find communications that are in all_results but not in recent_results
        for item in all_results:
            if item.get("title") not in recent_titles:
                # This item was filtered out, check its date
                posted_at = item.get("posted_at")
                # Convert to datetime for comparison
                if posted_at:
                    # The date should be older than 1 week
                    posted_date = datetime.datetime.fromisoformat(
                        posted_at.replace("Z", "+00:00")
                    )
                    now = mock_datetime.now()
                    one_week_ago = now - datetime.timedelta(weeks=1)
                    assert posted_date < one_week_ago, (
                        "Filtered item should be older than 1 week"
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
