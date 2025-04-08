"""
Configuration file for pytest unit tests.

This file contains fixtures for unit testing Canvas MCP with fake dependencies.
"""

import datetime
import os
import sqlite3
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from tests.fakes.fake_canvasapi import patch_canvasapi

from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.sync import SyncService
from canvas_mcp.utils.db_manager import DatabaseManager

# Import tool registration functions
from canvas_mcp.tools.assignments import register_assignment_tools
from canvas_mcp.tools.courses import register_course_tools
from canvas_mcp.tools.modules import register_module_tools
from canvas_mcp.tools.syllabus import register_syllabus_tools
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.tools.files import register_file_tools
from canvas_mcp.tools.search import register_search_tools
from canvas_mcp.tools.calendar import register_calendar_tools
from canvas_mcp.tools.sync import register_sync_tools

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
        from tests.init_db import create_database

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
            "conversations",
            "files",
        ]
        for table in tables:
            # Check if table exists before trying to delete from it
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()


class MockMCP:
    """Mock MCP server for testing."""

    def __init__(self):
        """Initialize the mock MCP server."""
        self.tools = {}

    def tool(self):
        """Decorator for registering tools."""

        def decorator(func):
            # Store the tool function in the dictionary
            self.tools[func.__name__] = func
            # Also set as attribute for compatibility with existing tests
            setattr(self, func.__name__, func)
            return func

        return decorator

    def __getattr__(self, name):
        """Allow accessing tools via attribute for compatibility."""
        if name in self.tools:
            return self.tools[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )


@pytest.fixture(scope="function")
def mock_mcp():
    """Return a mock MCP server with all tools registered."""
    mcp = MockMCP()

    # Register all tools
    register_assignment_tools(mcp)
    register_course_tools(mcp)
    register_module_tools(mcp)
    register_syllabus_tools(mcp)
    register_announcement_tools(mcp)
    register_file_tools(mcp)
    register_search_tools(mcp)
    register_calendar_tools(mcp)
    register_sync_tools(mcp)

    return mcp


@pytest.fixture(scope="function")
def mock_context(db_manager, api_adapter, sync_service):
    """Return a mock context for testing."""
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context={
                "db_manager": db_manager,
                "api_adapter": api_adapter,
                "sync_service": sync_service,
            }
        )
    )
    return context


@pytest.fixture
def mock_datetime():
    """Mock the datetime module for consistent testing."""
    with patch("canvas_mcp.utils.formatters.datetime") as mock_dt:
        # Configure the mock to use real datetime functionality
        mock_dt.now.return_value = datetime.datetime(2025, 4, 5, 12, 0, 0)
        mock_dt.datetime = datetime.datetime
        mock_dt.timedelta = datetime.timedelta
        mock_dt.fromisoformat = datetime.datetime.fromisoformat
        mock_dt.UTC = datetime.UTC
        # Make sure comparison operators work
        mock_dt.side_effect = lambda *args, **kwargs: datetime.datetime(*args, **kwargs)
        yield mock_dt
