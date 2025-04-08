"""
Configuration file for pytest unit tests.

This file contains fixtures for unit testing Canvas MCP with fake dependencies.
"""

import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from tests.fakes.fake_canvasapi import patch_canvasapi

from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.sync import SyncService
from canvas_mcp.utils.db_manager import DatabaseManager

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
def api_adapter() -> CanvasApiAdapter:
    """Return a Canvas API adapter with the fake Canvas API."""
    from canvasapi import Canvas

    canvas = Canvas("https://fake.instructure.com", "fake_api_key")
    return CanvasApiAdapter(canvas)


@pytest.fixture(scope="session")
def sync_service(
    db_manager: DatabaseManager, api_adapter: CanvasApiAdapter
) -> SyncService:
    """Return a sync service with the fake Canvas API."""
    return SyncService(db_manager, api_adapter)


# Canvas client fixture has been removed as part of the refactoring


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
def synced_course_ids(sync_service: SyncService) -> list[int]:
    """Return a list of course IDs after syncing courses using SyncService."""
    return sync_service.sync_courses()


@pytest.fixture(scope="function")
def synced_assignments(sync_service: SyncService, synced_course_ids: list[int]) -> int:
    """Return the number of assignments after syncing assignments."""
    return sync_service.sync_assignments(synced_course_ids)


@pytest.fixture(scope="function")
def synced_modules(sync_service: SyncService, synced_course_ids: list[int]) -> int:
    """Return the number of modules after syncing modules."""
    return sync_service.sync_modules(synced_course_ids)


@pytest.fixture(scope="function")
def synced_announcements(
    sync_service: SyncService, synced_course_ids: list[int]
) -> int:
    """Return the number of announcements after syncing announcements."""
    return sync_service.sync_announcements(synced_course_ids)


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
