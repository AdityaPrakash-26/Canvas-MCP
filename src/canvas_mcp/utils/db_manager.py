"""
Database Management Utilities

This module provides utilities for managing database connections and operations,
implementing best practices for SQLite connections across the Canvas MCP project.
"""

import logging
import sqlite3
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

# Configure logging
logger = logging.getLogger(__name__)

# Project paths
PROJECT_DIR = Path(__file__).parent.parent.parent.parent
DB_DIR = PROJECT_DIR / "data"
DEFAULT_DB_PATH = DB_DIR / "canvas_mcp.db"

# Type variable for return type of decorated functions
T = TypeVar("T")


class DatabaseManager:
    """
    Database manager for handling connections and common operations.
    Uses a context manager pattern for safer database interactions.
    """

    def __init__(self, db_path: str | Path = None):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database (defaults to project's database)
        """
        self.db_path = str(db_path or DEFAULT_DB_PATH)

    def connect(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        Connect to the SQLite database.

        Returns:
            Tuple of (connection, cursor)
        """
        # Connect to the database with a timeout
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Enable WAL mode - Must be done early
        try:
            # Check current mode first
            current_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
            if current_mode.lower() != 'wal':
                cursor.execute("PRAGMA journal_mode = WAL")
                # Verify change
                new_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
                if new_mode.lower() == 'wal':
                    logger.info("SQLite WAL mode enabled.")
                else:
                    logger.warning(f"Attempted to enable WAL mode, but mode is still {new_mode}.")
            else:
                logger.debug("SQLite WAL mode already enabled.")
        except Exception as e:
            logger.warning(f"Could not enable/verify WAL mode: {e}") # Log but don't fail

        # Enable foreign keys directly with PRAGMA (URI parameter doesn't work reliably)
        cursor.execute("PRAGMA foreign_keys = ON")

        # Verify that foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        if not foreign_keys_enabled:
            logger.error(
                "Failed to enable foreign key constraints. Database integrity may be compromised."
            )

        return conn, cursor

    def with_connection(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator for functions that need a database connection.
        Automatically handles connection creation, commits, and cleanup.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            conn, cursor = self.connect()
            try:
                result = func(conn, cursor, *args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error in {func.__name__}: {e}")
                raise
            finally:
                conn.close()

        return wrapper

    def execute_query(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Execute a SQL query and return all results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of rows
        """
        conn, cursor = self.connect()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute a SQL update/insert and return the number of affected rows.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Number of affected rows
        """
        conn, cursor = self.connect()
        try:
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing update: {e}")
            raise
        finally:
            conn.close()

    def get_by_id(self, table: str, id_value: int) -> sqlite3.Row | None:
        """
        Get a record by ID.

        Args:
            table: Table name
            id_value: ID value

        Returns:
            Row or None if not found
        """
        conn, cursor = self.connect()
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (id_value,))
            return cursor.fetchone()
        finally:
            conn.close()

    def row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any]:
        """
        Convert a SQLite Row to a dictionary.

        Args:
            row: SQLite Row object or None

        Returns:
            Dictionary representation of the row
        """
        if row is None:
            return {}
        return {key: row[key] for key in row.keys()}

    def rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        """
        Convert a list of SQLite Rows to a list of dictionaries.

        Args:
            rows: List of SQLite Row objects

        Returns:
            List of dictionaries
        """
        return [self.row_to_dict(row) for row in rows]


# Import necessary types
import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from canvas_mcp.models import BaseModel
    from canvas_mcp.sync.service import SyncService


async def run_db_persist_in_thread(
    db_manager: "DatabaseManager",
    persist_func: Callable[[sqlite3.Connection, sqlite3.Cursor, "SyncService", list["BaseModel"]], int],
    sync_service_instance: "SyncService",
    items_to_persist: list["BaseModel"],
) -> int:
    """Runs a synchronous DB persistence function in a thread."""
    if not items_to_persist:
        return 0

    def db_task_wrapper():
        conn, cursor = db_manager.connect()
        try:
            # Pass conn, cursor, sync_service, and items to the actual persist function
            count = persist_func(conn, cursor, sync_service_instance, items_to_persist)
            conn.commit()
            logger.debug(f"Committed {count} items via {persist_func.__name__}")
            return count
        except Exception as e:
            logger.error(f"Database error in {persist_func.__name__}, rolling back: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception as rb_e:
                logger.error(f"Rollback failed: {rb_e}")
            raise # Re-raise the original exception to signal failure
        finally:
            conn.close()

    try:
        # Execute the wrapper in a thread
        result = await asyncio.to_thread(db_task_wrapper)
        return result
    except Exception as e:
        # Log error propagated from the thread
        logger.error(f"Persistence task {persist_func.__name__} failed: {e}")
        return 0 # Or re-raise depending on desired sync_all behavior
