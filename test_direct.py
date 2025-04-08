#!/usr/bin/env python3
"""
Direct test script for Canvas client functionality without importing the full module.
This script creates a simplified version to test the database and API connections.
"""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure paths
PROJECT_DIR = Path(__file__).parent
DB_DIR = PROJECT_DIR / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"


# Define a minimal version of the Canvas client for testing
class TestCanvasClient:
    """Simplified Canvas client for testing"""

    def __init__(
        self, db_path: str, api_key: str | None = None, api_url: str | None = None
    ):
        """Initialize the Canvas client."""
        # Load environment variables if api_key not provided
        if api_key is None:
            load_dotenv()
            api_key = os.environ.get("CANVAS_API_KEY")

        self.api_key = api_key
        self.api_url = api_url or "https://canvas.instructure.com"
        self.db_path = db_path

        # Try to import canvasapi
        try:
            from canvasapi import Canvas

            self.canvas = Canvas(self.api_url, self.api_key)
            print("✅ canvasapi module found and Canvas instance created")
        except ImportError:
            self.canvas = None
            print("❌ canvasapi module not found")

    def connect_db(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Connect to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    def test_database(self):
        """Test database connection and structure"""
        try:
            conn, cursor = self.connect_db()

            # Check if tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name;
            """)
            tables = cursor.fetchall()

            print(f"Found {len(tables)} tables in the database:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table['name']}")
                count = cursor.fetchone()[0]
                print(f"  - {table['name']}: {count} rows")

            # Check for courses
            if "courses" in [table["name"] for table in tables]:
                cursor.execute(
                    "SELECT id, course_code, course_name FROM courses LIMIT 3"
                )
                courses = cursor.fetchall()

                if courses:
                    print("\nSample courses:")
                    for course in courses:
                        print(f"  - {course['course_code']}: {course['course_name']}")

            conn.close()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False

    def test_canvas_api(self):
        """Test Canvas API connection"""
        if not self.canvas:
            print("Canvas API client not available")
            return False

        try:
            user = self.canvas.get_current_user()
            print("\nCanvas API test successful!")
            print(f"Connected as: {user.name}")

            # Try to get courses
            courses = list(self.canvas.get_courses())
            print(f"Found {len(courses)} courses in Canvas")

            if courses:
                print("Sample courses from Canvas API:")
                for course in courses[:3]:  # Show up to 3 courses
                    print(f"  - {getattr(course, 'course_code', 'N/A')}: {course.name}")

            return True
        except Exception as e:
            print(f"Canvas API error: {e}")
            return False


# Main test function
def main():
    print("Canvas Client Direct Test")
    print("========================\n")

    API_KEY = os.environ.get("CANVAS_API_KEY")
    API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

    print(f"Canvas API URL: {API_URL}")
    print(
        f"Canvas API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:] if API_KEY else 'Not set'}"
    )
    print(f"Database Path: {DB_PATH}\n")

    # Check if database file exists
    if not DB_PATH.exists():
        print(f"❌ Database file does not exist at {DB_PATH}")
        return
    else:
        print(f"✅ Database file exists at {DB_PATH}")

    # Create test client
    client = TestCanvasClient(str(DB_PATH), API_KEY, API_URL)

    # Test database
    print("\nTesting database connection and structure...")
    db_result = client.test_database()

    # Test Canvas API
    print("\nTesting Canvas API connection...")
    api_result = client.test_canvas_api()

    # Overall status
    print("\n==== Test Summary ====")
    print(f"Database Tests: {'✅ Passed' if db_result else '❌ Failed'}")
    print(f"Canvas API Tests: {'✅ Passed' if api_result else '❌ Failed'}")
    print("=====================")


if __name__ == "__main__":
    main()
