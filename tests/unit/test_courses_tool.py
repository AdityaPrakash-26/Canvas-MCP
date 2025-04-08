"""
Unit tests for the courses tools.

These tests verify that the courses tools correctly interact with the database.
"""

# pytest is used for fixtures


class TestCoursesTools:
    """Test the courses tools."""

    def test_get_course_list_empty(
        self, mock_mcp, mock_context, clean_db
    ):  # clean_db ensures empty database
        """Test the get_course_list tool with an empty database."""
        # Call the get_course_list tool
        result = mock_mcp.get_course_list(mock_context)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_course_list_with_data(
        self, mock_mcp, mock_context, synced_course_ids
    ):  # synced_course_ids ensures data exists
        """Test the get_course_list tool with data in the database."""
        # Call the get_course_list tool
        result = mock_mcp.get_course_list(mock_context)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) > 0

        # Verify the structure of the first course
        first_course = result[0]
        assert "id" in first_course
        assert "canvas_course_id" in first_course
        assert "course_code" in first_course
        assert "course_name" in first_course
