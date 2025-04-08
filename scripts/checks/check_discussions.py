#!/usr/bin/env python3
"""
Script to check Canvas discussions for a specific course.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
import src.canvas_mcp.config as config


def main():
    """Main function to check Canvas discussions."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get course
        course_id = 65920000000145100  # IDS 385
        print(f"Checking discussions for course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Get all discussion topics (not just announcements)
        print("\nFetching all discussion topics...")
        discussions = list(course.get_discussion_topics())

        print(f"Found {len(discussions)} discussion topics:")
        for discussion in discussions:
            print(f"- ID: {discussion.id}")
            print(f"  Title: {discussion.title}")
            print(
                f"  Type: {'Announcement' if getattr(discussion, 'is_announcement', False) else 'Discussion'}"
            )
            print(f"  Posted at: {getattr(discussion, 'posted_at', 'Unknown')}")
            print(
                f"  Author: {getattr(discussion, 'author', {}).get('display_name', 'Unknown')}"
            )
            print()

        # Check course homepage
        print("\nChecking course homepage...")
        try:
            front_page = course.get_front_page()
            print(f"Front page title: {front_page.title}")
            print(
                f"Front page updated at: {getattr(front_page, 'updated_at', 'Unknown')}"
            )
        except Exception as e:
            print(f"Error getting front page: {e}")

        # Check course pages
        print("\nChecking course pages...")
        try:
            pages = list(course.get_pages())
            print(f"Found {len(pages)} pages:")
            for page in pages[:5]:  # Show first 5 pages
                print(f"- {page.title}")
                if hasattr(page, "updated_at"):
                    print(f"  Updated: {page.updated_at}")
            if len(pages) > 5:
                print(f"  ... and {len(pages) - 5} more pages")
        except Exception as e:
            print(f"Error getting pages: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
