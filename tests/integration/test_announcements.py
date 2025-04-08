"""
Integration tests for announcement-related functionality.

These tests verify that the announcement-related tools correctly retrieve
information from the database.
"""

# No need to import get_course_announcements, we'll use the test_client


def test_get_course_announcements(test_client, target_course_info):
    """Test getting course announcements."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get announcements for the target course
    announcements = test_client.get_course_announcements(
        target_course_info["internal_id"]
    )

    # Check that we got a list of announcements
    assert isinstance(announcements, list)
    print(
        f"Found {len(announcements)} announcements for course {target_course_info['internal_id']}"
    )

    # Test with num_weeks parameter
    announcements_4_weeks = test_client.get_course_announcements(
        target_course_info["internal_id"], num_weeks=4
    )
    assert isinstance(announcements_4_weeks, list)
    print(
        f"Found {len(announcements_4_weeks)} announcements for course {target_course_info['internal_id']} in the last 4 weeks"
    )

    # It's okay if there are no announcements, but we should still get a list
    if len(announcements) > 0:
        # Check the structure of the first announcement
        first_announcement = announcements[0]
        assert "title" in first_announcement
        assert "content" in first_announcement
        assert "posted_at" in first_announcement
        print(f"First announcement: {first_announcement.get('title')}")


def test_get_course_communications(test_client, target_course_info):
    """Test getting course communications."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get communications for the target course
    communications = test_client.get_course_communications(
        target_course_info["internal_id"]
    )

    # Check that we got a list of communications
    assert isinstance(communications, list)
    print(
        f"Found {len(communications)} communications for course {target_course_info['internal_id']}"
    )

    # Test with num_weeks parameter
    communications_4_weeks = test_client.get_course_communications(
        target_course_info["internal_id"], num_weeks=4
    )
    assert isinstance(communications_4_weeks, list)
    print(
        f"Found {len(communications_4_weeks)} communications for course {target_course_info['internal_id']} in the last 4 weeks"
    )

    # It's okay if there are no communications, but we should still get a list
    if len(communications) > 0:
        # Check the structure of the first communication
        first_communication = communications[0]
        assert "title" in first_communication
        assert "content" in first_communication
        assert "posted_at" in first_communication
        assert "source_type" in first_communication
        assert "course_name" in first_communication
        print(f"First communication: {first_communication.get('title')}")


def test_get_all_communications(test_client):
    """Test getting all communications."""
    # Get all communications
    communications = test_client.get_all_communications()

    # Check that we got a list of communications
    assert isinstance(communications, list)
    print(f"Found {len(communications)} communications across all courses")

    # Test with num_weeks parameter
    communications_4_weeks = test_client.get_all_communications(num_weeks=4)
    assert isinstance(communications_4_weeks, list)
    print(
        f"Found {len(communications_4_weeks)} communications across all courses in the last 4 weeks"
    )

    # It's okay if there are no communications, but we should still get a list
    if len(communications) > 0:
        # Check the structure of the first communication
        first_communication = communications[0]
        assert "title" in first_communication
        assert "content" in first_communication
        assert "posted_at" in first_communication
        assert "source_type" in first_communication
        assert "course_name" in first_communication
        print(f"First communication: {first_communication.get('title')}")
