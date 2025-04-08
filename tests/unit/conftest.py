"""
Configuration file for pytest unit tests.

This file contains fixtures for unit testing Canvas MCP with fake dependencies.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Generator

import pytest

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager
from tests.fakes.fake_canvasapi import patch_canvasapi

# Apply the patch before importing any code that uses canvasapi
patch_canvasapi()


@pytest.fixture(scope="session")
def test_db_path() -> Path:
    """Return the path to the test database."""
    return Path("tests/test_data/test_unit.db")


@pytest.fixture(scope="session")
def ensure_test_db(test_db_path: Path) -> None:
    """Ensure the test database exists."""
    # Ensure test data directory exists
    os.makedirs(test_db_path.parent, exist_ok=True)
    
    # Only create the database if it doesn't exist
    if not test_db_path.exists():
        print(f"Test database not found, will create: {test_db_path}")
        # Initialize the test database using the correct path
        from init_db import create_database
        create_database(str(test_db_path))
        print("Test database initialized.")
    else:
        print(f"Using existing test database: {test_db_path}")


@pytest.fixture(scope="session")
def db_manager(ensure_test_db: None, test_db_path: Path) -> DatabaseManager:
    """Return a database manager for the test database."""
    return DatabaseManager(test_db_path)


@pytest.fixture(scope="session")
def canvas_client(db_manager: DatabaseManager) -> CanvasClient:
    """Return a Canvas client with the fake Canvas API."""
    return CanvasClient(db_manager, "fake_api_key")


@pytest.fixture(scope="function")
def db_connection(
    db_manager: DatabaseManager,
) -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    """Return a connection and cursor for the test database."""
    conn, cursor = db_manager.connect()
    try:
        yield conn, cursor
    finally:
        conn.close()


@pytest.fixture(scope="session")
def target_course_id() -> int:
    """Return the ID of the target course for testing."""
    return 65920000000146127


@pytest.fixture(scope="function")
def synced_course_ids(canvas_client: CanvasClient) -> list[int]:
    """Return a list of course IDs after syncing courses."""
    return canvas_client.sync_courses()


@pytest.fixture(scope="function")
def synced_assignments(canvas_client: CanvasClient, synced_course_ids: list[int]) -> int:
    """Return the number of assignments after syncing assignments."""
    return canvas_client.sync_assignments(synced_course_ids)


@pytest.fixture(scope="function")
def synced_modules(canvas_client: CanvasClient, synced_course_ids: list[int]) -> int:
    """Return the number of modules after syncing modules."""
    return canvas_client.sync_modules(synced_course_ids)


@pytest.fixture(scope="function")
def synced_announcements(canvas_client: CanvasClient, synced_course_ids: list[int]) -> int:
    """Return the number of announcements after syncing announcements."""
    return canvas_client.sync_announcements(synced_course_ids)


@pytest.fixture(scope="function")
def clean_db(db_manager: DatabaseManager) -> None:
    """Clean the database before tests that need a fresh state."""
    conn, cursor = db_manager.connect()
    try:
        # Delete all data from tables
        tables = [
            "courses",
            "assignments",
            "modules",
            "module_items",
            "announcements",
            "files",
        ]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()
