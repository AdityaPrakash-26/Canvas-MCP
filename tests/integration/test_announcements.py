"""
Integration tests for announcements-communication-related functionality.

These tests verify that the announcements-communication-related tools correctly retrieve
information from the database.
"""


def test_get_communications(test_client):
    """Test getting all communications."""
    # Get all communications
    communications = test_client.get_communications()

    # Check that we got a list of communications
    assert isinstance(communications, list)
    print(f"Found {len(communications)} communications across all courses")

    # Test with num_weeks parameter
    communications_4_weeks = test_client.get_communications(num_weeks=4)
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
