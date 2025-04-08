#!/usr/bin/env python
"""
Test script to verify term filtering in course sync.

This script cleans the database, syncs courses with term filtering,
and checks if only current term courses are included.
"""

import os
import sqlite3
import sys

# Add the src directory to the path so we can import canvas_mcp modules
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import canvas_mcp.config as config
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager


def main():
    """Main function to verify term filtering."""
    print("Initializing Canvas client...")
    db_manager = DatabaseManager(config.DB_PATH)
    canvas_client = CanvasClient(db_manager, config.API_KEY, config.API_URL)

    if canvas_client.canvas is None:
        print("Error: Canvas client not initialized properly.")
        return

    # Get current user
    user = canvas_client.canvas.get_current_user()
    print(f"Current user: {user.name} (ID: {user.id})")

    # Clean the database
    print("\nCleaning the database...")
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Delete all courses and related data
    cursor.execute("DELETE FROM courses")
    conn.commit()
    conn.close()

    print("Database cleaned.")

    # Get all active courses directly from Canvas API
    print("\nFetching all active courses directly from Canvas API...")
    all_active_courses = list(user.get_courses(enrollment_state="active"))
    print(f"Found {len(all_active_courses)} active courses")

    # Get term IDs
    term_ids = set()
    for course in all_active_courses:
        term_id = getattr(course, "enrollment_term_id", None)
        if term_id:
            term_ids.add(term_id)

    print(f"Found {len(term_ids)} different term IDs: {term_ids}")

    # Find the most recent term
    if term_ids:
        max_term_id = max(term_ids)
        print(f"Most recent term ID: {max_term_id}")

        # Count courses in the most recent term
        current_term_courses = [
            course
            for course in all_active_courses
            if getattr(course, "enrollment_term_id", None) == max_term_id
        ]
        print(f"Found {len(current_term_courses)} courses in the most recent term")

    # Sync courses using our modified method (should now default to term filtering)
    print("\nSyncing courses using our modified method...")
    course_ids = canvas_client.sync_courses()
    print(f"Synced {len(course_ids)} courses")

    # Get course details from database
    print("\nCourse details from database:")
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, canvas_course_id, course_name FROM courses")
    db_courses = cursor.fetchall()

    for course in db_courses:
        print(f"- {course['course_name']} (ID: {course['canvas_course_id']})")

    conn.close()

    # Check if the numbers match with current term courses
    if len(current_term_courses) == len(course_ids):
        print(
            "\nSuccess! The number of synced courses matches the number of current term courses."
        )
    else:
        print(
            "\nWarning: The number of synced courses doesn't match the number of current term courses."
        )
        print(
            f"Current term courses: {len(current_term_courses)}, Synced courses: {len(course_ids)}"
        )


if __name__ == "__main__":
    main()
