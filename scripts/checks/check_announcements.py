#!/usr/bin/env python3
"""
Script to check Canvas announcements for a specific course.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
import src.canvas_mcp.config as config


def main():
    """Main function to check Canvas announcements."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get course
        course_id = 65920000000145100  # IDS 385
        print(f"Checking announcements for course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Get announcements
        print("\nFetching announcements...")
        announcements = list(course.get_discussion_topics(only_announcements=True))

        print(f"Found {len(announcements)} announcements:")
        for announcement in announcements:
            print(f"- ID: {announcement.id}")
            print(f"  Title: {announcement.title}")
            print(f"  Posted at: {getattr(announcement, 'posted_at', 'Unknown')}")
            print(
                f"  Author: {getattr(announcement, 'author', {}).get('display_name', 'Unknown')}"
            )
            print()

        # Check if announcements are in the database
        print("\nChecking database for these announcements:")
        import sqlite3

        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for announcement in announcements:
            cursor.execute(
                "SELECT * FROM announcements WHERE canvas_announcement_id = ?",
                (announcement.id,),
            )
            db_announcement = cursor.fetchone()

            if db_announcement:
                print(
                    f"- Announcement {announcement.id} found in database (ID: {db_announcement['id']})"
                )
            else:
                print(f"- Announcement {announcement.id} NOT found in database")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
