"""
Test client for Canvas MCP integration tests.

This module provides a client for testing Canvas MCP functionality
without going through the MCP server. It initializes the real components
and provides a clean interface for testing.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from canvasapi import Canvas

from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.sync import SyncService

# Import the tool registration functions
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.tools.assignments import register_assignment_tools
from canvas_mcp.tools.courses import register_course_tools
from canvas_mcp.tools.files import register_file_tools
from canvas_mcp.tools.modules import register_module_tools
from canvas_mcp.tools.search import register_search_tools
from canvas_mcp.tools.syllabus import register_syllabus_tools
from canvas_mcp.tools.sync import register_sync_tools
from canvas_mcp.utils.db_manager import DatabaseManager


class CanvasMCPTestClient:
    """Test client for Canvas MCP integration tests."""

    def __init__(self, db_path: Path):
        """
        Initialize the test client.

        Args:
            db_path: Path to the test database
        """
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)

        # Get API credentials from environment
        api_key = os.environ.get("CANVAS_API_KEY")
        api_url = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

        if not api_key:
            raise ValueError(
                "CANVAS_API_KEY environment variable is required for integration tests"
            )

        # Initialize Canvas API adapter and sync service
        try:
            canvas_api_client = Canvas(api_url, api_key)
            self.api_adapter = CanvasApiAdapter(canvas_api_client)
        except Exception as e:
            print(f"Error initializing Canvas API adapter: {e}")
            self.api_adapter = CanvasApiAdapter(None)

        self.sync_service = SyncService(self.db_manager, self.api_adapter)

        # Create a context object for the tools
        lifespan_context_data = {
            "db_manager": self.db_manager,
            "api_adapter": self.api_adapter,
            "sync_service": self.sync_service,
        }
        request_context_mock = SimpleNamespace(lifespan_context=lifespan_context_data)
        self.context = SimpleNamespace(request_context=request_context_mock)

        # Initialize the tool functions
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize the tool functions."""

        # Create a simple class to capture the tool functions
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        # Create a tool capture instance
        tool_capture = ToolCapture()

        # Register all the tools
        register_announcement_tools(tool_capture)
        register_assignment_tools(tool_capture)
        register_course_tools(tool_capture)
        register_file_tools(tool_capture)
        register_module_tools(tool_capture)
        register_search_tools(tool_capture)
        register_syllabus_tools(tool_capture)
        register_sync_tools(tool_capture)

        # Store the tool functions
        self.tools = tool_capture.tools

    def sync_canvas_data(self) -> dict[str, Any]:
        """
        Synchronize data from Canvas LMS to the local database.

        Returns:
            Dictionary with counts of synced items
        """
        # We can either use the tool or call the sync_service directly
        # Using the tool ensures we're testing the actual tool implementation
        return self.tools["sync_canvas_data"](self.context)

    def get_course_list(self) -> list[dict[str, Any]]:
        """
        Get list of all courses in the database.

        Returns:
            List of course information
        """
        return self.tools["get_course_list"](self.context)

    def get_course_assignments(self, course_id: int) -> list[dict[str, Any]]:
        """
        Get all assignments for a specific course.

        Args:
            course_id: Course ID

        Returns:
            List of assignments
        """
        return self.tools["get_course_assignments"](self.context, course_id)

    def get_assignment_details(
        self, course_id: int, assignment_name: str, include_canvas_data: bool = True
    ) -> dict[str, Any]:
        """
        Get comprehensive information about a specific assignment by name.

        Args:
            course_id: Course ID
            assignment_name: Name or partial name of the assignment
            include_canvas_data: Whether to include data from Canvas API if available

        Returns:
            Dictionary with assignment details and related resources
        """
        return self.tools["get_assignment_details"](
            self.context, course_id, assignment_name, include_canvas_data
        )

    def get_upcoming_deadlines(
        self, days: int = 7, course_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get upcoming assignment deadlines.

        Args:
            days: Number of days to look ahead
            course_id: Optional course ID to filter by

        Returns:
            List of upcoming deadlines
        """
        return self.tools["get_upcoming_deadlines"](self.context, days, course_id)

    def get_course_modules(
        self, course_id: int, include_items: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all modules for a specific course.

        Args:
            course_id: Course ID
            include_items: Whether to include module items

        Returns:
            List of modules
        """
        return self.tools["get_course_modules"](self.context, course_id, include_items)

    def get_syllabus(self, course_id: int, format: str = "raw") -> dict[str, Any]:
        """
        Get the syllabus for a specific course.

        Args:
            course_id: Course ID
            format: Format to return ("raw" for HTML, "parsed" for extracted text)

        Returns:
            Dictionary with syllabus content
        """
        return self.tools["get_syllabus"](self.context, course_id, format)

    def get_syllabus_file(
        self, course_id: int, extract_content: bool = True
    ) -> dict[str, Any]:
        """
        Attempt to find a syllabus file for a specific course.

        Args:
            course_id: Course ID
            extract_content: Whether to extract and store content from the syllabus file

        Returns:
            Dictionary with syllabus file information or error
        """
        return self.tools["get_syllabus_file"](self.context, course_id, extract_content)

    def get_course_files(
        self, course_id: int, file_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all files available in a specific course, with optional filtering by file type.

        Args:
            course_id: Course ID
            file_type: Optional file extension to filter by (e.g., 'pdf', 'docx')

        Returns:
            List of files with URLs
        """
        return self.tools["get_course_files"](self.context, course_id, file_type)

    def extract_text_from_course_file(
        self, file_url: str, file_type: str | None = None
    ) -> dict[str, Any]:
        """
        Extract text from a file.

        Args:
            file_url: URL of the file
            file_type: Optional file type to override auto-detection ('pdf', 'docx', 'url')

        Returns:
            Dictionary with extracted text and metadata
        """
        return self.tools["extract_text_from_course_file"](
            self.context, file_url, file_type
        )

    def get_course_announcements(
        self, course_id: int, limit: int = 10, num_weeks: int = 2
    ) -> list[dict[str, Any]]:
        """
        Get announcements for a specific course.

        Args:
            course_id: Course ID
            limit: Maximum number of announcements to return
            num_weeks: Number of weeks to look back for announcements

        Returns:
            List of announcements
        """
        return self.tools["get_course_announcements"](
            self.context, course_id, limit, num_weeks
        )

    def search_course_content(
        self, query: str, course_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for content across courses.

        Args:
            query: Search query
            course_id: Optional course ID to limit search

        Returns:
            List of matching items
        """
        return self.tools["search_course_content"](self.context, query, course_id)

    def get_course_communications(
        self, course_id: int, limit: int = 20, num_weeks: int = 2
    ) -> list[dict[str, Any]]:
        """
        Get all communications (announcements and conversations) for a specific course.

        Args:
            course_id: Course ID
            limit: Maximum number of communications to return
            num_weeks: Number of weeks to look back for communications

        Returns:
            List of communications (announcements and conversations)
        """
        return self.tools["get_course_communications"](
            self.context, course_id, limit, num_weeks
        )

    def get_all_communications(
        self, limit: int = 50, num_weeks: int = 2
    ) -> list[dict[str, Any]]:
        """
        Get all communications (announcements and conversations) from all courses.

        Args:
            limit: Maximum number of communications to return
            num_weeks: Number of weeks to look back for communications

        Returns:
            List of communications (announcements and conversations)
        """
        return self.tools["get_all_communications"](self.context, limit, num_weeks)
