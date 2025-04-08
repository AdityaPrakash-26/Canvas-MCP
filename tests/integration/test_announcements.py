"""
Integration tests for announcement-related functionality.

These tests verify that the announcement-related tools correctly retrieve
information from the database.
"""

import pytest

from canvas_mcp.tools.announcements import get_course_announcements


def test_get_course_announcements(test_context, target_course_info):
    """Test getting course announcements."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get announcements for the target course
    announcements = get_course_announcements(test_context, target_course_info["internal_id"])

    # Check that we got a list of announcements
    assert isinstance(announcements, list)
    print(
        f"Found {len(announcements)} announcements for course {target_course_info['internal_id']}"
    )

    # It's okay if there are no announcements, but we should still get a list
    if len(announcements) > 0:
        # Check the structure of the first announcement
        first_announcement = announcements[0]
        assert "title" in first_announcement
        assert "content" in first_announcement
        assert "posted_at" in first_announcement
        print(f"First announcement: {first_announcement.get('title')}")
