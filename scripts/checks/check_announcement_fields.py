#!/usr/bin/env python3
"""
Script to check the fields available in Canvas announcement objects.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Canvas MCP components
from src.canvas_mcp.config import API_KEY, API_URL


def main():
    """Main function to check announcement fields."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(API_URL, API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get a course with announcements
        course_id = 65920000000144735  # CS-110-1 (from previous output)
        print(f"\nChecking course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Get announcements
        print("\nFetching announcements...")
        announcements = list(course.get_discussion_topics(only_announcements=True))
        print(f"Found {len(announcements)} announcements")

        if announcements:
            # Get the first announcement
            announcement = announcements[0]
            print(f"\nFirst announcement: {announcement.title}")

            # Print all attributes
            print("\nAll attributes:")
            for attr_name in dir(announcement):
                if not attr_name.startswith("_") and not callable(
                    getattr(announcement, attr_name)
                ):
                    try:
                        attr_value = getattr(announcement, attr_name)
                        if attr_name == "author":
                            print(f"  {attr_name}: {attr_value}")
                            # If author is a dict, print its keys
                            if isinstance(attr_value, dict):
                                print(f"    Keys: {attr_value.keys()}")
                                for k, v in attr_value.items():
                                    print(f"    {k}: {v}")
                        else:
                            print(f"  {attr_name}: {attr_value}")
                    except Exception as e:
                        print(f"  {attr_name}: Error accessing attribute - {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
