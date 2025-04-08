#!/usr/bin/env python3
"""
Script to clean up the Canvas MCP database by removing orphaned assignments.
"""

import sqlite3
from pathlib import Path


def cleanup_database():
    """Remove assignments associated with non-existent courses."""
    # Connect to the database
    db_path = Path("data/canvas_mcp.db")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find assignments with non-existent course IDs
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
    else:
        print("No orphaned assignments found.")

    # Find duplicate canvas_assignment_ids
    cursor.execute("""
    SELECT canvas_assignment_id, COUNT(*) as count
    FROM assignments
    GROUP BY canvas_assignment_id
    HAVING count > 1
    """)

    duplicate_ids = cursor.fetchall()

    if duplicate_ids:
        print(f"\nFound {len(duplicate_ids)} canvas_assignment_ids with duplicates:")
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

            # Keep only one assignment per canvas_assignment_id (the one with the lowest ID)
            cursor.execute(
                """
            DELETE FROM assignments
            WHERE canvas_assignment_id = ?
            AND id NOT IN (
                SELECT MIN(id)
                FROM assignments
                WHERE canvas_assignment_id = ?
            )
            """,
                (canvas_id, canvas_id),
            )

            print(f"    Deleted {cursor.rowcount} duplicate assignments.")
    else:
        print("No duplicate canvas_assignment_ids found.")

    # Commit changes
    conn.commit()
    conn.close()

    print("\nDatabase cleanup complete.")


if __name__ == "__main__":
    cleanup_database()
