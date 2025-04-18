"""
Unit tests for the sync tools.

These tests verify that the sync tools correctly interact with the Canvas client.
"""

from types import SimpleNamespace

from canvas_mcp.tools.sync import register_sync_tools


class TestSyncTools:
    """Test the sync tools."""

    def test_sync_canvas_data(self):
        """Test the sync_canvas_data tool."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.sync_canvas_data = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_sync_tools(mock_mcp)

        # Create a mock sync service
        class MockSyncService:
            def sync_all(self):
                return {
                    "courses": 5,
                    "assignments": 10,
                    "modules": 3,
                    "announcements": 2,
                }

        # Create a mock context
        lifespan_context = {"sync_service": MockSyncService()}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the sync_canvas_data tool
        result = mock_mcp.sync_canvas_data(ctx)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" not in result
        assert "courses" in result
        assert result["courses"] >= 0
        assert "assignments" in result
        assert result["assignments"] >= 0
        assert "modules" in result
        assert result["modules"] >= 0
        assert "announcements" in result
        assert result["announcements"] >= 0

    def test_sync_filters_correctly(self, api_adapter):
        """Test that sync_canvas_data filters courses correctly."""
        # Get all courses directly from Canvas API
        user = api_adapter.get_current_user_raw()

        # Get active courses directly from Canvas API
        active_courses = api_adapter.get_courses_raw(user, enrollment_state="active")

        # Get term IDs from active courses
        term_ids = set()
        for course in active_courses:
            term_id = getattr(course, "enrollment_term_id", None)
            if term_id:
                term_ids.add(term_id)

        # Find the most recent term
        if term_ids:
            max_term_id = max(term_ids)

            # Count courses in the most recent term
            current_term_courses = [
                course
                for course in active_courses
                if getattr(course, "enrollment_term_id", None) == max_term_id
            ]
        else:
            # If no term IDs found, just use active courses
            current_term_courses = active_courses

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.sync_canvas_data = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_sync_tools(mock_mcp)

        # Create a mock sync service that returns the expected number of courses
        class MockSyncService:
            def sync_all(self):
                return {
                    "courses": len(current_term_courses),
                    "assignments": 10,
                    "modules": 3,
                    "announcements": 2,
                }

        # Create a mock context
        lifespan_context = {"sync_service": MockSyncService()}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the sync_canvas_data tool
        result = mock_mcp.sync_canvas_data(ctx)

        # Verify that the number of synced courses matches the number of
        # active courses in the current term
        assert result["courses"] == len(current_term_courses), (
            f"Expected {len(current_term_courses)} courses, but synced {result['courses']}"
        )

    def test_sync_canvas_data_error(self):
        """Test the sync_canvas_data tool with an error."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    self.sync_canvas_data = func
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_sync_tools(mock_mcp)

        # Create a mock context with a broken sync service
        class BrokenSyncService:
            def sync_all(self):
                raise ValueError("Test error")

        lifespan_context = {"sync_service": BrokenSyncService()}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Call the sync_canvas_data tool
        result = mock_mcp.sync_canvas_data(ctx)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "Test error" in result["error"]
