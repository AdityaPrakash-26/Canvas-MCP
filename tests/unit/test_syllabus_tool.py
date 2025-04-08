"""
Unit tests for the syllabus tools.

These tests verify that the syllabus tools correctly interact with the database.
"""

from types import SimpleNamespace

import pytest

from canvas_mcp.tools.syllabus import register_syllabus_tools


class TestSyllabusTools:
    """Test the syllabus tools."""

    def test_get_syllabus_file(
        self, canvas_client, db_manager, synced_course_ids
    ):
        """Test the get_syllabus_file tool."""
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
        register_syllabus_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager, "canvas_client": canvas_client}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Get the first course ID
        conn, cursor = db_manager.connect()
        cursor.execute("SELECT id FROM courses LIMIT 1")
        course_id = cursor.fetchone()["id"]
        conn.close()

        # Call the get_syllabus_file tool
        result = mock_mcp.get_syllabus_file(ctx, course_id)

        # Verify the result
        assert isinstance(result, dict)
        # Note: It's possible there's no syllabus file for this course
        if result.get("success", False):
            assert "syllabus_file" in result
            assert "all_syllabus_files" in result
        else:
            assert "error" in result
