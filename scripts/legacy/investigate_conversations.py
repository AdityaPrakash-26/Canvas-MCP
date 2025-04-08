#!/usr/bin/env python3
"""
Script to investigate the structure of Canvas conversations.
This script will examine what get_conversations() returns in detail.
"""

import datetime
import pprint
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


def inspect_object(obj, prefix=""):
    """Inspect an object and print its attributes."""
    print(f"{prefix}Type: {type(obj).__name__}")

    if hasattr(obj, "__dict__"):
        attrs = vars(obj)
        print(f"{prefix}Attributes:")
        for key, value in attrs.items():
            if not key.startswith("_"):
                if isinstance(value, str | int | float | bool | type(None)):
                    print(f"{prefix}  {key}: {value}")
                elif isinstance(value, list | tuple):
                    print(
                        f"{prefix}  {key}: {type(value).__name__} with {len(value)} items"
                    )
                else:
                    print(f"{prefix}  {key}: {type(value).__name__}")

    # Check for methods
    methods = [
        method
        for method in dir(obj)
        if not method.startswith("_") and callable(getattr(obj, method))
    ]
    if methods:
        print(f"{prefix}Methods: {', '.join(methods)}")


def main():
    """Main function to investigate Canvas conversations."""
    try:
        # Initialize Canvas API
        from canvasapi import Canvas

        canvas_api_client = Canvas(config.API_URL, config.API_KEY)

        # Get user
        user = canvas_api_client.get_current_user()
        print(f"Current user: {user.name} (ID: {user.id})")

        # Get conversations
        print("\nFetching conversations...")
        conversations = canvas_api_client.get_conversations()

        # Convert PaginatedList to regular list
        conversations_list = list(conversations)
        print(f"Found {len(conversations_list)} conversations")

        # Examine the first conversation in detail
        if conversations_list:
            print("\n=== EXAMINING FIRST CONVERSATION ===")
            first_conv = conversations_list[0]
            inspect_object(first_conv)

            # Try to convert to dict for better inspection
            try:
                conv_dict = first_conv.__dict__
                print("\nConversation as dictionary:")
                pprint.pprint(conv_dict, indent=2, width=100)
            except Exception as e:
                print(f"Error converting to dict: {e}")

            # Try to access specific attributes
            print("\nAccessing specific attributes:")
            important_attrs = [
                "id",
                "subject",
                "workflow_state",
                "last_message",
                "last_message_at",
                "message_count",
                "subscribed",
                "private",
                "starred",
                "properties",
                "audience",
                "audience_contexts",
                "avatar_url",
                "participants",
                "visible",
                "context_name",
            ]

            for attr in important_attrs:
                try:
                    value = getattr(first_conv, attr, "Not available")
                    print(f"- {attr}: {value}")
                except Exception as e:
                    print(f"- {attr}: Error: {e}")

            # Try to get messages
            print("\nTrying to get messages for this conversation:")
            try:
                # Try different approaches

                # Approach 1: Check if there's a get_messages method
                if hasattr(first_conv, "get_messages") and callable(
                    first_conv.get_messages
                ):
                    print("Using get_messages() method:")
                    messages = first_conv.get_messages()
                    print(f"Found {len(messages)} messages")

                    # Examine the first message
                    if messages:
                        first_msg = messages[0]
                        print("\nFirst message:")
                        inspect_object(first_msg, prefix="  ")
                else:
                    print("No get_messages() method available")

                # Approach 2: Get conversation details using the API
                print("\nUsing get_conversation() method:")
                conv_id = getattr(first_conv, "id", None)
                if conv_id:
                    conv_detail = canvas_api_client.get_conversation(conv_id)
                    print("Conversation details:")
                    inspect_object(conv_detail, prefix="  ")

                    # Check if messages are in the details
                    if hasattr(conv_detail, "messages"):
                        messages = conv_detail.messages
                        print(f"Found {len(messages)} messages in details")

                        # Examine the first message
                        if messages:
                            first_msg = messages[0]
                            print("\nFirst message from details:")
                            inspect_object(first_msg, prefix="  ")
                else:
                    print("No conversation ID available")

                # Approach 3: Direct API call
                print("\nUsing direct API call:")
                import requests

                if conv_id:
                    url = f"{config.API_URL}/api/v1/conversations/{conv_id}"
                    headers = {"Authorization": f"Bearer {config.API_KEY}"}

                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        conv_data = response.json()
                        print("Conversation data structure:")
                        pprint.pprint(conv_data, indent=2, width=100)

                        # Check for messages
                        messages = conv_data.get("messages", [])
                        print(f"Found {len(messages)} messages in API response")

                        # Examine the first message
                        if messages:
                            first_msg = messages[0]
                            print("\nFirst message structure:")
                            pprint.pprint(first_msg, indent=2, width=100)
                    else:
                        print(f"Error: Status code {response.status_code}")
                        print(f"Response: {response.text[:100]}...")
                else:
                    print("No conversation ID available")
            except Exception as e:
                print(f"Error getting messages: {e}")

            # Find an IDS 385 conversation
            print("\n=== FINDING IDS 385 CONVERSATION ===")
            ids385_conv = None
            for conv in conversations_list:
                context_name = getattr(conv, "context_name", "")
                if "IDS-385" in context_name or "IDS 385" in context_name:
                    ids385_conv = conv
                    break

            if ids385_conv:
                print(
                    f"Found IDS 385 conversation: {getattr(ids385_conv, 'subject', 'No subject')}"
                )

                # Get full details for this conversation
                conv_id = getattr(ids385_conv, "id", None)
                if conv_id:
                    print("\nGetting full details for IDS 385 conversation:")
                    url = f"{config.API_URL}/api/v1/conversations/{conv_id}"
                    headers = {"Authorization": f"Bearer {config.API_KEY}"}

                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        conv_data = response.json()

                        # Extract key information
                        print("\nKey information:")
                        print(f"- Subject: {conv_data.get('subject', 'No subject')}")
                        print(f"- Context: {conv_data.get('context_name', 'Unknown')}")
                        print(
                            f"- Workflow state: {conv_data.get('workflow_state', 'Unknown')}"
                        )
                        print(f"- Message count: {conv_data.get('message_count', 0)}")

                        # Check participants
                        participants = conv_data.get("participants", [])
                        print(f"\nParticipants ({len(participants)}):")
                        for p in participants:
                            print(
                                f"- {p.get('name', 'Unknown')} (ID: {p.get('id', 'Unknown')})"
                            )

                        # Check messages
                        messages = conv_data.get("messages", [])
                        print(f"\nMessages ({len(messages)}):")
                        for i, msg in enumerate(messages):
                            print(f"\nMessage {i + 1}:")
                            print(f"- ID: {msg.get('id', 'Unknown')}")
                            print(
                                f"- Created at: {format_datetime(msg.get('created_at', 'Unknown'))}"
                            )
                            print(f"- Author ID: {msg.get('author_id', 'Unknown')}")
                            print(f"- Generated: {msg.get('generated', False)}")

                            # Get body (truncated if long)
                            body = msg.get("body", "No body")
                            if len(body) > 100:
                                body = body[:100] + "..."
                            print(f"- Body: {body}")

                            # Check for attachments
                            attachments = msg.get("attachments", [])
                            if attachments:
                                print(f"- Attachments ({len(attachments)}):")
                                for a in attachments:
                                    print(
                                        f"  - {a.get('display_name', 'Unknown')} ({a.get('content-type', 'Unknown')})"
                                    )

                            # Check for media comments
                            media = msg.get("media_comment")
                            if media:
                                print(
                                    f"- Media comment: {media.get('display_name', 'Unknown')} ({media.get('media_type', 'Unknown')})"
                                )

                            # Check for forwarded messages
                            forwarded = msg.get("forwarded_messages", [])
                            if forwarded:
                                print(f"- Forwarded messages: {len(forwarded)}")
                    else:
                        print(f"Error: Status code {response.status_code}")
                        print(f"Response: {response.text[:100]}...")
            else:
                print("No IDS 385 conversation found")
        else:
            print("No conversations found")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
