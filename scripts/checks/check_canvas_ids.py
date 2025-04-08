#!/usr/bin/env python3
"""
Script to check Canvas course IDs and their formats.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
import src.canvas_mcp.config as config
from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter


def main():
    """Main function to check Canvas course IDs."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)
        api_adapter = CanvasApiAdapter(canvas_api_client)

        # Get current user
        user = api_adapter.get_current_user_raw()
        if not user:
            print("Failed to get current user")
            return

        print(f"User ID: {user.id}")

        # Get courses
        courses = api_adapter.get_courses_raw(user)
        if not courses:
            print("No courses found")
            return

        print(f"\nFound {len(courses)} courses:")
        for course in courses:
            course_id = getattr(course, "id", "Unknown")
            course_name = getattr(course, "name", "Unknown")
            course_code = getattr(course, "course_code", "Unknown")
            enrollment_state = "Unknown"

            # Try to get enrollment state
            if hasattr(course, "enrollments") and course.enrollments:
                enrollment_state = course.enrollments[0].get(
                    "enrollment_state", "Unknown"
                )

            # Get term info if available
            term_id = getattr(course, "enrollment_term_id", "Unknown")

            print(f"- ID: {course_id}")
            print(f"  Name: {course_name}")
            print(f"  Code: {course_code}")
            print(f"  Enrollment State: {enrollment_state}")
            print(f"  Term ID: {term_id}")
            print()

        # Check database for course IDs
        print("\nChecking database for course IDs:")
        import sqlite3

        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, canvas_course_id, course_code, course_name FROM courses"
        )
        db_courses = cursor.fetchall()

        print(f"Found {len(db_courses)} courses in database:")
        for course in db_courses:
            print(f"- DB ID: {course['id']}")
            print(f"  Canvas ID: {course['canvas_course_id']}")
            print(f"  Code: {course['course_code']}")
            print(f"  Name: {course['course_name']}")
            print()

        conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
