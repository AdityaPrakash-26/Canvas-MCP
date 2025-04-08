#!/usr/bin/env python
"""
Test script to verify the course filtering fix.

This script syncs courses and checks if dropped courses are filtered out.
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

    # Get active courses directly from Canvas API
    print("\nFetching active courses directly from Canvas API...")
    active_courses = list(user.get_courses(enrollment_state="active"))
    print(f"Found {len(active_courses)} active courses")

    # Sync courses using our modified method
    print("\nSyncing courses using our modified method...")
    course_ids = canvas_client.sync_courses()
    print(f"Synced {len(course_ids)} courses")

    # Check if the numbers match
    if len(active_courses) == len(course_ids):
        print(
            "\nSuccess! The number of synced courses matches the number of active courses."
        )
    else:
        print(
            "\nWarning: The number of synced courses doesn't match the number of active courses."
        )
        print(
            f"Active courses: {len(active_courses)}, Synced courses: {len(course_ids)}"
        )

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

    # Check if any visualization course exists
    print("\nChecking for visualization courses...")
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, canvas_course_id, course_name FROM courses WHERE course_name LIKE '%visualization%'"
    )
    vis_courses = cursor.fetchall()

    if vis_courses:
        print("Found visualization courses:")
        for course in vis_courses:
            print(f"- {course['course_name']} (ID: {course['canvas_course_id']})")
    else:
        print("No visualization courses found in the database.")

    conn.close()


if __name__ == "__main__":
    main()
