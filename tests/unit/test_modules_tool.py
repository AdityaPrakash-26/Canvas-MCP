"""
Unit tests for the modules tools.

These tests verify that the modules tools correctly interact with the database.
"""

from types import SimpleNamespace

from canvas_mcp.tools.modules import register_module_tools


class TestModulesTools:
    """Test the modules tools."""

    def test_get_course_modules_empty(self, db_manager, clean_db):
        """Test the get_course_modules tool with an empty database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.get_course_modules = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_module_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the get_course_modules tool
        result = mock_mcp.get_course_modules(ctx, 1)  # Use a dummy course ID

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_course_modules_with_data(
        self, canvas_client, db_manager, synced_course_ids, synced_modules
    ):
        """Test the get_course_modules tool with data in the database."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.get_course_modules = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_module_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"db_manager": db_manager}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Get the first course ID
        conn, cursor = db_manager.connect()
        cursor.execute("SELECT id FROM courses LIMIT 1")
        course_id = cursor.fetchone()["id"]
        conn.close()

        # Call the get_course_modules tool
        result = mock_mcp.get_course_modules(ctx, course_id)

        # Verify the result
        assert isinstance(result, list)
        # Note: It's possible there are no modules for this course (SP25_CS_540_1 has 0 modules)

        # Call the get_course_modules tool with include_items=True
        result_with_items = mock_mcp.get_course_modules(
            ctx, course_id, include_items=True
        )

        # Verify the result
        assert isinstance(result_with_items, list)
        assert len(result_with_items) == len(result)

        # If there are modules, check that they have the expected structure
        if len(result) > 0:
            first_module = result[0]
            assert "id" in first_module
            assert "name" in first_module

            # If include_items=True, check that items are included
            if len(result_with_items) > 0:
                first_module_with_items = result_with_items[0]
                assert "items" in first_module_with_items
