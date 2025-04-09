#!/usr/bin/env python3
"""
Script to verify if conversation content is available in the Canvas API.
This script will:
1. Connect directly to the Canvas API
2. Fetch specific conversations that have empty content in our database
3. Check if the content is available in the API response
"""

import datetime
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Canvas MCP components
from canvasapi import Canvas

import canvas_mcp.config as config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("verify_conversation_content")


def main():
    """Main function to verify conversation content."""
    try:
        # Initialize Canvas API directly
        logger.info(f"Connecting to Canvas API at {config.API_URL}")
        canvas = Canvas(config.API_URL, config.API_KEY)

        # Get current user
        user = canvas.get_current_user()
        logger.info(f"Connected as user: {user.name} (ID: {user.id})")

        # List of conversation IDs to check (from our database)
        # These are the Canvas conversation IDs, not our local database IDs
        conversation_ids = [
            65920000002016475,  # ID 32: For tomorrow's class...
            65920000002015848,  # ID 33: Reminder for class Monday
            65920000002013652,  # ID 34: Class Tomorrow
            65920000002013339,  # ID 35: Class Tomorrow
            65920000002009621,  # ID 36: Class Today - Please read!
            65920000002052243,  # ID 1: Final Project Instructions (has content in our DB)
        ]

        for canvas_conv_id in conversation_ids:
            logger.info(f"\nChecking conversation ID: {canvas_conv_id}")

            try:
                # Fetch the conversation directly from Canvas API
                conversation = canvas.get_conversation(canvas_conv_id)

                # Log basic info
                logger.info(
                    f"Subject: {getattr(conversation, 'subject', 'No subject')}"
                )
                logger.info(
                    f"Workflow state: {getattr(conversation, 'workflow_state', 'Unknown')}"
                )

                # Check date fields
                date_fields = [
                    "created_at",
                    "last_message_at",
                    "last_authored_message_at",
                ]
                for field in date_fields:
                    if hasattr(conversation, field):
                        value = getattr(conversation, field)
                        logger.info(
                            f"Date field {field}: {value} (type: {type(value)})"
                        )

                        # Try to parse the date
                        if isinstance(value, str):
                            try:
                                parsed_date = datetime.datetime.fromisoformat(
                                    value.replace("Z", "+00:00")
                                )
                                logger.info(
                                    f"Parsed date: {parsed_date} (type: {type(parsed_date)})"
                                )
                            except ValueError as e:
                                logger.error(f"Error parsing date: {e}")

                # Check if messages attribute exists
                if not hasattr(conversation, "messages"):
                    logger.error("Conversation has no messages attribute")
                    continue

                # Check if messages list is empty
                if not conversation.messages:
                    logger.error("Conversation has empty messages list")
                    continue

                # Log message count
                logger.info(f"Found {len(conversation.messages)} messages")

                # Examine the first message
                message = conversation.messages[0]
                logger.info(f"First message attributes: {dir(message)}")

                # Check message date fields
                msg_date_fields = ["created_at", "sent_at"]
                for field in msg_date_fields:
                    if hasattr(message, field):
                        value = getattr(message, field)
                        logger.info(
                            f"Message date field {field}: {value} (type: {type(value)})"
                        )

                        # Try to parse the date
                        if isinstance(value, str):
                            try:
                                parsed_date = datetime.datetime.fromisoformat(
                                    value.replace("Z", "+00:00")
                                )
                                logger.info(
                                    f"Parsed message date: {parsed_date} (type: {type(parsed_date)})"
                                )
                            except ValueError as e:
                                logger.error(f"Error parsing message date: {e}")

                # Try to extract body from different sources
                body_sources = [
                    (
                        "message['body']",
                        message.get("body", None)
                        if isinstance(message, dict)
                        else None,
                    ),
                    (
                        "message['message']",
                        message.get("message", None)
                        if isinstance(message, dict)
                        else None,
                    ),
                    (
                        "message.body",
                        getattr(message, "body", None)
                        if not isinstance(message, dict)
                        else None,
                    ),
                    (
                        "message.message",
                        getattr(message, "message", None)
                        if not isinstance(message, dict)
                        else None,
                    ),
                    (
                        "conversation.last_message",
                        getattr(conversation, "last_message", None),
                    ),
                    (
                        "message.text",
                        getattr(message, "text", None)
                        if not isinstance(message, dict)
                        else None,
                    ),
                ]

                # Log all possible body sources
                content_found = False
                for source_name, source_value in body_sources:
                    if source_value:
                        content_found = True
                        logger.info(
                            f"Content found in {source_name}: {source_value[:100]}..."
                        )

                if not content_found:
                    logger.warning("No content found in any source")

                # Check participants
                if hasattr(conversation, "participants"):
                    logger.info(f"Participants: {len(conversation.participants)}")

                    # Try to find the author
                    author_id = getattr(message, "author_id", None)
                    if author_id:
                        logger.info(f"Author ID: {author_id}")
                        for participant in conversation.participants:
                            if getattr(participant, "id", None) == author_id:
                                logger.info(
                                    f"Author: {getattr(participant, 'name', None)}"
                                )
                                break

            except Exception as e:
                logger.error(f"Error fetching conversation {canvas_conv_id}: {e}")

    except Exception as e:
        logger.exception(f"Error verifying conversation content: {e}")


if __name__ == "__main__":
    main()
