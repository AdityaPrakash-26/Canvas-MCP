#!/usr/bin/env python3
"""
Comprehensive tool testing script for Canvas-MCP.

This script tests all tools in the Canvas-MCP server using a mock MCP server.
It verifies that each tool functions correctly with various inputs.

Usage:
    python scripts/diagnostics/test_tools_comprehensive.py [--verbose] [--fix]

Options:
    --verbose       Enable verbose logging
    --fix           Attempt to fix identified issues
"""

import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.config import API_KEY, API_URL
from src.canvas_mcp.sync.service import SyncService
from src.canvas_mcp.tools.announcements import register_announcement_tools

# Import tool registration functions
from src.canvas_mcp.tools.assignments import register_assignment_tools
from src.canvas_mcp.tools.courses import register_course_tools
from src.canvas_mcp.tools.files import register_file_tools
from src.canvas_mcp.tools.modules import register_module_tools
from src.canvas_mcp.tools.search import register_search_tools
from src.canvas_mcp.tools.syllabus import register_syllabus_tools
from src.canvas_mcp.tools.sync import register_sync_tools
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Import the mock MCP server
from tests.mock_mcp import create_mock_mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tools_test")


def setup_test_environment(test_db_path=None):
    """Set up the test environment with API adapter, database manager, and mock MCP server."""
    # Get API credentials
    api_key = API_KEY
    api_url = API_URL

    if not api_key or not api_url:
        logger.error(
            "Canvas API credentials not found. Please set CANVAS_API_KEY and CANVAS_API_URL environment variables."
        )
        sys.exit(1)

    # Create a test database path
    if test_db_path is None:
        test_db_path = Path("data/tools_test.db")

    test_db_path = Path(test_db_path)
    test_db_path.parent.mkdir(exist_ok=True)

    # Initialize components
    try:
        from canvasapi import Canvas

        canvas = Canvas(api_url, api_key)
        api_adapter = CanvasApiAdapter(canvas)
        db_manager = DatabaseManager(str(test_db_path))
        sync_service = SyncService(db_manager, api_adapter)

        # Create a mock MCP server
        mock_mcp = create_mock_mcp("TestMCP")

        # Register all tools with the mock MCP server
        register_sync_tools(mock_mcp)
        register_course_tools(mock_mcp)
        register_assignment_tools(mock_mcp)
        register_module_tools(mock_mcp)
        register_syllabus_tools(mock_mcp)
        register_announcement_tools(mock_mcp)
        register_file_tools(mock_mcp)
        register_search_tools(mock_mcp)

        # Set the lifespan context
        mock_mcp.set_lifespan_context(
            {
                "db_manager": db_manager,
                "api_adapter": api_adapter,
                "sync_service": sync_service,
            }
        )

        return mock_mcp, sync_service, db_manager, api_adapter
    except Exception as e:
        logger.error(f"Error setting up test environment: {e}")
        sys.exit(1)


def initialize_database(db_path):
    """Initialize the database with the required tables."""
    logger.info(f"Initializing database at {db_path}")

    if not os.path.exists(db_path):
        # Import the database initialization function
        from tests.init_db import create_tables, create_views

        # Create a new connection for initialization
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables and views
        create_tables(cursor)
        create_views(cursor)

        # Commit changes
        conn.commit()
        conn.close()

        logger.info("Database initialized successfully")
    else:
        logger.info("Database already exists")


def test_sync_tools(mock_mcp):
    """Test the sync tools."""
    logger.info("Testing sync tools...")

    ctx = mock_mcp.create_context()

    # Test sync_canvas_data
    logger.info("Testing sync_canvas_data...")
    try:
        result = mock_mcp.execute_tool("sync_canvas_data", ctx)
        logger.info(f"sync_canvas_data result: {result}")

        if "error" in result:
            logger.error(f"Error in sync_canvas_data: {result['error']}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error testing sync_canvas_data: {e}")
        return False


def test_course_tools(mock_mcp):
    """Test the course tools."""
    logger.info("Testing course tools...")

    ctx = mock_mcp.create_context()

    # Test get_course_list
    logger.info("Testing get_course_list...")
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        logger.info(f"Found {len(courses)} courses")

        if not courses:
            logger.warning("No courses found, some tests may be skipped")
            return True

        # Test get_course_details
        course_id = courses[0]["id"]
        logger.info(f"Testing get_course_details with course_id={course_id}...")
        course_details = mock_mcp.execute_tool(
            "get_course_details", ctx, course_id=course_id
        )
        logger.info(f"Course details: {course_details}")

        return True
    except Exception as e:
        logger.error(f"Error testing course tools: {e}")
        return False


