"""
Configuration file for pytest.

This file contains fixtures and configuration for the Canvas MCP tests.
"""

import os
import shutil
import sqlite3
import sys
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from canvasapi import Canvas

# Add the project root directory to the Python path

# Test database paths
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DB_PATH = TEST_DATA_DIR / "test_canvas_mcp.db"
CACHED_DB_PATH = TEST_DATA_DIR / "cached_canvas_mcp.db"
CACHE_METADATA_PATH = TEST_DATA_DIR / "cache_metadata.txt"

# Cache validity period (in days)
CACHE_VALIDITY_DAYS = 7

# Set environment variable to use test database BEFORE importing server components
os.environ["CANVAS_MCP_TEST_DB"] = str(TEST_DB_PATH)
print(f"Test environment variable CANVAS_MCP_TEST_DB set to: {TEST_DB_PATH}")

# Import database creation function

sys.path.append(str(Path(__file__).parent.parent))
from tests.init_db import create_database

# Import test client
from tests.integration.test_client import CanvasMCPTestClient

# Import database utilities
from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.sync import SyncService
from canvas_mcp.utils.db_manager import DatabaseManager

# CanvasClient import has been removed as part of the refactoring


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """Return the path to the test database."""
    return TEST_DB_PATH


@pytest.fixture(scope="session")
def ensure_test_db(test_db_path: Path) -> None:
    """Ensure the test database exists, using a cached version if available and valid."""
    # Ensure test data directory exists
    os.makedirs(test_db_path.parent, exist_ok=True)

    # Check if we have a valid cached database
    cache_is_valid = False
    if CACHED_DB_PATH.exists() and CACHE_METADATA_PATH.exists():
        try:
            # Read the cache timestamp
            with open(CACHE_METADATA_PATH) as f:
                cache_timestamp_str = f.read().strip()
                cache_timestamp = datetime.fromisoformat(cache_timestamp_str)

            # Check if the cache is still valid
            cache_age = datetime.now() - cache_timestamp
            if cache_age < timedelta(days=CACHE_VALIDITY_DAYS):
                cache_is_valid = True
                print(
                    f"Found valid cached database (age: {cache_age.days} days, {cache_age.seconds // 3600} hours)"
                )
            else:
                print(
                    f"Cached database is too old ({cache_age.days} days, {cache_age.seconds // 3600} hours)"
                )
        except (ValueError, OSError) as e:
            print(f"Error reading cache metadata: {e}")

    # Use the cached database if it's valid
    if cache_is_valid and not test_db_path.exists():
        print(f"Copying cached database to: {test_db_path}")
        shutil.copy2(CACHED_DB_PATH, test_db_path)
        print("Using cached database for tests.")
    elif not test_db_path.exists():
        print(f"Test database not found, will create: {test_db_path}")
        # Initialize the test database using the correct path
        print(f"Initializing test database at: {test_db_path}")
        create_database(str(test_db_path))
        print("Test database initialized.")
    else:
        print(f"Using existing test database: {test_db_path}")


@pytest.fixture(scope="session")
def db_manager(
    ensure_test_db: None, test_db_path: Path
) -> DatabaseManager:  # ensure_test_db is used as a dependency
    """Return a database manager for the test database."""
    return DatabaseManager(test_db_path)


@pytest.fixture(scope="session")
def api_adapter(db_manager: DatabaseManager) -> CanvasApiAdapter:
    """Return a Canvas API adapter for testing."""
    # Ensure Canvas API key is available
    api_key = os.environ.get("CANVAS_API_KEY")
    api_url = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

    if not api_key:
        pytest.fail(
            "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests"
        )

    # Initialize Canvas API client
    try:
        canvas_api_client = Canvas(api_url, api_key)
        return CanvasApiAdapter(canvas_api_client)
    except Exception as e:
        print(f"Error initializing Canvas API adapter: {e}")
        return CanvasApiAdapter(None)


@pytest.fixture(scope="session")
def sync_service(
    db_manager: DatabaseManager, api_adapter: CanvasApiAdapter
) -> SyncService:
    """Return a sync service for testing."""
    return SyncService(db_manager, api_adapter)


# Canvas client fixture has been removed as part of the refactoring


@pytest.fixture(scope="session")
def test_client(
    ensure_test_db: None, test_db_path: Path
) -> CanvasMCPTestClient:  # ensure_test_db is used as a dependency
    """Return a test client for the Canvas MCP tools."""
    return CanvasMCPTestClient(test_db_path)


@pytest.fixture(scope="session")
def test_context(test_client: CanvasMCPTestClient) -> dict[str, Any]:
    """Return a test context for the MCP tools."""
    # Just return the context from the test client
    return test_client.context


@pytest.fixture(scope="session")
def db_connection(
    test_client: CanvasMCPTestClient,
) -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    """Return a connection and cursor for the test database."""
    conn, cursor = test_client.db_manager.connect()
    try:
        yield conn, cursor
    finally:
        conn.close()


# Target course information
TARGET_COURSE_CODE = "SP25_CS_540_1"
TARGET_CANVAS_COURSE_ID = 65920000000146127


@pytest.fixture(scope="session")
def ensure_course_data(test_client, db_connection) -> int:
    """Ensure the target course data exists in the database.

    This fixture will check if the target course exists in the database.
    If not, it will run a sync operation to populate the database.

    Returns:
        The internal ID of the target course
    """
    _, cursor = db_connection

    # Check if the target course exists
    cursor.execute(
        "SELECT id FROM courses WHERE course_code = ? OR canvas_course_id = ?",
        (TARGET_COURSE_CODE, TARGET_CANVAS_COURSE_ID),
    )
    result = cursor.fetchone()

    if result:
        course_id = result["id"]
        print(f"Found target course with internal ID: {course_id}")
        return course_id

    # Course not found, run sync
    print("Target course not found in database, running sync operation...")
    sync_result = test_client.sync_canvas_data()
    print(f"Sync completed: {sync_result}")

    # Check again for the course
    cursor.execute(
        "SELECT id FROM courses WHERE course_code = ? OR canvas_course_id = ?",
        (TARGET_COURSE_CODE, TARGET_CANVAS_COURSE_ID),
    )
    result = cursor.fetchone()

    if not result:
        pytest.fail(f"Failed to find target course {TARGET_COURSE_CODE} after sync")

    course_id = result["id"]
    print(f"Found target course with internal ID: {course_id}")
    return course_id


@pytest.fixture(scope="session")
def target_course_info(ensure_course_data) -> dict[str, Any]:
    """Return information about the target course."""
    return {
        "code": TARGET_COURSE_CODE,
        "canvas_id": TARGET_CANVAS_COURSE_ID,
        "internal_id": ensure_course_data,  # Already populated by ensure_course_data fixture
    }


# This fixture is no longer needed since target_course_info is now fully populated
