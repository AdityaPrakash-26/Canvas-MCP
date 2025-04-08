"""
Unit tests for the courses tools.

These tests verify that the courses tools correctly interact with the database.
"""

from types import SimpleNamespace

from canvas_mcp.tools.courses import register_course_tools


class TestCoursesTools:
    """Test the courses tools."""

    def test_get_course_list_empty(self, db_manager, clean_db):
        """Test the get_course_list tool with an empty database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.get_course_list = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_course_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the get_course_list tool
        result = mock_mcp.get_course_list(ctx)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_course_list_with_data(
        self, canvas_client, db_manager, synced_course_ids
    ):
        """Test the get_course_list tool with data in the database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.get_course_list = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_course_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the get_course_list tool
        result = mock_mcp.get_course_list(ctx)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) > 0

        # Verify the structure of the first course
        first_course = result[0]
        assert "id" in first_course
        assert "canvas_course_id" in first_course
        assert "course_code" in first_course
        assert "course_name" in first_course
