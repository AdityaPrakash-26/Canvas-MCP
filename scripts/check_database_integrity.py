#!/usr/bin/env python3
"""
Script to check and fix database integrity issues in Canvas MCP.

This script performs various checks on the database to identify and fix
common integrity issues, such as:
1. Orphaned assignments (associated with non-existent courses)
2. Duplicate canvas_assignment_ids across different courses
3. Other foreign key constraint violations

Usage:
    python check_database_integrity.py [--fix]

Options:
    --fix    Fix identified issues (default is to only report them)
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.canvas_mcp.utils.db_manager import DatabaseManager
import src.canvas_mcp.config as config


def check_orphaned_assignments(conn, cursor, fix=False):
    """Check for assignments associated with non-existent courses."""
    print("\n=== Checking for orphaned assignments ===")

    cursor.execute("""
    SELECT a.id, a.course_id, a.title, a.canvas_assignment_id
    FROM assignments a
    LEFT JOIN courses c ON a.course_id = c.id
    WHERE c.id IS NULL
    """)

    orphaned_assignments = cursor.fetchall()

    if orphaned_assignments:
        print(f"Found {len(orphaned_assignments)} orphaned assignments:")
        for assignment in orphaned_assignments:
            print(
                f"  ID: {assignment['id']}, Course ID: {assignment['course_id']}, Title: {assignment['title']}"
            )

        if fix:
            # Delete orphaned assignments
            cursor.execute("""
            DELETE FROM assignments
            WHERE id IN (
                SELECT a.id
                FROM assignments a
                LEFT JOIN courses c ON a.course_id = c.id
                WHERE c.id IS NULL
            )
            """)

            print(f"Deleted {cursor.rowcount} orphaned assignments.")
            conn.commit()
        else:
            print("Use --fix to delete these orphaned assignments.")
    else:
        print("No orphaned assignments found.")


def check_duplicate_canvas_assignment_ids(conn, cursor, fix=False):
    """Check for duplicate canvas_assignment_ids across different courses."""
    print("\n=== Checking for duplicate canvas_assignment_ids ===")

    cursor.execute("""
    SELECT canvas_assignment_id, COUNT(*) as count
    FROM assignments
    GROUP BY canvas_assignment_id
    HAVING count > 1
    """)

    duplicate_ids = cursor.fetchall()

    if duplicate_ids:
        print(f"Found {len(duplicate_ids)} canvas_assignment_ids with duplicates:")
        for duplicate in duplicate_ids:
            canvas_id = duplicate["canvas_assignment_id"]

            # Get details of the duplicates
            cursor.execute(
                """
            SELECT id, course_id, title
            FROM assignments
            WHERE canvas_assignment_id = ?
            """,
                (canvas_id,),
            )

            duplicates = cursor.fetchall()
            print(f"  Canvas ID: {canvas_id}")
            for dup in duplicates:
                print(
                    f"    Assignment ID: {dup['id']}, Course ID: {dup['course_id']}, Title: {dup['title']}"
                )

            if fix:
                # Generate unique IDs for duplicates by appending course_id
                for dup in duplicates[1:]:  # Skip the first one
                    new_canvas_id = int(f"{canvas_id}{dup['course_id']}")
                    cursor.execute(
                        """
                    UPDATE assignments
                    SET canvas_assignment_id = ?
                    WHERE id = ?
                    """,
                        (new_canvas_id, dup["id"]),
                    )

                    print(
                        f"    Updated assignment ID {dup['id']} with new canvas_assignment_id: {new_canvas_id}"
                    )

                conn.commit()
            else:
                print(
                    "    Use --fix to generate unique canvas_assignment_ids for these duplicates."
                )
    else:
        print("No duplicate canvas_assignment_ids found.")


def check_foreign_key_constraints(conn, cursor, fix=False):
    """Check if foreign key constraints are enabled and working."""
    print("\n=== Checking foreign key constraints ===")

    # Check if foreign keys are enabled
    cursor.execute("PRAGMA foreign_keys")
    foreign_keys_enabled = cursor.fetchone()[0]

    if foreign_keys_enabled:
        print("Foreign key constraints are enabled.")
    else:
        print("WARNING: Foreign key constraints are NOT enabled!")
        print("This can lead to data integrity issues.")
        print("Foreign keys should be enabled in the DatabaseManager.connect() method.")

    # Check for any existing foreign key violations
    tables = [
        "assignments",
        "modules",
        "module_items",
        "calendar_events",
        "user_courses",
        "discussions",
        "announcements",
        "grades",
        "lectures",
        "files",
        "syllabi",
    ]

    violations_found = False
    total_fixed = 0

    for table in tables:
        # Get foreign key definitions for this table
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()

        for fk in foreign_keys:
            parent_table = fk["table"]
            from_col = fk["from"]
            to_col = fk["to"]

            # Check for violations
            cursor.execute(f"""
            SELECT t.{from_col}, COUNT(*) as count
            FROM {table} t
            LEFT JOIN {parent_table} p ON t.{from_col} = p.{to_col}
            WHERE t.{from_col} IS NOT NULL AND p.{to_col} IS NULL
            GROUP BY t.{from_col}
            """)

            violations = cursor.fetchall()

            if violations:
                violations_found = True
                print(
                    f"Found foreign key violations in {table}.{from_col} -> {parent_table}.{to_col}:"
                )
                for violation in violations:
                    print(f"  {from_col} = {violation[0]}: {violation[1]} records")

                if fix:
                    # Get the IDs of the violating records
                    cursor.execute(
                        f"""
                    SELECT id FROM {table}
                    WHERE {from_col} = ? AND {from_col} IS NOT NULL
                    """,
                        (violation[0],),
                    )

                    violating_ids = [row["id"] for row in cursor.fetchall()]

                    # Delete the violating records
                    cursor.execute(
                        f"""
                    DELETE FROM {table}
                    WHERE id IN ({','.join(['?'] * len(violating_ids))})
                    """,
                        violating_ids,
                    )

                    fixed_count = cursor.rowcount
                    total_fixed += fixed_count
                    print(
                        f"  Fixed: Deleted {fixed_count} records from {table} with {from_col} = {violation[0]}"
                    )

    if fix and total_fixed > 0:
        conn.commit()
        print(f"Fixed a total of {total_fixed} foreign key constraint violations.")
    elif not violations_found:
        print("No foreign key constraint violations found.")
    elif not fix:
        print("Use --fix to delete records with foreign key violations.")


def main():
    """Main function to check and fix database integrity issues."""
    parser = argparse.ArgumentParser(
        description="Check and fix database integrity issues"
    )
    parser.add_argument("--fix", action="store_true", help="Fix identified issues")
    args = parser.parse_args()

    # Use the database path from config
    db_path = config.DB_PATH
    print(f"Checking database integrity for: {db_path}")

    # Connect to the database
    db_manager = DatabaseManager(db_path)
    conn, cursor = db_manager.connect()

    try:
        # Run the checks
        check_foreign_key_constraints(conn, cursor, args.fix)
        check_orphaned_assignments(conn, cursor, args.fix)
        check_duplicate_canvas_assignment_ids(conn, cursor, args.fix)

        print("\nDatabase integrity check completed.")
        if not args.fix:
            print("Run with --fix to automatically fix identified issues.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
