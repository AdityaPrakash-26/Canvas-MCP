#!/usr/bin/env python
"""
Verify that course filtering works correctly.

This script tests that the canvas_client correctly filters courses by:
1. Only including active courses (not dropped courses)
2. Only including courses from the most recent term
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import canvas_mcp.config as config
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager


def main():
    """Main function to verify course filtering."""
    print("Initializing Canvas client...")
    db_manager = DatabaseManager(config.DB_PATH)
    canvas_client = CanvasClient(db_manager, config.API_KEY, config.API_URL)

    if canvas_client.canvas is None:
        print("Error: Canvas client not initialized properly.")
        return

    # Get current user
    user = canvas_client.canvas.get_current_user()
    print(f"Current user: {user.name} (ID: {user.id})")

    # Get all courses directly from Canvas API
    print("\nFetching all courses directly from Canvas API...")
    all_courses = list(user.get_courses())
    print(f"Found {len(all_courses)} total courses")

    # Get active courses directly from Canvas API
    print("\nFetching active courses directly from Canvas API...")
    active_courses = list(user.get_courses(enrollment_state="active"))
    print(f"Found {len(active_courses)} active courses")

    # Get term IDs from active courses
    term_ids = set()
    for course in active_courses:
        term_id = getattr(course, "enrollment_term_id", None)
        if term_id:
            term_ids.add(term_id)

    print(f"\nFound {len(term_ids)} different term IDs: {term_ids}")

    # Find the most recent term
    if term_ids:
        max_term_id = max(term_ids)
        print(f"Most recent term ID: {max_term_id}")

        # Count courses in the most recent term
        current_term_courses = [
            course
            for course in active_courses
            if getattr(course, "enrollment_term_id", None) == max_term_id
        ]
        print(
            f"Found {len(current_term_courses)} active courses in the most recent term"
        )

    # Sync courses using our modified method
    print("\nSyncing courses using our modified method...")
    course_ids = canvas_client.sync_courses()
    print(f"Synced {len(course_ids)} courses")

    # Verify that the number of synced courses matches the number of active courses
    # in the current term
    if len(current_term_courses) == len(course_ids):
        print(
            "\nSUCCESS! The number of synced courses matches the number of active courses in the current term."
        )
    else:
        print(
            "\nWARNING: The number of synced courses doesn't match the number of active courses in the current term."
        )
        print(
            f"Active courses in current term: {len(current_term_courses)}, Synced courses: {len(course_ids)}"
        )

    # Print the synced courses
    print("\nSynced courses:")
    conn, cursor = db_manager.connect()
    cursor.execute("SELECT id, canvas_course_id, course_name FROM courses")
    db_courses = cursor.fetchall()

    for course in db_courses:
        print(f"- {course['course_name']} (ID: {course['canvas_course_id']})")

    conn.close()


if __name__ == "__main__":
    main()
