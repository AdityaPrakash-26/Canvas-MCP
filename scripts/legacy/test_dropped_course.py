#!/usr/bin/env python
"""
Test script to check for dropped courses in Canvas API.

This script connects to Canvas API and fetches courses with different enrollment state filters
to identify dropped courses.
"""

import json
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

    # Try different enrollment states
    enrollment_states = ["active", "invited", "completed", "deleted"]

    # Get all courses first
    print("\nFetching all courses without filtering...")
    all_courses = list(user.get_courses())
    print(f"Found {len(all_courses)} courses")

    # Create a dictionary to store courses by ID
    courses_by_id = {}
    for course in all_courses:
        course_id = getattr(course, "id", None)
        if course_id:
            courses_by_id[course_id] = course

    # Try each enrollment state
    for state in enrollment_states:
        try:
            print(f"\nFetching courses with enrollment_state={state}...")
            filtered_courses = list(user.get_courses(enrollment_state=state))
            print(f"Found {len(filtered_courses)} courses with state '{state}'")

            # Check which courses are in this state but not in active
            if state != "active":
                filtered_ids = {getattr(c, "id", None) for c in filtered_courses}
                active_courses = list(user.get_courses(enrollment_state="active"))
                active_ids = {getattr(c, "id", None) for c in active_courses}

                different_ids = filtered_ids - active_ids
                if different_ids:
                    print(f"Courses in state '{state}' but not in 'active':")
                    for course_id in different_ids:
                        course = courses_by_id.get(course_id)
                        if course:
                            course_name = getattr(course, "name", "Unknown")
                            print(f"- {course_name} (ID: {course_id})")

                            # Print all attributes for this course
                            print("  Attributes:")
                            for attr in dir(course):
                                if not attr.startswith("_") and not callable(
                                    getattr(course, attr)
                                ):
                                    try:
                                        value = getattr(course, attr)
                                        if attr == "enrollments":
                                            print(
                                                f"    {attr}: {json.dumps(value, indent=2)}"
                                            )
                                        else:
                                            print(f"    {attr}: {value}")
                                    except Exception as e:
                                        print(
                                            f"    {attr}: Error accessing attribute - {e}"
                                        )
        except Exception as e:
            print(f"Error fetching courses with state '{state}': {e}")

    # Try to find the info visualization course specifically
    print("\nLooking for Info Visualization course...")
    for course in all_courses:
        course_name = getattr(course, "name", "")
        if course_name and "visualization" in course_name.lower():
            print(
                f"Found course: {course_name} (ID: {getattr(course, 'id', 'Unknown')})"
            )

            # Print all attributes for this course
            print("  Attributes:")
            for attr in dir(course):
                if not attr.startswith("_") and not callable(getattr(course, attr)):
                    try:
                        value = getattr(course, attr)
                        if attr == "enrollments":
                            print(f"    {attr}: {json.dumps(value, indent=2)}")
                        else:
                            print(f"    {attr}: {value}")
                    except Exception as e:
                        print(f"    {attr}: Error accessing attribute - {e}")


if __name__ == "__main__":
    main()
