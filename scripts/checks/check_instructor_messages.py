#!/usr/bin/env python3
"""
Script to check for instructor messages in Canvas.
This script focuses on using the canvasapi library directly.
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
    """Main function to check for instructor messages."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get IDS 385 course
        course_id = 65920000000145100  # IDS 385
        print(f"\nChecking course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Get course instructors
        print("\nGetting course instructors:")
        instructors = []
        try:
            for enrollment in course.get_enrollments():
                if hasattr(enrollment, "type") and "teacher" in enrollment.type.lower():
                    instructor_id = enrollment.user_id
                    instructors.append(instructor_id)
                    print(f"- Instructor ID: {instructor_id}")

                    # Try to get more details about this instructor
                    try:
                        instructor = canvas_api_client.get_user(instructor_id)
                        print(f"  Name: {instructor.name}")
                    except Exception as e:
                        print(f"  Error getting instructor details: {e}")
        except Exception as e:
            print(f"Error getting enrollments: {e}")

        print(f"\nFound {len(instructors)} instructors")

        # Try to get conversations
        print("\nAttempting to get conversations:")
        try:
            # First try the standard method
            conversations = list(user.get_conversations())
            print(f"Found {len(conversations)} conversations")

            # Filter for IDS 385 conversations
            ids385_conversations = []
            for conv in conversations:
                if hasattr(conv, "context_name"):
                    context_name = conv.context_name
                    if "IDS-385" in context_name or "IDS 385" in context_name:
                        ids385_conversations.append(conv)

            print(
                f"Found {len(ids385_conversations)} conversations related to IDS 385:"
            )
            for i, conv in enumerate(ids385_conversations):
                print(f"\nConversation {i + 1}:")
                print(f"- Subject: {getattr(conv, 'subject', 'No subject')}")
                print(f"- Context: {getattr(conv, 'context_name', 'Unknown')}")

                # Check if any participants are instructors
                participants = getattr(conv, "participants", [])
                instructor_found = False
                for participant in participants:
                    participant_id = getattr(participant, "id", None)
                    if participant_id in instructors:
                        instructor_found = True
                        print(f"- From instructor: Yes (ID: {participant_id})")
                        break

                if not instructor_found:
                    print("- From instructor: No")

                # Try to get messages
                try:
                    messages = conv.get_messages()
                    print(f"- Messages: {len(messages)}")
                    for j, msg in enumerate(messages[:2]):
                        print(f"  Message {j + 1}:")
                        print(f"  From: {getattr(msg, 'author_name', 'Unknown')}")
                        print(f"  Body: {getattr(msg, 'body', 'No body')[:100]}...")
                    if len(messages) > 2:
                        print(f"  ... and {len(messages) - 2} more messages")
                except Exception as e:
                    print(f"  Error getting messages: {e}")
        except Exception as e:
            print(f"Error getting conversations: {e}")

        # Try to get announcements one more time
        print("\nChecking announcements one more time:")
        try:
            announcements = list(course.get_discussion_topics(only_announcements=True))
            print(f"Found {len(announcements)} announcements via get_discussion_topics")

            # Try to get all discussion topics and filter
            all_discussions = list(course.get_discussion_topics())
            announcement_discussions = [
                d for d in all_discussions if getattr(d, "is_announcement", False)
            ]
            print(
                f"Found {len(announcement_discussions)} announcements by filtering all discussions"
            )

            # Check if there are any discussions that might be announcements
            print(f"Found {len(all_discussions)} total discussion topics:")
            for i, d in enumerate(all_discussions):
                print(f"- Discussion {i + 1}: {getattr(d, 'title', 'No title')}")
                print(
                    f"  Type: {'Announcement' if getattr(d, 'is_announcement', False) else 'Discussion'}"
                )
                print(
                    f"  Author: {getattr(d, 'author', {}).get('display_name', 'Unknown')}"
                )
                print(
                    f"  Posted at: {format_datetime(getattr(d, 'posted_at', 'Unknown'))}"
                )
        except Exception as e:
            print(f"Error checking announcements: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
