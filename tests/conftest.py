"""
Configuration file for pytest.

This file contains fixtures and configuration for the Canvas MCP tests.
"""

import os
import sqlite3
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test database path
TEST_DB_PATH = Path(__file__).parent / "test_data" / "test_canvas_mcp.db"

# Set environment variable to use test database BEFORE importing server components
os.environ["CANVAS_MCP_TEST_DB"] = str(TEST_DB_PATH)
print(f"Test environment variable CANVAS_MCP_TEST_DB set to: {TEST_DB_PATH}")

# Import database creation function
from init_db import create_database

# Import database utilities
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager

# Import test client
from tests.integration.test_client import CanvasMCPTestClient


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """Return the path to the test database."""
    return TEST_DB_PATH


@pytest.fixture(scope="session")
def ensure_test_db(test_db_path: Path) -> None:
    """Ensure the test database exists."""
    # Ensure test data directory exists
    os.makedirs(test_db_path.parent, exist_ok=True)

    # Only create the database if it doesn't exist
    # This allows us to reuse the database across test runs
    if not test_db_path.exists():
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
def canvas_client(db_manager: DatabaseManager) -> CanvasClient:
    """Return a Canvas client for the test database."""
    # Ensure Canvas API key is available
    api_key = os.environ.get("CANVAS_API_KEY")
    api_url = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

    if not api_key:
        pytest.fail(
            "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests"
        )

    return CanvasClient(db_manager, api_key, api_url)


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


@pytest.fixture(scope="function")
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
def target_course_info() -> dict[str, Any]:
    """Return information about the target course."""
    return {
        "code": TARGET_COURSE_CODE,
        "canvas_id": TARGET_CANVAS_COURSE_ID,
        "internal_id": None,  # Will be populated during tests
    }


@pytest.fixture(scope="function")
def find_target_course_id(
    db_connection: tuple[sqlite3.Connection, sqlite3.Cursor],
    target_course_info: dict[str, Any],
) -> int | None:
    """Find the internal ID of the target course."""
    _, cursor = db_connection

    # Try to find the target course ID
    cursor.execute(
        "SELECT id FROM courses WHERE course_code = ? OR canvas_course_id = ?",
        (
            target_course_info["code"],
            target_course_info["canvas_id"],
        ),
    )
    result = cursor.fetchone()

    if result:
        course_id = result["id"]
        # Update the target_course_info dictionary
        target_course_info["internal_id"] = course_id
        print(f"Found target course with internal ID: {course_id}")
        return course_id

    return None
