#!/usr/bin/env python3
"""
Script to directly access Canvas inbox messages using the conversations API endpoint.
This script tries multiple approaches to access inbox messages.
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
    """Main function to access Canvas inbox messages."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get API URL and key
        api_url = config.API_URL
        api_key = config.API_KEY

        print("\nAttempting to access inbox messages using direct API calls:")

        # Approach 1: Direct API call to conversations endpoint
        print("\nApproach 1: Direct API call to conversations endpoint")
        try:
            url = f"{api_url}/api/v1/conversations"
            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                conversations = response.json()
                print(f"Success! Found {len(conversations)} conversations")

                # Print details of first few conversations
                for i, conv in enumerate(conversations[:3]):
                    print(f"\nConversation {i + 1}:")
                    print(f"- ID: {conv.get('id')}")
                    print(f"- Subject: {conv.get('subject', 'No subject')}")
                    print(f"- Context: {conv.get('context_name', 'Unknown')}")
                    print(
                        f"- Last message: {conv.get('last_message', 'No message')[:50]}..."
                    )
                    print(
                        f"- Last message at: {format_datetime(conv.get('last_message_at', 'Unknown'))}"
                    )
                    print(f"- Message count: {conv.get('message_count', 0)}")

                    # Check if this is from IDS 385
                    context_name = conv.get("context_name", "")
                    if "IDS-385" in context_name or "IDS 385" in context_name:
                        print("- From IDS 385: Yes")
                    else:
                        print("- From IDS 385: No")

                if len(conversations) > 3:
                    print(f"\n... and {len(conversations) - 3} more conversations")

                # Count IDS 385 conversations
                ids385_count = sum(
                    1
                    for conv in conversations
                    if "IDS-385" in conv.get("context_name", "")
                    or "IDS 385" in conv.get("context_name", "")
                )
                print(f"\nFound {ids385_count} conversations related to IDS 385")

                # If we found IDS 385 conversations, get details for one
                if ids385_count > 0:
                    ids385_conv = next(
                        (
                            conv
                            for conv in conversations
                            if "IDS-385" in conv.get("context_name", "")
                            or "IDS 385" in conv.get("context_name", "")
                        ),
                        None,
                    )
                    if ids385_conv:
                        conv_id = ids385_conv.get("id")
                        print(
                            f"\nGetting details for IDS 385 conversation (ID: {conv_id}):"
                        )

                        detail_url = f"{api_url}/api/v1/conversations/{conv_id}"
                        detail_response = requests.get(detail_url, headers=headers)
                        if detail_response.status_code == 200:
                            conv_detail = detail_response.json()
                            messages = conv_detail.get("messages", [])
                            print(
                                f"Found {len(messages)} messages in this conversation"
                            )

                            for j, msg in enumerate(messages[:3]):
                                print(f"\nMessage {j + 1}:")
                                print(f"- ID: {msg.get('id')}")
                                print(f"- Author: {msg.get('author_id')}")
                                print(
                                    f"- Created at: {format_datetime(msg.get('created_at', 'Unknown'))}"
                                )
                                print(f"- Body: {msg.get('body', 'No body')[:100]}...")

                                # Check if this is from an instructor
                                if (
                                    msg.get("author_id") == 65920000000013682
                                ):  # Instructor ID from previous script
                                    print("- From instructor: Yes")
                                else:
                                    print("- From instructor: No")

                            if len(messages) > 3:
                                print(f"\n... and {len(messages) - 3} more messages")
                        else:
                            print(
                                f"Error getting conversation details: {detail_response.status_code}"
                            )
                            print(f"Response: {detail_response.text[:100]}...")
            else:
                print(f"Error: Status code {response.status_code}")
                print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error with direct API call: {e}")

        # Approach 2: Try using the Canvas API client's user object
        print("\nApproach 2: Using Canvas API client's user object")
        try:
            # Try to access the user's conversations
            print("Checking available methods on user object:")
            user_methods = [
                method
                for method in dir(user)
                if not method.startswith("_") and callable(getattr(user, method))
            ]
            print(f"Available methods: {', '.join(user_methods)}")

            # Check if there's a method related to conversations or inbox
            conversation_methods = [
                method
                for method in user_methods
                if "conversation" in method.lower()
                or "message" in method.lower()
                or "inbox" in method.lower()
            ]
            if conversation_methods:
                print(
                    f"Found conversation-related methods: {', '.join(conversation_methods)}"
                )

                # Try each method
                for method_name in conversation_methods:
                    try:
                        method = getattr(user, method_name)
                        print(f"\nTrying method: {method_name}")
                        result = method()
                        print(f"Success! Result type: {type(result)}")

                        # If it's a list or PaginatedList, print the first few items
                        if hasattr(result, "__iter__"):
                            items = list(result)
                            print(f"Found {len(items)} items")
                            for i, item in enumerate(items[:3]):
                                print(f"- Item {i + 1}: {item}")
                            if len(items) > 3:
                                print(f"... and {len(items) - 3} more items")
                    except Exception as e:
                        print(f"Error with method {method_name}: {e}")
            else:
                print("No conversation-related methods found")
        except Exception as e:
            print(f"Error with Canvas API client approach: {e}")

        # Approach 3: Try using the Canvas API client directly
        print("\nApproach 3: Using Canvas API client directly")
        try:
            # Check if the Canvas API client has a method for conversations
            canvas_methods = [
                method
                for method in dir(canvas_api_client)
                if not method.startswith("_")
                and callable(getattr(canvas_api_client, method))
            ]
            conversation_methods = [
                method
                for method in canvas_methods
                if "conversation" in method.lower()
                or "message" in method.lower()
                or "inbox" in method.lower()
            ]

            if conversation_methods:
                print(
                    f"Found conversation-related methods: {', '.join(conversation_methods)}"
                )

                # Try each method
                for method_name in conversation_methods:
                    try:
                        method = getattr(canvas_api_client, method_name)
                        print(f"\nTrying method: {method_name}")
                        result = method()
                        print(f"Success! Result type: {type(result)}")

                        # If it's a list or PaginatedList, print the first few items
                        if hasattr(result, "__iter__"):
                            items = list(result)
                            print(f"Found {len(items)} items")
                            for i, item in enumerate(items[:3]):
                                print(f"- Item {i + 1}: {item}")
                            if len(items) > 3:
                                print(f"... and {len(items) - 3} more items")
                    except Exception as e:
                        print(f"Error with method {method_name}: {e}")
            else:
                print("No conversation-related methods found")
        except Exception as e:
            print(f"Error with Canvas API client direct approach: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
