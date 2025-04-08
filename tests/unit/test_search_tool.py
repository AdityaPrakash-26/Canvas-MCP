"""
Unit tests for the search tools.

These tests verify that the search tools correctly interact with the database.
"""

from types import SimpleNamespace

import pytest

from canvas_mcp.tools.search import register_search_tools


class TestSearchTools:
    """Test the search tools."""

    def test_search_course_content_empty(self, db_manager, clean_db):
        """Test the search_course_content tool with an empty database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.search_course_content = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_search_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the search_course_content tool
        result = mock_mcp.search_course_content(ctx, "test")

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_search_course_content_with_data(
        self,
        canvas_client,
        db_manager,
        synced_course_ids,
        synced_assignments,
        synced_modules,
    ):
        """Test the search_course_content tool with data in the database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.search_course_content = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_search_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Get a search term from an assignment title
        conn, cursor = db_manager.connect()
        cursor.execute("SELECT title FROM assignments LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        # Skip the test if no assignments are found
        if not row:
            pytest.skip("No assignments found in the database")

        # Use the first word of the assignment title as the search term
        search_term = row["title"].split()[0]

        # Call the search_course_content tool
        result = mock_mcp.search_course_content(ctx, search_term)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) > 0

        # Verify the structure of the first result
        first_result = result[0]
        assert "course_code" in first_result
        assert "course_name" in first_result
        assert "title" in first_result
        assert "content_type" in first_result

        # Get the first course ID
        conn, cursor = db_manager.connect()
        cursor.execute("SELECT id FROM courses LIMIT 1")
        course_id = cursor.fetchone()["id"]
        conn.close()

        # Call the search_course_content tool with a course filter
        result_filtered = mock_mcp.search_course_content(ctx, search_term, course_id)

        # Verify the result
        assert isinstance(result_filtered, list)
        # All results should be from the specified course
        for item in result_filtered:
            # Get the course ID for this item
            conn, cursor = db_manager.connect()
            cursor.execute(
                "SELECT id FROM courses WHERE course_code = ?", (item["course_code"],)
            )
            item_course_id = cursor.fetchone()["id"]
            conn.close()

            assert item_course_id == course_id
