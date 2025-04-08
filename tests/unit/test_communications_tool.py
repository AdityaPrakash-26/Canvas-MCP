"""Unit tests for the communications tools.

These tests verify that the communications tools correctly interact with the database.
Note: The announcements feature is being deprecated in favor of the unified communications feature.
"""

from types import SimpleNamespace

import pytest

from canvas_mcp.tools.announcements import register_announcement_tools


class TestCommunicationsTools:
    """Test the communications tools."""

    # Helper method to create a mock MCP server and context
    def _setup_mock_mcp_and_context(self, db_manager):
        """Set up a mock MCP server and context for testing."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    setattr(self, func.__name__, func)
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_announcement_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        return mock_mcp, ctx

    def test_get_course_announcements_empty(self, db_manager, clean_db):
        """Test the get_course_announcements tool with an empty database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

        # Call the get_course_announcements tool
        result = mock_mcp.get_course_announcements(ctx, 1)  # Use a dummy course ID

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_course_announcements_with_data(self, db_manager):
        """Test the get_course_announcements tool with data in the database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

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
        result = mock_mcp.get_course_announcements(ctx, course_id)

        # Verify the result
        assert isinstance(result, list)
        # Note: It's possible there are no announcements for this course

        # Call the get_course_announcements tool with a limit
        result_limited = mock_mcp.get_course_announcements(ctx, course_id, limit=5)

        # Verify the result
        assert isinstance(result_limited, list)
        assert len(result_limited) <= 5

        # Call the get_course_announcements tool with num_weeks parameter
        result_weeks = mock_mcp.get_course_announcements(ctx, course_id, num_weeks=4)

        # Verify the result
        assert isinstance(result_weeks, list)

        # If there are announcements, check that they have the expected structure
        if len(result) > 0:
            first_announcement = result[0]
            assert "id" in first_announcement
            assert "title" in first_announcement
            assert "content" in first_announcement
            assert "posted_at" in first_announcement

    def test_get_course_communications_empty(self, db_manager, clean_db):
        """Test the get_course_communications tool with an empty database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

        # Call the get_course_communications tool
        result = mock_mcp.get_course_communications(ctx, 1)  # Use a dummy course ID

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_course_communications_with_data(self, db_manager):
        """Test the get_course_communications tool with data in the database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

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
        result = mock_mcp.get_course_communications(ctx, course_id)

        # Verify the result
        assert isinstance(result, list)

        # Call the get_course_communications tool with a limit
        result_limited = mock_mcp.get_course_communications(ctx, course_id, limit=5)

        # Verify the result
        assert isinstance(result_limited, list)
        assert len(result_limited) <= 5

        # Call the get_course_communications tool with num_weeks parameter
        result_weeks = mock_mcp.get_course_communications(ctx, course_id, num_weeks=4)

        # Verify the result
        assert isinstance(result_weeks, list)

    def test_get_all_communications_empty(self, db_manager, clean_db):
        """Test the get_all_communications tool with an empty database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

        # Call the get_all_communications tool
        result = mock_mcp.get_all_communications(ctx)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_all_communications_with_data(self, db_manager):
        """Test the get_all_communications tool with data in the database."""
        # Set up mock MCP and context
        mock_mcp, ctx = self._setup_mock_mcp_and_context(db_manager)

        # Call the get_all_communications tool
        result = mock_mcp.get_all_communications(ctx)

        # Verify the result
        assert isinstance(result, list)

        # Call the get_all_communications tool with a limit
        result_limited = mock_mcp.get_all_communications(ctx, limit=5)

        # Verify the result
        assert isinstance(result_limited, list)
        assert len(result_limited) <= 5

        # Call the get_all_communications tool with num_weeks parameter
        result_weeks = mock_mcp.get_all_communications(ctx, num_weeks=4)

        # Verify the result
        assert isinstance(result_weeks, list)
