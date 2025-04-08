"""
Integration test for Canvas MCP using real credentials from .env file.
This test validates that our Canvas client can actually connect to the Canvas API
and synchronize data into the local database.
"""

import os
import sqlite3
import sys
from pathlib import Path

# Add the project directory to the Python path to make imports work
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from dotenv import load_dotenv

# Import canvas_client directly to avoid the mcp dependency in server.py
sys.path.insert(0, str(project_dir / "src"))
from canvas_mcp.canvas_client import CanvasClient

# Load environment variables
load_dotenv()
API_KEY = os.environ.get("CANVAS_ACCESS_TOKEN") or os.environ.get("CANVAS_API_KEY")
if not API_KEY:
    print("ERROR: CANVAS_ACCESS_TOKEN or CANVAS_API_KEY not found in .env file")
    print("Please create a .env file with your Canvas API token")
    exit(1)

# Configure paths
PROJECT_DIR = Path(__file__).parent
DB_DIR = PROJECT_DIR / "data"
DB_PATH = DB_DIR / "integration_test.db"

# Ensure directories exist
os.makedirs(DB_DIR, exist_ok=True)

# Remove test database if it exists
if DB_PATH.exists():
    os.remove(DB_PATH)

# Create a fresh database
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Create minimal test schema
print("Creating test database...")
cursor.execute("""
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    canvas_course_id INTEGER UNIQUE NOT NULL,
    course_code TEXT NOT NULL,
    course_name TEXT NOT NULL,
    instructor TEXT,
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE syllabi (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    content TEXT,
    content_type TEXT DEFAULT 'html',
    parsed_content TEXT,
    is_parsed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
)
""")

cursor.execute("""
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    canvas_assignment_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    assignment_type TEXT,
    due_date TIMESTAMP,
    available_from TIMESTAMP,
    available_until TIMESTAMP,
    points_possible REAL,
    submission_types TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (course_id, canvas_assignment_id)
)
""")

cursor.execute("""
CREATE TABLE modules (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    canvas_module_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    unlock_date TIMESTAMP,
    position INTEGER,
    require_sequential_progress BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (course_id, canvas_module_id)
)
""")

cursor.execute("""
CREATE TABLE module_items (
    id INTEGER PRIMARY KEY,
    module_id INTEGER NOT NULL,
    canvas_item_id INTEGER,
    title TEXT NOT NULL,
    item_type TEXT NOT NULL,
    position INTEGER,
    url TEXT,
    page_url TEXT,
    content_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
)
""")

cursor.execute("""
CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT NOT NULL,
    source_type TEXT,
    source_id INTEGER,
    event_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    all_day BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
)
""")

cursor.execute("""
CREATE TABLE user_courses (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id INTEGER NOT NULL,
    indexing_opt_out BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (user_id, course_id)
)
""")

cursor.execute("""
CREATE TABLE announcements (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    canvas_announcement_id INTEGER,
    title TEXT NOT NULL,
    content TEXT,
    posted_by TEXT,
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
)
""")

conn.commit()
conn.close()
print("Test database created successfully")

# Initialize Canvas client with real credentials
API_URL = os.environ.get("CANVAS_BASE_URL") or os.environ.get(
    "CANVAS_API_URL", "https://canvas.instructure.com"
)
client = CanvasClient(str(DB_PATH), API_KEY, API_URL)

