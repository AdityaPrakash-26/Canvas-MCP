#!/usr/bin/env python3
"""
Tool integration test script for Canvas-MCP.

This script tests the integration between different tools and components
to ensure they work together correctly.

Usage:
    python scripts/test_tools_integration.py [--verbose]

Options:
    --verbose       Enable verbose logging
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import MCP server
from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.config import API_KEY, API_URL
from src.canvas_mcp.sync.service import SyncService

# Import tools
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tools_test")


def setup_test_environment():
    """Set up the test environment with API adapter and database manager."""
    # Get API credentials
    api_key = API_KEY
    api_url = API_URL

    if not api_key or not api_url:
        logger.error(
            "Canvas API credentials not found. Please set CANVAS_API_KEY and CANVAS_API_URL environment variables."
        )
        sys.exit(1)

    # Create a test database path
    test_db_path = Path("data/tools_test.db")
    test_db_path.parent.mkdir(exist_ok=True)

    # Initialize components
    try:
        from canvasapi import Canvas

        canvas = Canvas(api_url, api_key)
        api_adapter = CanvasApiAdapter(canvas)
        db_manager = DatabaseManager(str(test_db_path))
        sync_service = SyncService(db_manager, api_adapter)

        # Create a mock context for tools
        lifespan_context = {
            "db_manager": db_manager,
            "api_adapter": api_adapter,
            "sync_service": sync_service,
        }
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        return ctx, sync_service, db_manager, api_adapter
    except Exception as e:
        logger.error(f"Error setting up test environment: {e}")
        sys.exit(1)


def test_tool_chain(ctx):
    """Test a chain of tool calls to simulate a typical user interaction."""
    logger.info("Testing tool chain...")

    # Step 1: Sync data
    logger.info("Step 1: Syncing Canvas data...")
    sync_result = sync_canvas_data(ctx)
    logger.info(f"Sync result: {sync_result}")

    if "error" in sync_result:
        logger.error(f"Sync failed: {sync_result['error']}")
        return False

    # Step 2: Get course list
    logger.info("Step 2: Getting course list...")
    courses = get_course_list(ctx)
    logger.info(f"Found {len(courses)} courses")

    if not courses:
        logger.error("No courses found")
        return False

    # Select a course for further testing
    course = courses[0]
    course_id = course["id"]
    logger.info(f"Selected course: {course['course_code']} (ID: {course_id})")

    # Step 3: Get course assignments
    logger.info("Step 3: Getting course assignments...")
    assignments = get_course_assignments(ctx, course_id)
    logger.info(f"Found {len(assignments)} assignments for course {course_id}")

    # Step 4: Get upcoming deadlines
    logger.info("Step 4: Getting upcoming deadlines...")
    deadlines = get_upcoming_deadlines(ctx, course_id, days=30)
    logger.info(f"Found {len(deadlines)} upcoming deadlines for course {course_id}")

    # Step 5: Get course modules
    logger.info("Step 5: Getting course modules...")
    modules = get_course_modules(ctx, course_id)
    logger.info(f"Found {len(modules)} modules for course {course_id}")

    # Step 6: Get syllabus
    logger.info("Step 6: Getting syllabus...")
    get_syllabus(ctx, course_id)
    logger.info(f"Got syllabus for course {course_id}")

    # Step 7: Get calendar events
    logger.info("Step 7: Getting calendar events...")
    calendar_events = get_course_calendar_events(ctx, course_id)
    logger.info(f"Found {len(calendar_events)} calendar events for course {course_id}")

    # Step 8: Search course content
    logger.info("Step 8: Searching course content...")
    search_term = "assignment"  # A common term likely to be found
    search_results = search_course_content(ctx, course_id, search_term)
    logger.info(f"Found {len(search_results)} results for search term '{search_term}'")

    logger.info("Tool chain test completed successfully")
    return True


def test_tool_error_handling(ctx):
    """Test how tools handle errors."""
    logger.info("Testing tool error handling...")

    # Test with invalid course ID
    logger.info("Testing get_course_assignments with invalid course ID...")
    invalid_course_id = 999999
    assignments = get_course_assignments(ctx, invalid_course_id)
    logger.info(f"Result: {assignments}")

    # Test search with empty query
    logger.info("Testing search_course_content with empty query...")
    courses = get_course_list(ctx)
    if courses:
        course_id = courses[0]["id"]
        search_results = search_course_content(ctx, course_id, "")
        logger.info(f"Result: {search_results}")
    else:
        logger.warning("No courses found, skipping test")

    # Test get_syllabus with invalid format
    logger.info("Testing get_syllabus with invalid format...")
    if courses:
        course_id = courses[0]["id"]
        try:
            syllabus = get_syllabus(ctx, course_id, format="invalid_format")
            logger.info(f"Result: {syllabus}")
        except Exception as e:
            logger.info(f"Caught expected exception: {e}")
    else:
        logger.warning("No courses found, skipping test")

    logger.info("Tool error handling test completed")
    return True


def test_tool_performance(ctx):
    """Test the performance of tools with repeated calls."""
    logger.info("Testing tool performance...")

    # Get course list
    courses = get_course_list(ctx)
    if not courses:
        logger.warning("No courses found, skipping performance test")
        return True

    course_id = courses[0]["id"]

    # Test get_course_assignments performance
    logger.info("Testing get_course_assignments performance...")
    start_time = time.time()
    for _ in range(10):
        get_course_assignments(ctx, course_id)
    end_time = time.time()
    logger.info(
        f"get_course_assignments: 10 calls in {end_time - start_time:.2f} seconds"
    )

    # Test get_course_modules performance
    logger.info("Testing get_course_modules performance...")
    start_time = time.time()
    for _ in range(10):
        get_course_modules(ctx, course_id)
    end_time = time.time()
    logger.info(f"get_course_modules: 10 calls in {end_time - start_time:.2f} seconds")

    # Test search_course_content performance
    logger.info("Testing search_course_content performance...")
    start_time = time.time()
    for i in range(10):
        search_term = f"test{i}"
        search_course_content(ctx, course_id, search_term)
    end_time = time.time()
    logger.info(
        f"search_course_content: 10 calls in {end_time - start_time:.2f} seconds"
    )

    logger.info("Tool performance test completed")
    return True


def main():
    """Main function to run the tool integration test script."""
    parser = argparse.ArgumentParser(description="Test tool integration")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting tool integration tests")

    # Setup test environment
    ctx, sync_service, db_manager, api_adapter = setup_test_environment()

    # Run tests
    tool_chain_ok = test_tool_chain(ctx)
    tool_error_handling_ok = test_tool_error_handling(ctx)
    tool_performance_ok = test_tool_performance(ctx)

    # Summarize results
    logger.info("\nTool integration test summary:")
    logger.info(f"Tool chain test: {'OK' if tool_chain_ok else 'FAILED'}")
    logger.info(
        f"Tool error handling test: {'OK' if tool_error_handling_ok else 'FAILED'}"
    )
    logger.info(f"Tool performance test: {'OK' if tool_performance_ok else 'FAILED'}")

    if not all([tool_chain_ok, tool_error_handling_ok, tool_performance_ok]):
        logger.warning("Some tool integration tests failed")
        sys.exit(1)
    else:
        logger.info("All tool integration tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
