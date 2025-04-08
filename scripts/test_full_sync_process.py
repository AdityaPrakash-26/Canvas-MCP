#!/usr/bin/env python3
"""
Comprehensive test script for the full synchronization process.

This script performs a complete synchronization with detailed logging at each step,
verifying data integrity and checking for potential issues.

Usage:
    python scripts/test_full_sync_process.py [--verbose] [--term_id TERM_ID]

Options:
    --verbose       Enable verbose logging
    --term_id       Specify a term ID to sync (default: -1, most recent term)
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.config import get_canvas_api_key, get_canvas_api_url
from src.canvas_mcp.sync.service import SyncService
from src.canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"sync_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger("sync_test")


def setup_test_environment():
    """Set up the test environment with API adapter and database manager."""
    # Get API credentials
    api_key = get_canvas_api_key()
    api_url = get_canvas_api_url()

    if not api_key or not api_url:
        logger.error(
            "Canvas API credentials not found. Please set CANVAS_API_KEY and CANVAS_API_URL environment variables."
        )
        sys.exit(1)

    # Create a test database path
    test_db_path = Path("data/test_sync.db")
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


def test_api_connectivity(api_adapter):
    """Test connectivity to the Canvas API."""
    logger.info("Testing Canvas API connectivity...")

    if not api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return False

    user = api_adapter.get_current_user_raw()
    if not user:
        logger.error("Failed to get current user from Canvas API")
        return False

    logger.info(
        f"Successfully connected to Canvas API as user: {user.name} (ID: {user.id})"
    )
    return True


def test_database_setup(db_manager):
    """Test database setup and schema."""
    logger.info("Testing database setup...")

    try:
        conn, cursor = db_manager.connect()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = [
            "courses",
            "assignments",
            "modules",
            "module_items",
            "announcements",
            "syllabi",
            "user_courses",
        ]

        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            logger.error(f"Missing tables in database: {missing_tables}")
            return False

        logger.info(f"Database schema verified. Found tables: {', '.join(tables)}")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error testing database setup: {e}")
        return False


def perform_sync_with_timing(sync_service, term_id):
    """Perform synchronization with timing for each step."""
    logger.info(f"Starting full synchronization process with term_id={term_id}...")

    # Time the entire sync process
    start_time = time.time()

    # Sync courses
    logger.info("Syncing courses...")
    course_start = time.time()
    course_ids = sync_service.sync_courses(term_id=term_id)
    course_time = time.time() - course_start
    logger.info(f"Synced {len(course_ids)} courses in {course_time:.2f} seconds")

    if not course_ids:
        logger.warning(
            "No courses were synced. Check term_id parameter and Canvas access."
        )
        return None

    # Sync assignments
    logger.info("Syncing assignments...")
    assignment_start = time.time()
    assignment_count = sync_service.sync_assignments(course_ids)
    assignment_time = time.time() - assignment_start
    logger.info(
        f"Synced {assignment_count} assignments in {assignment_time:.2f} seconds"
    )

    # Sync modules
    logger.info("Syncing modules...")
    module_start = time.time()
    module_count = sync_service.sync_modules(course_ids)
    module_time = time.time() - module_start
    logger.info(f"Synced {module_count} modules in {module_time:.2f} seconds")

    # Sync announcements
    logger.info("Syncing announcements...")
    announcement_start = time.time()
    announcement_count = sync_service.sync_announcements(course_ids)
    announcement_time = time.time() - announcement_start
    logger.info(
        f"Synced {announcement_count} announcements in {announcement_time:.2f} seconds"
    )

    # Calculate total time
    total_time = time.time() - start_time
    logger.info(f"Full synchronization completed in {total_time:.2f} seconds")

    return {
        "courses": len(course_ids),
        "assignments": assignment_count,
        "modules": module_count,
        "announcements": announcement_count,
        "timing": {
            "courses": course_time,
            "assignments": assignment_time,
            "modules": module_time,
            "announcements": announcement_time,
            "total": total_time,
        },
    }


def verify_data_integrity(db_manager, sync_results):
    """Verify data integrity after synchronization."""
    logger.info("Verifying data integrity...")

    try:
        conn, cursor = db_manager.connect()

        # Check course count
        cursor.execute("SELECT COUNT(*) as count FROM courses")
        course_count = cursor.fetchone()["count"]
        if course_count != sync_results["courses"]:
            logger.warning(
                f"Course count mismatch: {course_count} in DB vs {sync_results['courses']} reported"
            )

        # Check assignment count
        cursor.execute("SELECT COUNT(*) as count FROM assignments")
        assignment_count = cursor.fetchone()["count"]
        if assignment_count != sync_results["assignments"]:
            logger.warning(
                f"Assignment count mismatch: {assignment_count} in DB vs {sync_results['assignments']} reported"
            )

        # Check module count
        cursor.execute("SELECT COUNT(*) as count FROM modules")
        module_count = cursor.fetchone()["count"]
        if module_count != sync_results["modules"]:
            logger.warning(
                f"Module count mismatch: {module_count} in DB vs {sync_results['modules']} reported"
            )

        # Check announcement count
        cursor.execute("SELECT COUNT(*) as count FROM announcements")
        announcement_count = cursor.fetchone()["count"]
        if announcement_count != sync_results["announcements"]:
            logger.warning(
                f"Announcement count mismatch: {announcement_count} in DB vs {sync_results['announcements']} reported"
            )

        # Check for orphaned records
        cursor.execute("""
            SELECT COUNT(*) as count FROM assignments a
            LEFT JOIN courses c ON a.course_id = c.id
            WHERE c.id IS NULL
        """)
        orphaned_assignments = cursor.fetchone()["count"]
        if orphaned_assignments > 0:
            logger.error(f"Found {orphaned_assignments} orphaned assignments")

        cursor.execute("""
            SELECT COUNT(*) as count FROM modules m
            LEFT JOIN courses c ON m.course_id = c.id
            WHERE c.id IS NULL
        """)
        orphaned_modules = cursor.fetchone()["count"]
        if orphaned_modules > 0:
            logger.error(f"Found {orphaned_modules} orphaned modules")

        cursor.execute("""
            SELECT COUNT(*) as count FROM announcements a
            LEFT JOIN courses c ON a.course_id = c.id
            WHERE c.id IS NULL
        """)
        orphaned_announcements = cursor.fetchone()["count"]
        if orphaned_announcements > 0:
            logger.error(f"Found {orphaned_announcements} orphaned announcements")

        # Check for null values in critical fields
        cursor.execute(
            "SELECT COUNT(*) as count FROM courses WHERE course_code IS NULL OR name IS NULL"
        )
        null_courses = cursor.fetchone()["count"]
        if null_courses > 0:
            logger.error(f"Found {null_courses} courses with NULL critical fields")

        cursor.execute("SELECT COUNT(*) as count FROM assignments WHERE title IS NULL")
        null_assignments = cursor.fetchone()["count"]
        if null_assignments > 0:
            logger.error(f"Found {null_assignments} assignments with NULL title")

        conn.close()

        logger.info("Data integrity verification completed")
        return True
    except Exception as e:
        logger.error(f"Error verifying data integrity: {e}")
        return False


def check_edge_cases(db_manager):
    """Check for potential edge cases in the data."""
    logger.info("Checking for edge cases...")

    try:
        conn, cursor = db_manager.connect()

        # Check for very long text fields that might cause issues
        cursor.execute(
            "SELECT COUNT(*) as count FROM assignments WHERE length(description) > 10000"
        )
        long_descriptions = cursor.fetchone()["count"]
        if long_descriptions > 0:
            logger.warning(
                f"Found {long_descriptions} assignments with very long descriptions"
            )

        # Check for unusual dates
        cursor.execute(
            "SELECT COUNT(*) as count FROM assignments WHERE due_date < '2000-01-01' OR due_date > '2100-01-01'"
        )
        unusual_dates = cursor.fetchone()["count"]
        if unusual_dates > 0:
            logger.warning(f"Found {unusual_dates} assignments with unusual due dates")

        # Check for duplicate Canvas IDs
        cursor.execute("""
            SELECT canvas_assignment_id, COUNT(*) as count
            FROM assignments
            GROUP BY canvas_assignment_id
            HAVING count > 1
        """)
        duplicate_assignments = cursor.fetchall()
        if duplicate_assignments:
            logger.error(
                f"Found {len(duplicate_assignments)} duplicate assignment Canvas IDs"
            )
            for row in duplicate_assignments:
                logger.error(
                    f"  Canvas ID {row['canvas_assignment_id']} appears {row['count']} times"
                )

        conn.close()

        logger.info("Edge case checking completed")
        return True
    except Exception as e:
        logger.error(f"Error checking edge cases: {e}")
        return False


def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(
        description="Test the full synchronization process"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--term_id",
        type=int,
        default=-1,
        help="Term ID to sync (default: -1, most recent term)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting comprehensive sync test")

    # Setup test environment
    sync_service, db_manager, api_adapter = setup_test_environment()

    # Test API connectivity
    if not test_api_connectivity(api_adapter):
        logger.error("API connectivity test failed. Exiting.")
        sys.exit(1)

    # Test database setup
    if not test_database_setup(db_manager):
        logger.error("Database setup test failed. Exiting.")
        sys.exit(1)

    # Perform sync with timing
    sync_results = perform_sync_with_timing(sync_service, args.term_id)
    if not sync_results:
        logger.error("Synchronization failed. Exiting.")
        sys.exit(1)

    # Verify data integrity
    verify_data_integrity(db_manager, sync_results)

    # Check edge cases
    check_edge_cases(db_manager)

    logger.info("Comprehensive sync test completed")


if __name__ == "__main__":
    main()
