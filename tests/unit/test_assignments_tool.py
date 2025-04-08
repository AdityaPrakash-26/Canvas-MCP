"""
Unit tests for the assignments tools.

These tests verify that the assignments tools correctly interact with the database.
"""

from types import SimpleNamespace

import pytest

from canvas_mcp.tools.assignments import register_assignment_tools


class TestAssignmentsTools:
    """Test the assignments tools."""

    def test_get_assignment_details(
        self, api_adapter, db_manager, synced_course_ids, synced_assignments
    ):
        """Test the get_assignment_details tool."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    # Store the function with its name
                    setattr(self, func.__name__, func)
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_assignment_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager, "api_adapter": api_adapter}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Get a course ID and assignment name
        conn, cursor = db_manager.connect()
        cursor.execute(
            "SELECT c.id, a.title FROM courses c JOIN assignments a ON c.id = a.course_id LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        # Skip the test if no assignments are found
        if not row:
            pytest.skip("No assignments found in the database")

        course_id = row["id"]
        assignment_name = row["title"]

        # Call the get_assignment_details tool
        result = mock_mcp.get_assignment_details(ctx, course_id, assignment_name)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" not in result
        assert "assignment" in result
        assert "course_code" in result
        assert "course_name" in result
