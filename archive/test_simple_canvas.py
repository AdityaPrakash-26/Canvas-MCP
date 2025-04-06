"""
Simple test to directly test Canvas API access without MCP dependencies.
"""
import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.environ.get("CANVAS_ACCESS_TOKEN") or os.environ.get("CANVAS_API_KEY")
if not API_KEY:
    print("ERROR: CANVAS_ACCESS_TOKEN or CANVAS_API_KEY not found in .env file")
    print("Please create a .env file with your Canvas API token")
    exit(1)

API_URL = os.environ.get("CANVAS_BASE_URL") or os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
print(f"Using API URL: {API_URL}")

# Import CanvasAPI
from canvasapi import Canvas
print("Successfully imported canvasapi module")

# Initialize Canvas API
canvas = Canvas(API_URL, API_KEY)

# Test direct Canvas API access
print("\nTesting direct API access...")
try:
    user = canvas.get_current_user()
    print(f"Successfully authenticated as user: {user.name} (ID: {user.id})")
except Exception as e:
    print(f"Error accessing Canvas API directly: {e}")
    print("API response or details if available:", getattr(e, 'response', None))
    exit(1)  # Exit if we can't authenticate

print("\nTesting direct course access...")
try:
    # Get courses from Canvas
    courses = list(user.get_courses())
    print(f"Found {len(courses)} courses for user {user.id}")

    # Debugging: check if any courses have term_id
    term_ids = set()
    for course in courses:
        term_id = getattr(course, 'enrollment_term_id', None)
        if term_id is not None:
            term_ids.add(term_id)

    if term_ids:
        print(f"Found courses with term IDs: {term_ids}")
        print(f"Maximum term ID (most recent): {max(term_ids)}")
        
        # Get courses in the most recent term
        max_term_id = max(term_ids)
        current_courses = [
            course for course in courses
            if getattr(course, 'enrollment_term_id', None) == max_term_id
        ]
        print(f"Found {len(current_courses)} courses in the most recent term (ID: {max_term_id})")
        
        # Print course details
        for i, course in enumerate(current_courses[:5]):  # Show first 5
            print(f"  {i+1}. {course.name} ({getattr(course, 'course_code', 'No code')}) - ID: {course.id}")
        if len(current_courses) > 5:
            print(f"  ... and {len(current_courses) - 5} more courses")
            
        # Test getting details for the first course
        if current_courses:
            print("\nTesting detailed course access...")
            try:
                first_course = current_courses[0]
                detailed_course = canvas.get_course(first_course.id)
                print(f"Got detailed info for course: {detailed_course.name}")
                
                # Print course attributes
                attributes = ['term_id', 'start_at', 'end_at', 'course_code', 'teacher', 'syllabus_body']
                for attr in attributes:
                    value = getattr(detailed_course, attr, None)
                    if attr == 'syllabus_body' and value:
                        print(f"  {attr}: {value[:100]}..." if len(str(value)) > 100 else f"  {attr}: {value}")
                    else:
                        print(f"  {attr}: {value}")
                
                # Test getting assignments
                print("\nTesting assignment access...")
                try:
                    assignments = list(detailed_course.get_assignments())
                    print(f"Found {len(assignments)} assignments for course {detailed_course.name}")
                    
                    # Print assignment details
                    for i, assignment in enumerate(assignments[:3]):  # Show first 3
                        print(f"  {i+1}. {assignment.name} - Due: {getattr(assignment, 'due_at', 'No due date')}")
                    if len(assignments) > 3:
                        print(f"  ... and {len(assignments) - 3} more assignments")
                except Exception as e:
                    print(f"Error getting assignments: {e}")
                
                # Test getting modules
                print("\nTesting module access...")
                try:
                    modules = list(detailed_course.get_modules())
                    print(f"Found {len(modules)} modules for course {detailed_course.name}")
                    
                    # Print module details
                    for i, module in enumerate(modules[:3]):  # Show first 3
                        print(f"  {i+1}. {module.name}")
                    if len(modules) > 3:
                        print(f"  ... and {len(modules) - 3} more modules")
                except Exception as e:
                    print(f"Error getting modules: {e}")
                
            except Exception as e:
                print(f"Error getting detailed course info: {e}")
    else:
        print("No courses found with term_id attribute")
        
except Exception as e:
    print(f"Error accessing courses directly: {e}")
    print("API response or details if available:", getattr(e, 'response', None))

print("\nTest completed.")
