#!/usr/bin/env python
"""
Test script to check enrollment states in Canvas API.

This script connects to Canvas API and fetches courses with different enrollment state filters
to understand how dropped courses are represented.
"""

import os
import sys

# Add the src directory to the path so we can import canvas_mcp modules
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import canvas_mcp.config as config
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager


def main():
    """Main function to test enrollment states."""
    print("Initializing Canvas client...")
    db_manager = DatabaseManager(config.DB_PATH)
    canvas_client = CanvasClient(db_manager, config.API_KEY, config.API_URL)

    if canvas_client.canvas is None:
        print("Error: Canvas client not initialized properly.")
        return

    # Get current user
    user = canvas_client.canvas.get_current_user()
    print(f"Current user: {user.name} (ID: {user.id})")

    # Get all courses without filtering
    print("\nFetching all courses without filtering...")
    all_courses = list(user.get_courses())
    print(f"Found {len(all_courses)} courses")

    # Print course details including enrollment state
    print("\nCourse details:")
    for course in all_courses:
        # Try to get enrollment state
        enrollment_state = None
        if hasattr(course, "enrollments") and course.enrollments:
            enrollment_state = course.enrollments[0].get("enrollment_state", "unknown")

        course_name = getattr(course, "name", "Unknown Name")
        course_id = getattr(course, "id", "Unknown ID")
        print(f"- {course_name} (ID: {course_id})")
        print(f"  Code: {getattr(course, 'course_code', 'N/A')}")
        print(f"  Enrollment State: {enrollment_state}")
        print(f"  Workflow State: {getattr(course, 'workflow_state', 'N/A')}")

        # Print all attributes for debugging
        print("  All attributes:")
        for attr in dir(course):
            if not attr.startswith("_") and not callable(getattr(course, attr)):
                try:
                    value = getattr(course, attr)
                    print(f"    {attr}: {value}")
                except Exception as e:
                    print(f"    {attr}: Error accessing attribute - {e}")
        print()

    # Try to get courses with specific enrollment states
    enrollment_states = ["active", "invited", "completed", "deleted"]
    for state in enrollment_states:
        try:
            print(f"\nFetching courses with enrollment_state={state}...")
            filtered_courses = list(user.get_courses(enrollment_state=state))
            print(f"Found {len(filtered_courses)} courses with state '{state}'")
            for course in filtered_courses:
                print(f"- {course.name} (ID: {course.id})")
        except Exception as e:
            print(f"Error fetching courses with state '{state}': {e}")


if __name__ == "__main__":
    main()