def test_assignment_tools(mock_mcp):
    """Test the assignment tools."""
    logger.info("Testing assignment tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping assignment tools tests")
            return True

        course_id = courses[0]["id"]

        # Test get_course_assignments
        logger.info(f"Testing get_course_assignments with course_id={course_id}...")
        assignments = mock_mcp.execute_tool(
            "get_course_assignments", ctx, course_id=course_id
        )
        logger.info(f"Found {len(assignments)} assignments")

        # Test get_upcoming_deadlines
        logger.info("Testing get_upcoming_deadlines...")
        deadlines = mock_mcp.execute_tool("get_upcoming_deadlines", ctx, days=30)
        logger.info(f"Found {len(deadlines)} upcoming deadlines")

        # Test get_assignment_details if assignments exist
        if assignments:
            assignment_name = assignments[0]["title"]
            logger.info(
                f"Testing get_assignment_details with assignment_name={assignment_name}..."
            )
            assignment_details = mock_mcp.execute_tool(
                "get_assignment_details",
                ctx,
                course_id=course_id,
                assignment_name=assignment_name,
            )
            logger.info(f"Assignment details: {assignment_details}")

        return True
    except Exception as e:
        logger.error(f"Error testing assignment tools: {e}")
        return False


def test_module_tools(mock_mcp):
    """Test the module tools."""
    logger.info("Testing module tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping module tools tests")
            return True

        course_id = courses[0]["id"]

        # Test get_course_modules
        logger.info(f"Testing get_course_modules with course_id={course_id}...")
        modules = mock_mcp.execute_tool("get_course_modules", ctx, course_id=course_id)
        logger.info(f"Found {len(modules)} modules")

        # Test get_course_modules with include_items=True
        logger.info("Testing get_course_modules with include_items=True...")
        modules_with_items = mock_mcp.execute_tool(
            "get_course_modules", ctx, course_id=course_id, include_items=True
        )
        logger.info(f"Found {len(modules_with_items)} modules with items")

        return True
    except Exception as e:
        logger.error(f"Error testing module tools: {e}")
        return False


def test_syllabus_tools(mock_mcp):
    """Test the syllabus tools."""
    logger.info("Testing syllabus tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping syllabus tools tests")
            return True

        course_id = courses[0]["id"]

        # Test get_syllabus
        logger.info(f"Testing get_syllabus with course_id={course_id}...")
        syllabus = mock_mcp.execute_tool("get_syllabus", ctx, course_id=course_id)
        logger.info(f"Syllabus: {syllabus}")

        # Test get_syllabus with different formats
        for format in ["html", "text", "markdown"]:
            logger.info(f"Testing get_syllabus with format={format}...")
            syllabus = mock_mcp.execute_tool(
                "get_syllabus", ctx, course_id=course_id, format=format
            )
            logger.info(f"Syllabus in {format} format retrieved")

        return True
    except Exception as e:
        logger.error(f"Error testing syllabus tools: {e}")
        return False


def test_announcement_tools(mock_mcp):
    """Test the announcement tools."""
    logger.info("Testing announcement tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping announcement tools tests")
            return True

        course_id = courses[0]["id"]

        # Test get_course_announcements
        logger.info(f"Testing get_course_announcements with course_id={course_id}...")
        announcements = mock_mcp.execute_tool(
            "get_course_announcements", ctx, course_id=course_id
        )
        logger.info(f"Found {len(announcements)} announcements")

        return True
    except Exception as e:
        logger.error(f"Error testing announcement tools: {e}")
        return False


def test_file_tools(mock_mcp):
    """Test the file tools."""
    logger.info("Testing file tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping file tools tests")
            return True

        course_id = courses[0]["id"]

        # Test get_course_files
        logger.info(f"Testing get_course_files with course_id={course_id}...")
        files = mock_mcp.execute_tool("get_course_files", ctx, course_id=course_id)
        logger.info(f"Found {len(files)} files")

        return True
    except Exception as e:
        logger.error(f"Error testing file tools: {e}")
        return False


