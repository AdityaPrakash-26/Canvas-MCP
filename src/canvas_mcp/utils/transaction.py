"""
Transaction Management Utilities

This module provides utilities for managing database transactions,
implementing best practices for SQLite transactions across the Canvas MCP project.
"""

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)


@contextmanager
def transaction(
    conn: sqlite3.Connection, cursor: sqlite3.Cursor
) -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    """
    Context manager for database transactions.
    Automatically handles commits and rollbacks.

    Args:
        conn: SQLite connection
        cursor: SQLite cursor

    Yields:
        The connection and cursor for use within the transaction

    Example:
        ```python
        conn, cursor = db_manager.connect()
        try:
            with transaction(conn, cursor):
                cursor.execute("INSERT INTO table (column) VALUES (?)", (value,))
                # More operations...
                # Transaction will be committed if no exceptions occur
        finally:
            conn.close()
        ```
    """
    try:
        # Begin transaction explicitly
        cursor.execute("BEGIN TRANSACTION")

        # Yield connection and cursor for use within the context
        yield conn, cursor

        # If we get here without an exception, commit the transaction
        conn.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        # If an exception occurs, roll back the transaction
        logger.error(f"Transaction failed, rolling back: {e}")
        try:
            conn.rollback()
            logger.debug("Transaction rolled back successfully")
        except Exception as rollback_error:
            logger.error(f"Error rolling back transaction: {rollback_error}")
        # Re-raise the original exception
        raise
