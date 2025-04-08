#!/usr/bin/env python3
"""
Script to check if Canvas conversations include messages from all courses.
This script will analyze conversations by course to determine if get_conversations()
is a superset of all course communications.
"""

import datetime
import sys
from collections import defaultdict
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
    """Main function to check conversations by course."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get active courses
        print("\nFetching active courses...")
        courses = list(user.get_courses(enrollment_state="active"))
        print(f"Found {len(courses)} active courses:")
        for i, course in enumerate(courses):
            print(f"{i + 1}. {course.name} (ID: {course.id})")

        # Get conversations
        print("\nFetching conversations...")
        conversations = list(canvas_api_client.get_conversations())
        print(f"Found {len(conversations)} total conversations")

        # Group conversations by course
        course_conversations = defaultdict(list)
        course_names = {}

        for conv in conversations:
            context_name = getattr(conv, "context_name", "Unknown")
            course_conversations[context_name].append(conv)

            # Store course names for later reference
            for course in courses:
                if course.name in context_name:
                    course_names[context_name] = course.id

        # Print conversations by course
        print("\nConversations by course:")
        for context, convs in sorted(
            course_conversations.items(), key=lambda x: len(x[1]), reverse=True
        ):
            course_id = course_names.get(context, "Unknown")
            print(f"\n{context} (ID: {course_id}): {len(convs)} conversations")

            # Print first 3 conversations for this course
            for i, conv in enumerate(convs[:3]):
                print(
                    f"  {i + 1}. {getattr(conv, 'subject', 'No subject')} ({format_datetime(getattr(conv, 'last_message_at', 'Unknown'))})"
                )

                # Print a snippet of the last message
                last_message = getattr(conv, "last_message", "")
                if last_message:
                    if len(last_message) > 50:
                        last_message = last_message[:50] + "..."
                    print(f"     Last message: {last_message}")

            if len(convs) > 3:
                print(f"     ... and {len(convs) - 3} more conversations")

        # Check for conversations without a course context
        no_context = [
            conv
            for conv in conversations
            if not hasattr(conv, "context_name") or not conv.context_name
        ]
        if no_context:
            print(f"\nConversations without a course context: {len(no_context)}")
            for i, conv in enumerate(no_context[:3]):
                print(
                    f"  {i + 1}. {getattr(conv, 'subject', 'No subject')} ({format_datetime(getattr(conv, 'last_message_at', 'Unknown'))})"
                )
            if len(no_context) > 3:
                print(f"     ... and {len(no_context) - 3} more conversations")

        # Compare with announcements
        print("\nComparing with announcements:")
        for course in courses[:3]:  # Check first 3 courses
            print(f"\nCourse: {course.name} (ID: {course.id})")

            # Get announcements for this course
            try:
                announcements = list(
                    course.get_discussion_topics(only_announcements=True)
                )
                print(f"  Announcements: {len(announcements)}")

                # Get conversations for this course
                course_convs = []
                for context, convs in course_conversations.items():
                    if course.name in context:
                        course_convs.extend(convs)

                print(f"  Conversations: {len(course_convs)}")

                # Check if there's overlap
                if announcements and course_convs:
                    print("  Checking for overlap...")

                    # Get announcement titles
                    announcement_titles = [
                        getattr(a, "title", "") for a in announcements
                    ]

                    # Check if any conversation subjects match announcement titles
                    matches = []
                    for conv in course_convs:
                        subject = getattr(conv, "subject", "")
                        if subject in announcement_titles:
                            matches.append(subject)

                    if matches:
                        print(f"  Found {len(matches)} overlapping titles:")
                        for match in matches[:3]:
                            print(f"    - {match}")
                        if len(matches) > 3:
                            print(f"      ... and {len(matches) - 3} more")
                    else:
                        print("  No overlapping titles found")
            except Exception as e:
                print(f"  Error getting announcements: {e}")

        # Summary
        print("\nSummary:")
        print(f"- Total courses: {len(courses)}")
        print(f"- Total conversations: {len(conversations)}")
        print(f"- Courses with conversations: {len(course_conversations)}")

        # Check if all courses have conversations
        courses_with_convs = set()
        for context in course_conversations.keys():
            for course in courses:
                if course.name in context:
                    courses_with_convs.add(course.id)

        print(
            f"- Courses with at least one conversation: {len(courses_with_convs)}/{len(courses)}"
        )

        if len(courses_with_convs) < len(courses):
            print("\nCourses without conversations:")
            for course in courses:
                if course.id not in courses_with_convs:
                    print(f"  - {course.name} (ID: {course.id})")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
