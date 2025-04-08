#!/usr/bin/env python3
"""
Canvas MCP Tool Extractor and Tester

This script extracts the tool functions from the MCP server and tests them directly.
It preserves the existing architecture while allowing direct testing of the tools.

Usage:
    python scripts/extract_tools_test.py                      # Interactive mode
    python scripts/extract_tools_test.py --test               # Run all tests
    python scripts/extract_tools_test.py --list-tools         # List all available tools
    python scripts/extract_tools_test.py --tool <tool_name>   # Test a specific tool
    python scripts/extract_tools_test.py --tool <tool_name> --args '{"arg1": "value1"}' # Test with arguments
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.sync.service import SyncService
from src.canvas_mcp.utils.db_manager import DatabaseManager
import src.canvas_mcp.config as config

# Import tool registration functions
from src.canvas_mcp.tools.assignments import register_assignment_tools
from src.canvas_mcp.tools.courses import register_course_tools
from src.canvas_mcp.tools.modules import register_module_tools
from src.canvas_mcp.tools.search import register_search_tools
from src.canvas_mcp.tools.syllabus import register_syllabus_tools
from src.canvas_mcp.tools.sync import register_sync_tools
from src.canvas_mcp.tools.announcements import register_announcement_tools
from src.canvas_mcp.tools.files import register_file_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("extract_tools_test")


class MockMCP:
    """Mock MCP server for extracting tools."""

    def __init__(self):
        """Initialize the mock MCP server."""
        self.tools = {}

    def tool(self):
        """Decorator for registering tools."""

        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class MockContext:
    """Mock context for testing tools."""

    def __init__(self, db_manager, api_adapter, sync_service):
        """Initialize the mock context."""
        self.request_context = SimpleNamespace(
            lifespan_context={
                "db_manager": db_manager,
                "api_adapter": api_adapter,
                "sync_service": sync_service,
            }
        )


def pretty_print(data):
    """Pretty print data as JSON."""
    if data is None:
        print("None")
        return

    try:
        print(json.dumps(data, indent=2))
    except (TypeError, ValueError):
        print(data)


def extract_tools():
    """Extract tools from the MCP server."""
    # Create a mock MCP server
    mock_mcp = MockMCP()

    # Register all tools with the mock MCP server
    register_sync_tools(mock_mcp)
    register_course_tools(mock_mcp)
    register_assignment_tools(mock_mcp)
    register_module_tools(mock_mcp)
    register_syllabus_tools(mock_mcp)
    register_announcement_tools(mock_mcp)
    register_file_tools(mock_mcp)
    register_search_tools(mock_mcp)

    return mock_mcp.tools


def test_tools():
    """Test all Canvas MCP tools."""
    logger.info("Initializing components...")

    # Create database manager
    db_manager = DatabaseManager(config.DB_PATH)

    # Create Canvas API adapter
    try:
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)
        api_adapter = CanvasApiAdapter(canvas_api_client)
        logger.info("Canvas API adapter initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Canvas API adapter: {e}")
        api_adapter = CanvasApiAdapter(None)
        logger.warning(
            "Created database-only Canvas API adapter due to initialization error"
        )

    # Create Sync Service
    sync_service = SyncService(db_manager, api_adapter)
    logger.info("Sync service initialized successfully")

    # Create mock context
    ctx = MockContext(db_manager, api_adapter, sync_service)

    # Extract tools
    tools = extract_tools()

    # Test sync_canvas_data
    logger.info("Testing sync_canvas_data...")
    sync_result = tools["sync_canvas_data"](ctx)
    logger.info(f"sync_canvas_data result: {sync_result}")

    # Test get_course_list
    logger.info("Testing get_course_list...")
    courses = tools["get_course_list"](ctx)
    logger.info(f"Found {len(courses)} courses")

    if not courses:
        logger.warning("No courses found, some tests will be skipped")
        return

    # Get the first course ID
    course_id = courses[0]["id"]
    logger.info(f"Using course ID: {course_id}")

    # Check if get_course_details exists
    if "get_course_details" in tools:
        logger.info(f"Testing get_course_details with course_id={course_id}...")
        course_details = tools["get_course_details"](ctx, course_id=course_id)
        logger.info(f"Course details: {course_details}")
    else:
        logger.info("get_course_details function not found, skipping test")

    # Test get_course_assignments
    logger.info(f"Testing get_course_assignments with course_id={course_id}...")
    assignments = tools["get_course_assignments"](ctx, course_id=course_id)
    logger.info(f"Found {len(assignments)} assignments")

    # Test get_upcoming_deadlines
    logger.info("Testing get_upcoming_deadlines...")
    deadlines = tools["get_upcoming_deadlines"](ctx, days=30)
    logger.info(f"Found {len(deadlines)} upcoming deadlines")

    # Test get_course_modules
    logger.info(f"Testing get_course_modules with course_id={course_id}...")
    modules = tools["get_course_modules"](ctx, course_id=course_id)
    logger.info(f"Found {len(modules)} modules")

    # Test get_course_modules with include_items=True
    logger.info("Testing get_course_modules with include_items=True...")
    modules_with_items = tools["get_course_modules"](
        ctx, course_id=course_id, include_items=True
    )
    logger.info(f"Found {len(modules_with_items)} modules with items")

    # Test get_syllabus
    logger.info(f"Testing get_syllabus with course_id={course_id}...")
    syllabus = tools["get_syllabus"](ctx, course_id=course_id)
    logger.info("Syllabus retrieved successfully")
    logger.info(f"Syllabus type: {type(syllabus).__name__}")

    # Test get_course_announcements
    logger.info(f"Testing get_course_announcements with course_id={course_id}...")
    announcements = tools["get_course_announcements"](ctx, course_id=course_id)
    logger.info(f"Found {len(announcements)} announcements")

    # Test get_course_files
    logger.info(f"Testing get_course_files with course_id={course_id}...")
    files = tools["get_course_files"](ctx, course_id=course_id)
    logger.info(f"Found {len(files)} files")

    # Test search_course_content
    logger.info(f"Testing search_course_content with course_id={course_id}...")
    search_results = tools["search_course_content"](
        ctx, course_id=course_id, query="assignment"
    )
    logger.info(f"Found {len(search_results)} search results")

    logger.info("All tests completed successfully!")


def interactive_mode():
    """Run an interactive session to test tools."""
    logger.info("Initializing components...")

    # Create database manager
    db_manager = DatabaseManager(config.DB_PATH)

    # Create Canvas API adapter
    try:
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)
        api_adapter = CanvasApiAdapter(canvas_api_client)
        logger.info("Canvas API adapter initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Canvas API adapter: {e}")
        api_adapter = CanvasApiAdapter(None)
        logger.warning(
            "Created database-only Canvas API adapter due to initialization error"
        )

    # Create Sync Service
    sync_service = SyncService(db_manager, api_adapter)
    logger.info("Sync service initialized successfully")

    # Create mock context
    ctx = MockContext(db_manager, api_adapter, sync_service)

    # Extract tools
    tools = extract_tools()

    print("\nCanvas MCP Tool Tester")
    print("====================")
    print("Type 'help' for available commands")
    print("Type 'exit' to quit")

    while True:
        try:
            command = input("\n> ").strip()

            if command.lower() in ["exit", "quit"]:
                break

            if command.lower() == "help":
                print("\nAvailable Commands:")
                print("  help              - Show this help message")
                print("  tools             - List available tools")
                print("  test              - Run tests for all tools")
                print("  call <n> [args]- Call a tool with optional JSON arguments")
                print("  exit              - Exit the tester")
                continue

            if command.lower() == "tools":
                print("\nAvailable Tools:")
                for tool_name in sorted(tools.keys()):
                    print(f"  - {tool_name}")
                continue

            if command.lower() == "test":
                test_tools()
                continue

            if command.lower().startswith("call "):
                # Parse tool command: call <n> [args as JSON]
                parts = command.split(" ", 2)
                if len(parts) < 2:
                    print("Usage: call <n> [args as JSON]")
                    continue

                tool_name = parts[1]
                if tool_name not in tools:
                    print(f"Tool '{tool_name}' not found")
                    continue

                args = {}
                if len(parts) > 2:
                    try:
                        args = json.loads(parts[2])
                    except json.JSONDecodeError:
                        print("Error: Arguments must be valid JSON")
                        continue

                print(f"Calling tool {tool_name} with args: {args}")
                result = tools[tool_name](ctx, **args)
                print("\nResult:")
                pretty_print(result)
                continue

            print("Unknown command. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Canvas MCP Tool Extractor and Tester")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run tests automatically",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools",
    )
    parser.add_argument(
        "--tool",
        type=str,
        help="Specify a tool to test directly",
    )
    parser.add_argument(
        "--args",
        type=str,
        default="{}",
        help="JSON-formatted arguments for the tool (example: '{\"course_id\": 123}')",
    )
    args = parser.parse_args()

    # Initialize components if needed for any mode except help
    if args.list_tools:
        # Initialize components
        db_manager = DatabaseManager(config.DB_PATH)
        try:
            from canvasapi import Canvas

            canvas_api_client = Canvas(config.API_URL, config.API_KEY)
            api_adapter = CanvasApiAdapter(canvas_api_client)
            logger.info("Canvas API adapter initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Canvas API adapter: {e}")
            api_adapter = CanvasApiAdapter(None)
            logger.warning(
                "Created database-only Canvas API adapter due to initialization error"
            )

        sync_service = SyncService(db_manager, api_adapter)
        ctx = MockContext(db_manager, api_adapter, sync_service)

        # Extract tools
        tools = extract_tools()

        # List all available tools
        print("\nAvailable Tools:")
        for tool_name in sorted(tools.keys()):
            print(f"  - {tool_name}")
        return
    elif args.tool:
        # Run a specific tool
        logger.info(f"Testing tool: {args.tool}")

        # Initialize components
        db_manager = DatabaseManager(config.DB_PATH)
        try:
            from canvasapi import Canvas

            canvas_api_client = Canvas(config.API_URL, config.API_KEY)
            api_adapter = CanvasApiAdapter(canvas_api_client)
            logger.info("Canvas API adapter initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Canvas API adapter: {e}")
            api_adapter = CanvasApiAdapter(None)
            logger.warning(
                "Created database-only Canvas API adapter due to initialization error"
            )

        sync_service = SyncService(db_manager, api_adapter)
        ctx = MockContext(db_manager, api_adapter, sync_service)

        # Extract tools
        tools = extract_tools()

        if args.tool not in tools:
            logger.error(
                f"Tool '{args.tool}' not found. Available tools: {', '.join(sorted(tools.keys()))}"
            )
            return

        # Parse arguments
        try:
            tool_args = json.loads(args.args)
            logger.info(f"Using arguments: {tool_args}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON arguments: {args.args}")
            return

        # Call the tool
        try:
            result = tools[args.tool](ctx, **tool_args)
            print("\nResult:")
            pretty_print(result)
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
    elif args.test:
        test_tools()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
