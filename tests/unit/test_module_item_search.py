"""
Unit tests for searching module items with HTML content.

These tests verify that HTML content in module items is properly converted to Markdown
and can be found by the search functionality.
"""

from types import SimpleNamespace

from canvas_mcp.tools.search import register_search_tools
from canvas_mcp.utils.formatters import convert_html_to_markdown


class TestModuleItemSearch:
    """Test searching module items with HTML content."""

    def test_search_finds_converted_html_content(self, db_manager, clean_db):
        """Test that the search tool can find HTML content converted to Markdown."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.search_course_content = func
                    return func

                return decorator

        # Register the search tools
        mock_mcp = MockMCP()
        register_search_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Insert test data into the database
        conn, cursor = db_manager.connect()
        try:
            # Insert a test course
            cursor.execute(
                """
                INSERT INTO courses (id, canvas_course_id, course_code, course_name)
                VALUES (1, 12345, 'TEST101', 'Test Course')
                """
            )

            # Insert a test module
            cursor.execute(
                """
                INSERT INTO modules (id, course_id, canvas_module_id, name)
                VALUES (1, 1, 67890, 'Test Module')
                """
            )

            # Convert HTML to Markdown
            html_content = "<p>Hello <strong>World</strong></p>"
            markdown_content = convert_html_to_markdown(html_content)
            assert markdown_content is not None, "HTML to Markdown conversion failed"
            assert "Hello **World**" in markdown_content, "Conversion result unexpected"

            # Insert a test module item with the converted Markdown content
            cursor.execute(
                """
                INSERT INTO module_items (
                    id, module_id, canvas_item_id, title, item_type, content_details
                )
                VALUES (1, 1, 54321, 'Test Item', 'Page', ?)
                """,
                (markdown_content,),
            )

            conn.commit()
        finally:
            conn.close()

        # Search for "World" which should be in the converted content
        result = mock_mcp.search_course_content(ctx, "World")

        # Verify the result
        assert isinstance(result, list)
        assert len(result) > 0, "Search should find the module item"

        # Verify the structure of the first result
        first_result = result[0]
        assert first_result["course_code"] == "TEST101"
        assert first_result["course_name"] == "Test Course"
        assert first_result["title"] == "Test Item"
        assert first_result["content_type"] == "module_item"

        # Search for "Hello" which should also be in the converted content
        result = mock_mcp.search_course_content(ctx, "Hello")
        assert len(result) > 0, "Search should find the module item"

        # Search for "strong" which should NOT be in the converted content (HTML tag)
        result = mock_mcp.search_course_content(ctx, "strong")
        assert len(result) == 0, "Search should not find HTML tags"

        # Search for "**" which is part of the Markdown syntax but should be found as literal characters
        result = mock_mcp.search_course_content(ctx, "**")
        assert len(result) > 0, "Search should find literal Markdown syntax characters"