def test_search_tools(mock_mcp):
    """Test the search tools."""
    logger.info("Testing search tools...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping search tools tests")
            return True

        course_id = courses[0]["id"]

        # Test search_course_content
        logger.info(f"Testing search_course_content with course_id={course_id}...")
        search_results = mock_mcp.execute_tool(
            "search_course_content", ctx, course_id=course_id, query="assignment"
        )
        logger.info(f"Found {len(search_results)} search results")

        return True
    except Exception as e:
        logger.error(f"Error testing search tools: {e}")
        return False


def test_tool_performance(mock_mcp):
    """Test the performance of tools."""
    logger.info("Testing tool performance...")

    ctx = mock_mcp.create_context()

    # Get course list first
    try:
        courses = mock_mcp.execute_tool("get_course_list", ctx)
        if not courses:
            logger.warning("No courses found, skipping performance tests")
            return True

        course_id = courses[0]["id"]

        # Test get_course_assignments performance
        logger.info("Testing get_course_assignments performance...")
        start_time = time.time()
        for _ in range(5):
            mock_mcp.execute_tool("get_course_assignments", ctx, course_id=course_id)
        end_time = time.time()
        logger.info(
            f"get_course_assignments: 5 calls in {end_time - start_time:.2f} seconds"
        )

        # Test get_course_modules performance
        logger.info("Testing get_course_modules performance...")
        start_time = time.time()
        for _ in range(5):
            mock_mcp.execute_tool("get_course_modules", ctx, course_id=course_id)
        end_time = time.time()
        logger.info(
            f"get_course_modules: 5 calls in {end_time - start_time:.2f} seconds"
        )

        # Test search_course_content performance
        logger.info("Testing search_course_content performance...")
        start_time = time.time()
        for i in range(5):
            search_term = f"test{i}"
            mock_mcp.execute_tool(
                "search_course_content", ctx, course_id=course_id, query=search_term
            )
        end_time = time.time()
        logger.info(
            f"search_course_content: 5 calls in {end_time - start_time:.2f} seconds"
        )

        return True
    except Exception as e:
        logger.error(f"Error testing tool performance: {e}")
        return False


def test_error_handling(mock_mcp):
    """Test error handling in tools."""
    logger.info("Testing error handling in tools...")

    ctx = mock_mcp.create_context()

    # Test with invalid course ID
    logger.info("Testing with invalid course ID...")
    try:
        invalid_course_id = 999999
        mock_mcp.execute_tool(
            "get_course_assignments", ctx, course_id=invalid_course_id
        )
        logger.warning("Expected an exception but none was raised")
    except Exception as e:
        logger.info(f"Caught expected exception: {e}")

    # Test with invalid parameters
    logger.info("Testing with invalid parameters...")
    try:
        mock_mcp.execute_tool("get_upcoming_deadlines", ctx, days="invalid")
        logger.warning("Expected an exception but none was raised")
    except Exception as e:
        logger.info(f"Caught expected exception: {e}")

    # Test with non-existent tool
    logger.info("Testing with non-existent tool...")
    try:
        mock_mcp.execute_tool("non_existent_tool", ctx)
        logger.warning("Expected an exception but none was raised")
    except Exception as e:
        logger.info(f"Caught expected exception: {e}")

    return True


def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description="Test Canvas-MCP tools")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix identified issues"
    )
    parser.add_argument("--db", help="Path to the test database")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting comprehensive tool tests")

    # Setup test environment
    mock_mcp, sync_service, db_manager, api_adapter = setup_test_environment(args.db)

    # Initialize the database
    initialize_database(db_manager.db_path)

    # Run tests
    test_results = {
        "sync_tools": test_sync_tools(mock_mcp),
        "course_tools": test_course_tools(mock_mcp),
        "assignment_tools": test_assignment_tools(mock_mcp),
        "module_tools": test_module_tools(mock_mcp),
        "syllabus_tools": test_syllabus_tools(mock_mcp),
        "announcement_tools": test_announcement_tools(mock_mcp),
        "file_tools": test_file_tools(mock_mcp),
        "search_tools": test_search_tools(mock_mcp),
        "tool_performance": test_tool_performance(mock_mcp),
        "error_handling": test_error_handling(mock_mcp),
    }

    # Summarize results
    logger.info("\nTool test summary:")
    all_passed = True
    for test_name, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False

    if all_passed:
        logger.info("All tool tests passed!")
        sys.exit(0)
    else:
        logger.error("Some tool tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
