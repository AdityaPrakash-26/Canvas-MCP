"""
Script to check syllabus availability in Canvas courses.
"""
from canvasapi import Canvas
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.environ.get("CANVAS_ACCESS_TOKEN") or os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_BASE_URL") or os.environ.get("CANVAS_API_URL")

print(f"Using API URL: {API_URL}")

# Initialize Canvas API
canvas = Canvas(API_URL, API_KEY)

# Get user and courses
user = canvas.get_current_user()
print(f"Authenticated as: {user.name} (ID: {user.id})")

courses = list(user.get_courses())
print(f"Found {len(courses)} courses")

# Check each course for syllabus
print("\nChecking syllabi for all courses:")
for course in courses:
    try:
        detailed = canvas.get_course(course.id)
        has_syllabus = hasattr(detailed, 'syllabus_body') and detailed.syllabus_body is not None
        syllabus_status = "Has syllabus" if has_syllabus else "No syllabus"
        
        if has_syllabus:
            syllabus_length = len(detailed.syllabus_body)
            syllabus_preview = detailed.syllabus_body[:100] + "..." if syllabus_length > 100 else detailed.syllabus_body
            print(f"Course {course.name}: {syllabus_status}")
            print(f"  Length: {syllabus_length} chars")
            print(f"  Preview: {syllabus_preview}")
        else:
            print(f"Course {course.name}: {syllabus_status}")
    except Exception as e:
        print(f"Error with course {course.id}: {e}")

print("\nDone checking syllabi.")
