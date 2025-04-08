#!/usr/bin/env python3
"""
Error handling and edge case test script for Canvas-MCP.

This script deliberately tests error conditions and edge cases to ensure
that the application handles them gracefully.

Usage:
    python scripts/test_error_handling.py [--verbose]

Options:
    --verbose       Enable verbose logging
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.config import API_KEY, API_URL
from src.canvas_mcp.sync.service import SyncService
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("error_test")


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
    test_db_path = Path("data/error_test.db")
    test_db_path.parent.mkdir(exist_ok=True)

    # Initialize components
    try:
        from canvasapi import Canvas

        canvas = Canvas(api_url, api_key)
        api_adapter = CanvasApiAdapter(canvas)
        db_manager = DatabaseManager(str(test_db_path))
        sync_service = SyncService(db_manager, api_adapter)

        return sync_service, db_manager, api_adapter
    except Exception as e:
        logger.error(f"Error setting up test environment: {e}")
        sys.exit(1)


class MockCanvas:
    """Mock Canvas API that raises exceptions."""

    def __init__(
        self, exception_type=Exception, exception_message="Simulated API error"
    ):
        self.exception_type = exception_type
        self.exception_message = exception_message

    def get_current_user(self):
        """Simulate an API error."""
        raise self.exception_type(self.exception_message)

    def get_course(self, course_id):
        """Simulate an API error."""
        raise self.exception_type(self.exception_message)

    def get_courses(self, **kwargs):
        """Simulate an API error."""
        raise self.exception_type(self.exception_message)


class MockDatabaseManager:
    """Mock database manager that raises exceptions."""

    def __init__(
        self, exception_type=Exception, exception_message="Simulated database error"
    ):
        self.exception_type = exception_type
        self.exception_message = exception_message

    def connect(self):
        """Simulate a database connection error."""
        raise self.exception_type(self.exception_message)

    def with_connection(self, func):
        """Simulate a database connection error in the wrapper."""

        def wrapper(*args, **kwargs):
            raise self.exception_type(self.exception_message)

        return wrapper


def test_api_error_handling(sync_service, api_adapter):
    """Test how the application handles API errors."""
    logger.info("Testing API error handling...")

    # Save the original canvas instance
    original_canvas = api_adapter.canvas

    try:
        # Test with a mock canvas that raises exceptions
        api_adapter.canvas = MockCanvas()

        # Test sync_courses with API error
        logger.info("Testing sync_courses with API error...")
        try:
            sync_service.sync_courses()
            logger.error("Expected an exception but none was raised")
        except Exception as e:
            logger.info(f"Caught expected exception: {e}")

        # Test get_course_list with API error
        logger.info("Testing get_course_list with API error...")
        try:
            # We need to access the database directly since we're testing API errors
            conn, cursor = sync_service.db_manager.connect()
            cursor.execute("SELECT * FROM courses LIMIT 1")
            course = cursor.fetchone()
            conn.close()

            if course:
                course_id = course["id"]
                sync_service.sync_assignments([course_id])
                logger.error("Expected an exception but none was raised")
            else:
                logger.warning("No courses found in database, skipping test")
        except Exception as e:
            logger.info(f"Caught expected exception: {e}")

        logger.info("API error handling tests completed")
    finally:
        # Restore the original canvas instance
        api_adapter.canvas = original_canvas


def test_database_error_handling(sync_service, db_manager):
    """Test how the application handles database errors."""
    logger.info("Testing database error handling...")

    # Save the original db_manager
    original_db_manager = sync_service.db_manager

    try:
        # Test with a mock db_manager that raises exceptions
        sync_service.db_manager = MockDatabaseManager()

        # Test sync_courses with database error
        logger.info("Testing sync_courses with database error...")
        try:
            sync_service.sync_courses()
            logger.error("Expected an exception but none was raised")
        except Exception as e:
            logger.info(f"Caught expected exception: {e}")

        logger.info("Database error handling tests completed")
    finally:
        # Restore the original db_manager
        sync_service.db_manager = original_db_manager


def test_edge_cases(sync_service, db_manager):
    """Test edge cases in the application."""
    logger.info("Testing edge cases...")

    # Test with invalid course IDs
    logger.info("Testing sync_assignments with invalid course IDs...")
    result = sync_service.sync_assignments([-1, -2, -3])
    logger.info(f"Result: {result}")

    # Test with empty course list
    logger.info("Testing sync_assignments with empty course list...")
    result = sync_service.sync_assignments([])
    logger.info(f"Result: {result}")

    # Test with None course list
    logger.info("Testing sync_assignments with None course list...")
    result = sync_service.sync_assignments(None)
    logger.info(f"Result: {result}")

    # Test with very large term_id
    logger.info("Testing sync_courses with very large term_id...")
    result = sync_service.sync_courses(term_id=999999999)
    logger.info(f"Result: {result}")

    # Test with negative term_id
    logger.info("Testing sync_courses with negative term_id...")
    result = sync_service.sync_courses(term_id=-999)
    logger.info(f"Result: {result}")

    logger.info("Edge case tests completed")


def test_concurrent_operations(sync_service):
    """Test how the application handles concurrent operations."""
    logger.info("Testing concurrent operations...")

    # This is a simplified test that doesn't actually run concurrent operations,
    # but it simulates the effect by calling operations in quick succession

    # First, sync courses to get some course IDs
    course_ids = sync_service.sync_courses()

    if not course_ids:
        logger.warning("No courses found, skipping concurrent operations test")
        return

    # Now call sync operations in quick succession
    logger.info("Calling sync operations in quick succession...")

    start_time = time.time()

    # Call sync_assignments
    sync_service.sync_assignments(course_ids)

    # Call sync_modules immediately after
    sync_service.sync_modules(course_ids)

    # Call sync_announcements immediately after
    sync_service.sync_announcements(course_ids)

    end_time = time.time()

    logger.info(f"Completed all sync operations in {end_time - start_time:.2f} seconds")
    logger.info("Concurrent operations test completed")


def main():
    """Main function to run the error handling test script."""
    parser = argparse.ArgumentParser(description="Test error handling and edge cases")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting error handling and edge case tests")

    # Setup test environment
    sync_service, db_manager, api_adapter = setup_test_environment()

    # Run tests
    test_api_error_handling(sync_service, api_adapter)
    test_database_error_handling(sync_service, db_manager)
    test_edge_cases(sync_service, db_manager)
    test_concurrent_operations(sync_service)

    logger.info("Error handling and edge case tests completed")


if __name__ == "__main__":
    main()
