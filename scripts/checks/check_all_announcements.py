#!/usr/bin/env python3
"""
Script to check Canvas announcements through multiple methods.
"""

import datetime
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Canvas MCP components
import src.canvas_mcp.config as config


def format_datetime(dt):
    """Format datetime for display."""
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def main():
    """Main function to check Canvas announcements through multiple methods."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get all courses
        courses = list(user.get_courses(enrollment_state="active"))
        print(f"\nFound {len(courses)} active courses:")

        for course in courses:
            print(f"\n{'=' * 80}")
            print(f"Course: {course.name} ({course.course_code}) - ID: {course.id}")

            # Method 1: Get announcements via discussion topics with only_announcements=True
            print("\nMethod 1: Discussion topics with only_announcements=True")
            try:
                announcements1 = list(
                    course.get_discussion_topics(only_announcements=True)
                )
                print(f"Found {len(announcements1)} announcements")
                for a in announcements1[:3]:  # Show first 3
                    print(
                        f"- {a.title} (ID: {a.id}, Posted: {format_datetime(getattr(a, 'posted_at', 'Unknown'))})"
                    )
                if len(announcements1) > 3:
                    print(f"  ... and {len(announcements1) - 3} more")
            except Exception as e:
                print(f"Error: {e}")

            # Method 2: Get all discussion topics and filter for announcements
            print("\nMethod 2: All discussion topics, filtered for announcements")
            try:
                all_discussions = list(course.get_discussion_topics())
                announcements2 = [
                    d for d in all_discussions if getattr(d, "is_announcement", False)
                ]
                print(
                    f"Found {len(announcements2)} announcements out of {len(all_discussions)} discussions"
                )
                for a in announcements2[:3]:  # Show first 3
                    print(
                        f"- {a.title} (ID: {a.id}, Posted: {format_datetime(getattr(a, 'posted_at', 'Unknown'))})"
                    )
                if len(announcements2) > 3:
                    print(f"  ... and {len(announcements2) - 3} more")
            except Exception as e:
                print(f"Error: {e}")

            # Method 3: Try to access announcements directly
            print("\nMethod 3: Direct announcements endpoint")
            try:
                # This is a custom request since canvasapi doesn't have a direct method
                url = f"{config.API_URL}/courses/{course.id}/announcements"
                headers = {"Authorization": f"Bearer {config.API_KEY}"}

                import requests

                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    announcements3 = response.json()
                    print(f"Found {len(announcements3)} announcements")
                    for a in announcements3[:3]:  # Show first 3
                        print(
                            f"- {a.get('title')} (ID: {a.get('id')}, Posted: {format_datetime(a.get('posted_at', 'Unknown'))})"
                        )
                    if len(announcements3) > 3:
                        print(f"  ... and {len(announcements3) - 3} more")
                else:
                    print(f"Error: Status code {response.status_code}")
                    print(f"Response: {response.text[:100]}...")
            except Exception as e:
                print(f"Error: {e}")

            # Method 4: Check activity stream
            print("\nMethod 4: Activity stream")
            try:
                activities = list(course.get_activity_stream())
                announcements4 = [
                    a for a in activities if getattr(a, "type", "") == "Announcement"
                ]
                print(f"Found {len(announcements4)} announcements in activity stream")
                for a in announcements4[:3]:  # Show first 3
                    print(
                        f"- {getattr(a, 'title', 'No title')} (ID: {getattr(a, 'id', 'No ID')}, Posted: {format_datetime(getattr(a, 'created_at', 'Unknown'))})"
                    )
                if len(announcements4) > 3:
                    print(f"  ... and {len(announcements4) - 3} more")
            except Exception as e:
                print(f"Error: {e}")

            # Method 5: Check recent messages
            print("\nMethod 5: Recent messages")
            try:
                messages = list(user.get_messages(context_code=f"course_{course.id}"))
                print(f"Found {len(messages)} messages")
                for m in messages[:3]:  # Show first 3
                    print(
                        f"- {getattr(m, 'subject', 'No subject')} (ID: {getattr(m, 'id', 'No ID')}, Created: {format_datetime(getattr(m, 'created_at', 'Unknown'))})"
                    )
                if len(messages) > 3:
                    print(f"  ... and {len(messages) - 3} more")
            except Exception as e:
                print(f"Error: {e}")

            print(f"{'=' * 80}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
