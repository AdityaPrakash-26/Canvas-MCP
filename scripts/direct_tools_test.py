#!/usr/bin/env python3
"""
Direct Canvas MCP Tools Tester

This script directly tests the Canvas MCP tools without using the MCP client-server architecture.
It imports the tools directly and calls them with the necessary context.

Usage:
    python scripts/direct_tools_test.py
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
import src.canvas_mcp.config as config

# Import tool modules
from scripts.extract_tools_test import extract_tools
from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.sync.service import SyncService
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("direct_tools_test")


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

    # Get course details from course list
    logger.info(f"Getting course details for course_id={course_id}...")
    course_details = next((c for c in courses if c["id"] == course_id), None)
    logger.info(f"Course details: {course_details}")

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
    tools["get_syllabus"](ctx, course_id=course_id)
    logger.info("Syllabus retrieved")

    # Test get_course_announcements
    logger.info(f"Testing get_course_announcements with course_id={course_id}...")
    announcements = tools["get_course_announcements"](ctx, course_id=course_id)
    logger.info(f"Found {len(announcements)} announcements")

    # Test get_course_files
    logger.info(f"Testing get_course_files with course_id={course_id}...")
    files = tools["get_course_files"](ctx, course_id=course_id)
    logger.info(f"Found {len(files)} files")

    # Test get_course_calendar_events
    logger.info(f"Testing get_course_calendar_events with course_id={course_id}...")
    calendar_events = tools["get_course_calendar_events"](ctx, course_id=course_id)
    logger.info(f"Found {len(calendar_events)} calendar events")

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

    print("\nCanvas MCP Direct Tool Tester")
    print("============================")
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
                print("  call <name> [args]- Call a tool with optional JSON arguments")
                print("  exit              - Exit the tester")
                continue

            if command.lower() == "tools":
                print("\nAvailable Tools:")
                for tool_name in tools:
                    print(f"  - {tool_name}")
                continue

            if command.lower() == "test":
                test_tools()
                continue

            if command.lower().startswith("call "):
                # Parse tool command: call <name> [args as JSON]
                parts = command.split(" ", 2)
                if len(parts) < 2:
                    print("Usage: call <name> [args as JSON]")
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
    parser = argparse.ArgumentParser(description="Direct Canvas MCP Tools Tester")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run tests automatically",
    )
    args = parser.parse_args()

    if args.test:
        test_tools()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
