#!/usr/bin/env python3
"""
Test script to explore Canvas API data structure.
This is a temporary file for analysis purposes only.
"""

import os
import sys

from dotenv import load_dotenv

try:
    from canvasapi import Canvas
except ImportError:
    print("canvasapi module not found. Installing...")
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "uv", "add", "canvasapi", "python-dotenv"]
    )
    from canvasapi import Canvas

# Load environment variables
load_dotenv()

# Canvas API URL and key
API_URL = os.environ.get("CANVAS_BASE_URL")
API_KEY = os.environ.get("CANVAS_API_KEY")

if not API_KEY:
    print("Error: CANVAS_API_KEY not found in environment variables.")
    sys.exit(1)

# Initialize Canvas API
canvas = Canvas(API_URL, API_KEY)

try:
    # Get current user
    user = canvas.get_current_user()
    print(f"Authenticated as: {user.name} (ID: {user.id})")

    # Fetch courses
    print("\n=== Courses ===")
    courses = user.get_courses()
    for course in courses:
        print(f"Course: {course.name} (ID: {course.id})")

        # Fetch course detailed information (including syllabus)
        detailed_course = canvas.get_course(course.id)
        if hasattr(detailed_course, "syllabus_body") and detailed_course.syllabus_body:
            print(
                f"  Syllabus available: {len(detailed_course.syllabus_body)} characters"
            )
        else:
            print("  No syllabus found")

        # Fetch assignments for the course
        try:
            print("\n  === Assignments ===")
            assignments = course.get_assignments()
            for assignment in assignments:
                print(f"  Assignment: {assignment.name}")
                print(
                    f"    Due: {assignment.due_at if hasattr(assignment, 'due_at') else 'No due date'}"
                )
                print(f"    Points: {assignment.points_possible}")
        except Exception as e:
            print(f"  Error fetching assignments: {e}")

        # Fetch modules for the course
        try:
            print("\n  === Modules ===")
            modules = course.get_modules()
            for module in modules:
                print(f"  Module: {module.name}")

                # Fetch module items
                try:
                    items = module.get_module_items()
                    print(f"    Items: {len(list(items))}")
                except Exception as e:
                    print(f"    Error fetching module items: {e}")
        except Exception as e:
            print(f"  Error fetching modules: {e}")

        # Only process one course for this initial test
        break

except Exception as e:
    print(f"Error: {e}")
