"""Unit tests for the communications tools.

These tests verify that the communications tools correctly interact with the database.
Note: The announcements feature is being deprecated in favor of the unified communications feature.

"""

import pytest


# Test functions for announcements tools


def test_get_course_announcements_empty(
    mock_mcp, mock_context, clean_db
):  # clean_db ensures empty database
    """Test the get_course_announcements tool with an empty database."""
    # Call the get_course_announcements tool
    result = mock_mcp.get_course_announcements(mock_context, 1)  # Use a dummy course ID

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_course_announcements_with_data(
    mock_mcp, mock_context, db_manager, synced_course_ids
):  # synced_course_ids ensures data exists
    """Test the get_course_announcements tool with data in the database."""
    # Get the first course ID
    conn, cursor = db_manager.connect()
    cursor.execute("SELECT id FROM courses LIMIT 1")
    course_row = cursor.fetchone()
    conn.close()

    # Skip the test if no courses are found
    if not course_row:
        pytest.skip("No courses found in the database")

    course_id = course_row["id"]

    # Call the get_course_announcements tool
    result = mock_mcp.get_course_announcements(mock_context, course_id)

    # Verify the result
    assert isinstance(result, list)
    # Note: It's possible there are no announcements for this course

    # Call the get_course_announcements tool with a limit
    result_limited = mock_mcp.get_course_announcements(mock_context, course_id, limit=5)

    # Verify the result
    assert isinstance(result_limited, list)
    assert len(result_limited) <= 5

    # Call the get_course_announcements tool with num_weeks parameter
    result_weeks = mock_mcp.get_course_announcements(
        mock_context, course_id, num_weeks=4
    )

    # Verify the result
    assert isinstance(result_weeks, list)

    # If there are announcements, check that they have the expected structure
    if len(result) > 0:
        first_announcement = result[0]
        assert "id" in first_announcement
        assert "title" in first_announcement
        assert "content" in first_announcement
        assert "posted_at" in first_announcement


def test_get_course_communications_empty(
    mock_mcp, mock_context, clean_db
):  # clean_db ensures empty database
    """Test the get_course_communications tool with an empty database."""
    # Call the get_course_communications tool
    result = mock_mcp.get_course_communications(
        mock_context, 1
    )  # Use a dummy course ID

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_course_communications_with_data(
    mock_mcp, mock_context, db_manager, synced_course_ids
):  # synced_course_ids ensures data exists
    """Test the get_course_communications tool with data in the database."""
    # Get the first course ID
    conn, cursor = db_manager.connect()
    cursor.execute("SELECT id FROM courses LIMIT 1")
    course_row = cursor.fetchone()
    conn.close()

    # Skip the test if no courses are found
    if not course_row:
        pytest.skip("No courses found in the database")

    course_id = course_row["id"]

    # Call the get_course_communications tool
    result = mock_mcp.get_course_communications(mock_context, course_id)

    # Verify the result
    assert isinstance(result, list)

    # Call the get_course_communications tool with a limit
    result_limited = mock_mcp.get_course_communications(
        mock_context, course_id, limit=5
    )

    # Verify the result
    assert isinstance(result_limited, list)
    assert len(result_limited) <= 5

    # Call the get_course_communications tool with num_weeks parameter
    result_weeks = mock_mcp.get_course_communications(
        mock_context, course_id, num_weeks=4
    )

    # Verify the result
    assert isinstance(result_weeks, list)


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
