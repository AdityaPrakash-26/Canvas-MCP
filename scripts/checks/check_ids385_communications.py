#!/usr/bin/env python3
"""
Script to check all possible communications in the IDS 385 course.
"""

import datetime
import sys
from pathlib import Path

import requests

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
    """Main function to check all communications in IDS 385."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get IDS 385 course
        course_id = 65920000000145100  # IDS 385
        print(f"Checking communications for course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Check discussions in detail
        print("\nChecking all discussion topics in detail...")
        try:
            discussions = list(course.get_discussion_topics())
            print(f"Found {len(discussions)} discussion topics:")

            for i, discussion in enumerate(discussions):
                print(f"\nDiscussion {i + 1}/{len(discussions)}:")
                print(f"- ID: {discussion.id}")
                print(f"- Title: {discussion.title}")
                print(
                    f"- Type: {'Announcement' if getattr(discussion, 'is_announcement', False) else 'Discussion'}"
                )
                print(
                    f"- Posted at: {format_datetime(getattr(discussion, 'posted_at', 'Unknown'))}"
                )
                print(
                    f"- Author: {getattr(discussion, 'author', {}).get('display_name', 'Unknown')}"
                )

                # Get discussion details
                try:
                    details = discussion.get_entries()
                    entries = list(details)
                    print(f"- Entries: {len(entries)}")
                    for j, entry in enumerate(entries[:3]):  # Show first 3 entries
                        print(
                            f"  Entry {j + 1}: by {getattr(entry, 'user_name', 'Unknown')}"
                        )
                        print(
                            f"  Posted: {format_datetime(getattr(entry, 'created_at', 'Unknown'))}"
                        )
                    if len(entries) > 3:
                        print(f"  ... and {len(entries) - 3} more entries")
                except Exception as e:
                    print(f"  Error getting entries: {e}")
        except Exception as e:
            print(f"Error getting discussions: {e}")

        # Try to access inbox/conversations
        print("\nChecking inbox/conversations...")
        try:
            user = canvas_api_client.get_current_user()
            conversations = list(user.get_conversations())
            print(f"Found {len(conversations)} conversations in inbox")

            # Filter for IDS 385 conversations
            ids385_conversations = []
            for conv in conversations:
                context_name = getattr(conv, "context_name", "")
                if "IDS-385" in context_name or "IDS 385" in context_name:
                    ids385_conversations.append(conv)

            print(
                f"Found {len(ids385_conversations)} conversations related to IDS 385:"
            )
            for i, conv in enumerate(ids385_conversations):
                print(f"\nConversation {i + 1}/{len(ids385_conversations)}:")
                print(f"- Subject: {getattr(conv, 'subject', 'No subject')}")
                print(f"- Context: {getattr(conv, 'context_name', 'Unknown')}")
                print(
                    f"- Last message: {format_datetime(getattr(conv, 'last_message_at', 'Unknown'))}"
                )
                print(f"- Participants: {len(getattr(conv, 'participants', []))}")

                # Try to get messages in this conversation
                try:
                    messages = conv.get_messages()
                    print(f"- Messages: {len(messages)}")
                    for j, msg in enumerate(messages[:3]):  # Show first 3 messages
                        print(
                            f"  Message {j + 1}: from {getattr(msg, 'author_name', 'Unknown')}"
                        )
                        print(
                            f"  Sent: {format_datetime(getattr(msg, 'created_at', 'Unknown'))}"
                        )
                        print(f"  Body: {getattr(msg, 'body', 'No body')[:100]}...")
                    if len(messages) > 3:
                        print(f"  ... and {len(messages) - 3} more messages")
                except Exception as e:
                    print(f"  Error getting messages: {e}")
        except Exception as e:
            print(f"Error checking inbox: {e}")

        # Check course stream
        print("\nChecking course stream...")
        try:
            # Direct API call since canvasapi doesn't have this method
            url = f"{config.API_URL}/courses/{course_id}/activity_stream"
            headers = {"Authorization": f"Bearer {config.API_KEY}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                activities = response.json()
                print(f"Found {len(activities)} activities in course stream")
                for i, activity in enumerate(activities[:5]):  # Show first 5
                    print(f"- Activity {i + 1}: {activity.get('type', 'Unknown type')}")
                    print(f"  Title: {activity.get('title', 'No title')}")
                    print(
                        f"  Created: {format_datetime(activity.get('created_at', 'Unknown'))}"
                    )
                if len(activities) > 5:
                    print(f"  ... and {len(activities) - 5} more activities")
            else:
                print(f"Error: Status code {response.status_code}")
                print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error checking course stream: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
