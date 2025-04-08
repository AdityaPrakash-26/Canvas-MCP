#!/usr/bin/env python
"""
Test script to directly interact with Canvas API.

This script uses the canvasapi library to directly interact with the Canvas API
and explore different ways to fetch courses, especially dropped courses.
"""

import os
import sys

# Add the src directory to the path so we can import canvas_mcp modules
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from canvasapi import Canvas

import canvas_mcp.config as config


def main():
    """Main function to test Canvas API."""
    print("Initializing Canvas API...")
    canvas = Canvas(config.API_URL, config.API_KEY)

    # Get current user
    user = canvas.get_current_user()
    print(f"Current user: {user.name} (ID: {user.id})")

    # Try different ways to get courses
    print("\nTrying different ways to get courses...")

    # Method 1: Get courses directly from Canvas
    print("\nMethod 1: Get courses directly from Canvas")
    try:
        courses = list(canvas.get_courses())
        print(f"Found {len(courses)} courses")
        for course in courses[:3]:  # Just show first 3 to avoid too much output
            print(
                f"- {getattr(course, 'name', 'Unknown')} (ID: {getattr(course, 'id', 'Unknown')})"
            )
    except Exception as e:
        print(f"Error: {e}")

    # Method 2: Get courses from user
    print("\nMethod 2: Get courses from user")
    try:
        user_courses = list(user.get_courses())
        print(f"Found {len(user_courses)} courses")
        for course in user_courses[:3]:  # Just show first 3
            print(
                f"- {getattr(course, 'name', 'Unknown')} (ID: {getattr(course, 'id', 'Unknown')})"
            )
    except Exception as e:
        print(f"Error: {e}")

    # Method 3: Get courses with include parameter
    print("\nMethod 3: Get courses with include=['term'] parameter")
    try:
        courses_with_term = list(user.get_courses(include=["term"]))
        print(f"Found {len(courses_with_term)} courses")
        for course in courses_with_term[:3]:  # Just show first 3
            term_name = "Unknown"
            if hasattr(course, "term"):
                term_name = getattr(course.term, "name", "Unknown Term")
            print(
                f"- {getattr(course, 'name', 'Unknown')} (ID: {getattr(course, 'id', 'Unknown')}, Term: {term_name})"
            )
    except Exception as e:
        print(f"Error: {e}")

    # Method 4: Get courses with state parameter
    print("\nMethod 4: Get courses with state parameter")
    states = ["available", "completed", "deleted"]
    for state in states:
        try:
            state_courses = list(user.get_courses(state=[state]))
            print(f"Found {len(state_courses)} courses with state '{state}'")
            for course in state_courses[:3]:  # Just show first 3
                print(
                    f"- {getattr(course, 'name', 'Unknown')} (ID: {getattr(course, 'id', 'Unknown')})"
                )
        except Exception as e:
            print(f"Error with state '{state}': {e}")

    # Method 5: Get enrollments directly
    print("\nMethod 5: Get enrollments directly")
    try:
        enrollments = list(user.get_enrollments())
        print(f"Found {len(enrollments)} enrollments")

        # Group enrollments by state
        enrollments_by_state = {}
        for enrollment in enrollments:
            state = getattr(enrollment, "enrollment_state", "unknown")
            if state not in enrollments_by_state:
                enrollments_by_state[state] = []
            enrollments_by_state[state].append(enrollment)

        # Print counts by state
        print("Enrollment counts by state:")
        for state, enr_list in enrollments_by_state.items():
            print(f"- {state}: {len(enr_list)}")

        # Print some example enrollments for each state
        for state, enr_list in enrollments_by_state.items():
            print(f"\nExample enrollments with state '{state}':")
            for enrollment in enr_list[:2]:  # Just show first 2
                course_id = getattr(enrollment, "course_id", "Unknown")
                try:
                    course = canvas.get_course(course_id)
                    course_name = getattr(course, "name", "Unknown")
                except:
                    course_name = "Could not fetch course"

                print(f"- Course: {course_name} (ID: {course_id})")
                print(f"  Type: {getattr(enrollment, 'type', 'Unknown')}")
                print(f"  Role: {getattr(enrollment, 'role', 'Unknown')}")
                print(f"  State: {getattr(enrollment, 'enrollment_state', 'Unknown')}")

                # Print all attributes for this enrollment
                print("  All attributes:")
                for attr in dir(enrollment):
                    if not attr.startswith("_") and not callable(
                        getattr(enrollment, attr)
                    ):
                        try:
                            value = getattr(enrollment, attr)
                            print(f"    {attr}: {value}")
                        except Exception as e:
                            print(f"    {attr}: Error accessing attribute - {e}")
    except Exception as e:
        print(f"Error: {e}")

    # Look for info visualization course
    print("\nLooking for Info Visualization course...")
    try:
        all_courses = list(user.get_courses())
        for course in all_courses:
            course_name = getattr(course, "name", "")
            if course_name and "visualization" in course_name.lower():
                print(
                    f"Found course: {course_name} (ID: {getattr(course, 'id', 'Unknown')})"
                )

                # Try to get detailed course info
                try:
                    detailed_course = canvas.get_course(course.id)
                    print("Detailed course info:")
                    for attr in dir(detailed_course):
                        if not attr.startswith("_") and not callable(
                            getattr(detailed_course, attr)
                        ):
                            try:
                                value = getattr(detailed_course, attr)
                                print(f"  {attr}: {value}")
                            except Exception as e:
                                print(f"  {attr}: Error accessing attribute - {e}")
                except Exception as e:
                    print(f"Error getting detailed course info: {e}")

                # Try to get enrollments for this course
                try:
                    course_enrollments = list(course.get_enrollments())
                    print(
                        f"Found {len(course_enrollments)} enrollments for this course"
                    )
                    for enrollment in course_enrollments:
                        print(f"- User ID: {getattr(enrollment, 'user_id', 'Unknown')}")
                        print(f"  Type: {getattr(enrollment, 'type', 'Unknown')}")
                        print(f"  Role: {getattr(enrollment, 'role', 'Unknown')}")
                        print(
                            f"  State: {getattr(enrollment, 'enrollment_state', 'Unknown')}"
                        )
                except Exception as e:
                    print(f"Error getting course enrollments: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
