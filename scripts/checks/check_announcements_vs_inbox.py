#!/usr/bin/env python3
"""
Script to check if Canvas inbox messages include announcements.
This script will:
1. Get all announcements from a course
2. Get all inbox messages/conversations
3. Compare to see if announcements appear in the inbox
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
    """Main function to check if announcements appear in inbox."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get IDS 385 course (the one with missing announcements)
        course_id = 65920000000145100  # IDS 385
        print(f"\nChecking course ID: {course_id}")

        course = canvas_api_client.get_course(course_id)
        print(f"Course: {course.name} ({course.course_code})")

        # Get announcements via the API
        print(
            "\n1. Checking announcements via get_discussion_topics(only_announcements=True):"
        )
        try:
            announcements = list(course.get_discussion_topics(only_announcements=True))
            print(f"Found {len(announcements)} announcements")
            for i, a in enumerate(announcements):
                print(f"- Announcement {i + 1}: {a.title}")
                print(f"  ID: {a.id}")
                print(
                    f"  Posted at: {format_datetime(getattr(a, 'posted_at', 'Unknown'))}"
                )
                print(
                    f"  Author: {getattr(a, 'author', {}).get('display_name', 'Unknown')}"
                )
        except Exception as e:
            print(f"Error getting announcements: {e}")

        # Try direct API call for announcements
        print("\n2. Checking announcements via direct API call:")
        try:
            import requests

            url = f"{config.API_URL}/courses/{course_id}/announcements"
            headers = {"Authorization": f"Bearer {config.API_KEY}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                direct_announcements = response.json()
                print(f"Found {len(direct_announcements)} announcements via direct API")
                for i, a in enumerate(direct_announcements[:3]):
                    print(f"- Announcement {i + 1}: {a.get('title', 'No title')}")
                    print(f"  ID: {a.get('id', 'No ID')}")
                    print(
                        f"  Posted at: {format_datetime(a.get('posted_at', 'Unknown'))}"
                    )
                    print(f"  Author: {a.get('user_name', 'Unknown')}")
                if len(direct_announcements) > 3:
                    print(f"  ... and {len(direct_announcements) - 3} more")
            else:
                print(f"Error: Status code {response.status_code}")
                print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error with direct API call: {e}")

        # Get inbox conversations
        print("\n3. Checking inbox conversations:")
        try:
            # Direct API call for conversations
            url = f"{config.API_URL}/conversations"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                conversations = response.json()
                print(f"Found {len(conversations)} conversations in inbox")

                # Filter for IDS 385 conversations
                ids385_conversations = []
                for conv in conversations:
                    context_name = conv.get("context_name", "")
                    if "IDS-385" in context_name or "IDS 385" in context_name:
                        ids385_conversations.append(conv)

                print(
                    f"Found {len(ids385_conversations)} conversations related to IDS 385:"
                )
                for i, conv in enumerate(ids385_conversations[:5]):
                    print(f"\nConversation {i + 1}/{len(ids385_conversations)}:")
                    print(f"- Subject: {conv.get('subject', 'No subject')}")
                    print(f"- Context: {conv.get('context_name', 'Unknown')}")
                    print(f"- Last message: {conv.get('last_message', 'No message')}")
                    print(
                        f"- Last message at: {format_datetime(conv.get('last_message_at', 'Unknown'))}"
                    )

                    # Get messages for this conversation
                    conv_id = conv.get("id")
                    if conv_id:
                        msg_url = f"{config.API_URL}/conversations/{conv_id}"
                        msg_response = requests.get(msg_url, headers=headers)
                        if msg_response.status_code == 200:
                            conv_detail = msg_response.json()
                            messages = conv_detail.get("messages", [])
                            print(f"- Messages: {len(messages)}")
                            for j, msg in enumerate(messages[:2]):
                                print(
                                    f"  Message {j + 1}: from {msg.get('author_id', 'Unknown')}"
                                )
                                print(f"  Body: {msg.get('body', 'No body')[:100]}...")
                            if len(messages) > 2:
                                print(f"  ... and {len(messages) - 2} more messages")
                        else:
                            print(
                                f"- Error getting messages: {msg_response.status_code}"
                            )
                if len(ids385_conversations) > 5:
                    print(
                        f"\n... and {len(ids385_conversations) - 5} more conversations"
                    )
            else:
                print(f"Error: Status code {response.status_code}")
                print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error checking inbox: {e}")

        # Check for instructor messages
        print("\n4. Checking for instructor messages:")
        try:
            # Get course users
            instructors = []
            for enrollment in course.get_enrollments():
                if hasattr(enrollment, "type") and "teacher" in enrollment.type.lower():
                    instructors.append(enrollment.user_id)

            print(f"Found {len(instructors)} instructors: {instructors}")

            # Check for messages from instructors
            instructor_messages = []
            for conv in conversations:
                participants = conv.get("participants", [])
                for participant in participants:
                    if participant.get("id") in instructors:
                        instructor_messages.append(conv)
                        break

            print(f"Found {len(instructor_messages)} conversations from instructors:")
            for i, conv in enumerate(instructor_messages[:3]):
                print(f"- Subject: {conv.get('subject', 'No subject')}")
                print(f"- Context: {conv.get('context_name', 'Unknown')}")
                print(
                    f"- Last message: {conv.get('last_message', 'No message')[:50]}..."
                )
            if len(instructor_messages) > 3:
                print(f"... and {len(instructor_messages) - 3} more")
        except Exception as e:
            print(f"Error checking instructor messages: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
