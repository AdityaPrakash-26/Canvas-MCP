"""
Tools for testing.

This module exposes the Canvas MCP tools for testing purposes.
It creates a mock MCP server and registers all the tools,
then exposes them for direct use in tests.
"""

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

# Create a mock MCP server for testing
mock_mcp = FastMCP("Mock MCP for Testing")

# Dictionary to store the tools
tools: dict[str, Callable] = {}


# Create a mock tool decorator that captures the function
def mock_tool_decorator(func):
    """Mock tool decorator that captures the function."""
    # Store the function in the tools dictionary
    tools[func.__name__] = func
    return func


# Replace the tool decorator with our mock
mock_mcp.tool = mock_tool_decorator

# Import and register all the tools
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.tools.assignments import register_assignment_tools
from canvas_mcp.tools.courses import register_course_tools
from canvas_mcp.tools.files import register_file_tools
from canvas_mcp.tools.modules import register_module_tools
from canvas_mcp.tools.search import register_search_tools
from canvas_mcp.tools.syllabus import register_syllabus_tools
from canvas_mcp.tools.sync import register_sync_tools

# Register all tools with our mock MCP
register_announcement_tools(mock_mcp)
register_assignment_tools(mock_mcp)
register_course_tools(mock_mcp)
register_file_tools(mock_mcp)
register_module_tools(mock_mcp)
register_search_tools(mock_mcp)
register_syllabus_tools(mock_mcp)
register_sync_tools(mock_mcp)

# Export all the tools
sync_canvas_data = tools["sync_canvas_data"]
get_course_list = tools["get_course_list"]
get_course_assignments = tools["get_course_assignments"]
get_assignment_details = tools["get_assignment_details"]
get_upcoming_deadlines = tools["get_upcoming_deadlines"]
get_course_modules = tools["get_course_modules"]
get_syllabus = tools["get_syllabus"]
get_syllabus_file = tools["get_syllabus_file"]
get_course_files = tools["get_course_files"]
extract_text_from_course_file = tools["extract_text_from_course_file"]
get_course_announcements = tools["get_course_announcements"]
search_course_content = tools["search_course_content"]