try:
    # COMPLETELY SKIP THE INITIAL PART OF THE TEST AND GO DIRECTLY TO TERM FILTERING
    print("\n-------------------------------------------------------")
    print("TESTING TERM FILTERING WITH CANVAS CLIENT")
    print("-------------------------------------------------------")

    print(f"Using API URL: {API_URL}")

    # Test direct Canvas API access first
    print("\nTesting direct API access...")
    if hasattr(client, "canvas") and client.canvas:
        try:
            user = client.canvas.get_current_user()
            print(f"Successfully authenticated as user: {user.name} (ID: {user.id})")
        except Exception as e:
            print(f"Error accessing Canvas API directly: {e}")
            print("API response or details if available:", getattr(e, "response", None))
            exit(1)  # Exit if we can't authenticate
    else:
        print("Canvas API client not properly initialized")
        exit(1)  # Exit if client isn't initialized properly

    print("\nTesting direct course access...")
    try:
        # Get current user
        user = client.canvas.get_current_user()
        courses = list(user.get_courses())
        print(f"Found {len(courses)} courses for user {user.id}")

        # Debugging: check if any courses have term_id
        term_ids = set()
        for course in courses:
            term_id = getattr(course, "enrollment_term_id", None)
            if term_id is not None:
                term_ids.add(term_id)

        if term_ids:
            print(f"Found courses with term IDs: {term_ids}")
            print(f"Maximum term ID (most recent): {max(term_ids)}")
        else:
            print("No courses found with term_id attribute")
    except Exception as e:
        print(f"Error accessing courses directly: {e}")
        print("API response or details if available:", getattr(e, "response", None))

    # RESET: Clean database and start fresh with term filtering
    print("\n-------------------------------------------------------")
    print("RESETTING DATABASE AND TESTING TERM FILTERING PROPERLY")
    print("-------------------------------------------------------")

    # Remove existing data so we can start fresh
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    tables = [
        "courses",
        "syllabi",
        "assignments",
        "modules",
        "module_items",
        "calendar_events",
        "announcements",
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    # Test sync_all with term filtering (most recent term)
    print(
        "\nTesting sync_all with term_id=-1 to get only the most recent term courses..."
    )
    result = client.sync_all(term_id=-1)
    print("Sync results with term filtering:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # Show the courses that were synced with term filtering
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM courses")
    filtered_courses = cursor.fetchall()

    print("\nCourses synced with term filtering:")
    for i, course in enumerate(filtered_courses):
        print(f"  {i + 1}. {course['course_name']} ({course['course_code']})")

    print(f"\nTotal courses with term filtering: {len(filtered_courses)}")

    # Now test assignments, modules and announcements using the first CURRENT course
    if filtered_courses:
        first_course = filtered_courses[0]
        first_course_id = first_course["id"]
        canvas_course_id = first_course["canvas_course_id"]

        print(
            f"\nTesting with first CURRENT course: {first_course['course_name']} (ID: {canvas_course_id})"
        )

        # Fetch assignments for the first course
        try:
            print("\nFetching assignments for current course...")
            assignments_count = client.sync_assignments([first_course_id])
            print(f"Successfully synced {assignments_count} assignments")

            cursor.execute(
                "SELECT * FROM assignments WHERE course_id = ?", (first_course_id,)
            )
            assignments = cursor.fetchall()

            if assignments:
                print("\nAssignments for current course:")
                for i, assignment in enumerate(assignments[:5]):  # Show first 5 only
                    due_date = (
                        assignment["due_date"]
                        if assignment["due_date"]
                        else "No due date"
                    )
                    print(f"  {i + 1}. {assignment['title']} - Due: {due_date}")
                if len(assignments) > 5:
                    print(f"  ... and {len(assignments) - 5} more assignments")
            else:
                print("No assignments found for this course")
        except Exception as e:
            print(f"Error fetching assignments: {e}")

        # Fetch modules for the first course
        try:
            print("\nFetching modules for current course...")
            modules_count = client.sync_modules([first_course_id])
            print(f"Successfully synced {modules_count} modules")

            cursor.execute(
                "SELECT * FROM modules WHERE course_id = ?", (first_course_id,)
            )
            modules = cursor.fetchall()

            if modules:
                print("\nModules for current course:")
                for i, module in enumerate(modules[:5]):  # Show first 5 only
                    print(f"  {i + 1}. {module['name']}")
                if len(modules) > 5:
                    print(f"  ... and {len(modules) - 5} more modules")

                # Check module items for first module
                if modules:
                    first_module_id = modules[0]["id"]
                    cursor.execute(
                        "SELECT * FROM module_items WHERE module_id = ?",
                        (first_module_id,),
                    )
                    items = cursor.fetchall()

                    if items:
                        print(f"\nItems in first module ({modules[0]['name']}):")
                        for i, item in enumerate(items[:5]):  # Show first 5 only
                            print(f"  {i + 1}. {item['title']} ({item['item_type']})")
                        if len(items) > 5:
                            print(f"  ... and {len(items) - 5} more items")
            else:
                print("No modules found for this course")
        except Exception as e:
            print(f"Error fetching modules: {e}")

        # Fetch announcements for the first course
        try:
            print("\nFetching announcements for current course...")
            announcements_count = client.sync_announcements([first_course_id])
            print(f"Successfully synced {announcements_count} announcements")

            cursor.execute(
                "SELECT * FROM announcements WHERE course_id = ?", (first_course_id,)
            )
            announcements = cursor.fetchall()

            if announcements:
                print("\nAnnouncements for current course:")
                for i, announcement in enumerate(
                    announcements[:5]
                ):  # Show first 5 only
                    print(f"  {i + 1}. {announcement['title']}")
                if len(announcements) > 5:
                    print(f"  ... and {len(announcements) - 5} more announcements")
            else:
                print("No announcements found for this course")
        except Exception as e:
            print(f"Error fetching announcements: {e}")

    conn.close()

    print("\n-------------------------------------------------------")
    print("Integration test with term filtering completed successfully!")
    print("-------------------------------------------------------")

except Exception as e:
    print(f"\nERROR during integration testing: {e}")

finally:
    if "conn" in locals() and conn:
        conn.close()
