#!/usr/bin/env python3
"""
Database initialization script for Canvas MCP tests.
This script uses the main database creation logic from the source code
to ensure the test database schema is always up-to-date.
"""

import os
from pathlib import Path

# Import the actual database creation function from the source code
from canvas_mcp.init_db import create_database as create_src_database


def create_database(db_path: str) -> None:
    """
    Create a new SQLite database for testing using the main source schema.

    Args:
        db_path: Path to the SQLite database file
    """
    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Call the imported function to create the database with the correct schema
    create_src_database(db_path)

    print(f"Test database initialized at {db_path} using source schema.")


# The following functions are removed as they define an outdated schema:
# - create_tables(cursor: sqlite3.Cursor) -> None:
# - create_views(cursor: sqlite3.Cursor) -> None:
# ... (rest of the old create_tables and create_views code deleted) ...


def main() -> None:
    """Create database in the project directory for testing."""
    project_dir = Path(__file__).parent
    # Typically, tests might use an in-memory DB or a dedicated test file
    # Adjust path as needed for your testing strategy
    db_path = project_dir / "data" / "test_canvas_mcp.db"
    create_database(str(db_path))


if __name__ == "__main__":
    main()
