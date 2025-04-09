"""
Canvas Conversations Sync

This module provides functionality for synchronizing conversation data between
the Canvas API and the local database.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

from canvas_mcp.models import DBConversation

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SYNC_DAYS = 21


def sync_conversations(sync_service, sync_days: int = DEFAULT_SYNC_DAYS) -> int:
    """
    Synchronize conversation data from Canvas to the local database.

    Args:
        sync_service: The sync service instance.
        sync_days: Number of past days to sync conversations from.

    Returns:
        Number of conversations synced
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return 0

    # Calculate the cutoff date
    term_start_date = datetime.now(UTC) - timedelta(days=sync_days)
    logger.info(f"Using cutoff date: {term_start_date}")

    # Get courses to sync
    conn, cursor = sync_service.db_manager.connect()
    try:
        cursor.execute("SELECT * FROM courses")
        courses_to_sync = [dict(row) for row in cursor.fetchall()]
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting courses to sync: {e}")
        return 0
    finally:
        conn.close()

    if not courses_to_sync:
        logger.warning("No courses found to sync conversations")
        return 0

    # Create a mapping of course names to local IDs
    course_name_to_id = {
        course["course_name"]: course["id"] for course in courses_to_sync
    }

    # Fetch all conversations
    logger.info("Fetching conversations from Canvas API")
    raw_conversations = sync_service.api_adapter.get_conversations_raw()
    if not raw_conversations:
        logger.info("No conversations found")
        return 0

    logger.info(f"Found {len(raw_conversations)} conversations from Canvas API")

    # Process conversations
    conversation_count = 0
    processed_conversations = set()  # Track processed conversations to avoid duplicates

    for raw_conv in raw_conversations:
        try:
            # Skip if no context_name (not course-related)
            context_name = getattr(raw_conv, "context_name", None)
            if not context_name:
                continue

            # Find matching course
            matching_course_id = None
            for course_name, local_id in course_name_to_id.items():
                if course_name in context_name:
                    matching_course_id = local_id
                    break

            if not matching_course_id:
                continue  # Skip if no matching course

            # Get conversation ID
            conv_id = getattr(raw_conv, "id", None)
            if not conv_id or conv_id in processed_conversations:
                continue  # Skip if no ID or already processed

            # Get conversation details to get the message
            logger.info(f"Fetching details for conversation {conv_id}")
            conv_detail = sync_service.api_adapter.get_conversation_detail_raw(conv_id)
            if (
                not conv_detail
                or not hasattr(conv_detail, "messages")
                or not conv_detail.messages
            ):
                logger.warning(f"No valid messages found for conversation {conv_id}")
                continue

            # Get the most recent message
            message = conv_detail.messages[0]

            # Get message timestamp (last_message_at is the most reliable source)
            message_created_at = None

            # Try conversation-level timestamp first (most reliable)
            if hasattr(raw_conv, "last_message_at") and raw_conv.last_message_at:
                try:
                    message_created_at = datetime.fromisoformat(
                        raw_conv.last_message_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # If that fails, try message-level timestamp
            if (
                not message_created_at
                and hasattr(message, "created_at")
                and message.created_at
            ):
                try:
                    message_created_at = datetime.fromisoformat(
                        message.created_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            # If we still don't have a timestamp, use current time
            if not message_created_at:
                message_created_at = datetime.now(UTC)
                logger.warning(
                    f"Using current time for conversation {conv_id} as fallback"
                )

            # Skip if message is older than term start date
            if message_created_at < term_start_date:
                logger.info(
                    f"Skipping conversation {conv_id} - message date {message_created_at} is older than cutoff"
                )
                continue

            # Get message body
            message_body = None

            # Try to get body from message
            # Handle both dictionary and object cases
            if isinstance(message, dict) and "body" in message:
                message_body = message["body"]
            elif hasattr(message, "body") and message.body:
                message_body = message.body
            # Fallback to last_message on the conversation
            elif hasattr(raw_conv, "last_message") and raw_conv.last_message:
                message_body = raw_conv.last_message

            # If we still don't have a message body, use a default
            if not message_body:
                message_body = "[No message content available]"
                logger.warning(
                    f"No message body found for conversation {conv_id}, using default"
                )

            # Clean up HTML if present
            if "<" in message_body and ">" in message_body:
                try:
                    # Simple regex approach to clean HTML
                    cleaned_body = re.sub(r"<[^>]+>", " ", message_body)
                    cleaned_body = re.sub(r"\s+", " ", cleaned_body).strip()
                    message_body = cleaned_body
                except Exception as e:
                    logger.warning(f"Error cleaning HTML from message: {e}")

            # Get author name from participants
            author_name = "Instructor"  # Default
            author_id = getattr(message, "author_id", None)

            if hasattr(conv_detail, "participants"):
                # Handle both list of dicts and list of objects
                if conv_detail.participants and isinstance(
                    conv_detail.participants[0], dict
                ):
                    # If we have participants as dicts, use the first one's name
                    if "name" in conv_detail.participants[0]:
                        author_name = conv_detail.participants[0]["name"]
                # Otherwise try to match by author_id if available
                elif author_id:
                    for participant in conv_detail.participants:
                        if getattr(participant, "id", None) == author_id:
                            author_name = getattr(participant, "name", author_name)
                            break

            # Ensure message_created_at has timezone
            if not message_created_at.tzinfo:
                message_created_at = message_created_at.replace(tzinfo=UTC)

            # Prepare conversation data
            conversation_data = {
                "id": conv_id,
                "course_id": matching_course_id,
                "title": getattr(raw_conv, "subject", "No Subject"),
                "content": message_body,
                "posted_by": author_name,
                "posted_at": message_created_at.isoformat(),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # Validate using Pydantic model
            db_conversation = DBConversation.model_validate(conversation_data)

            # Persist conversation
            conn, cursor = sync_service.db_manager.connect()
            try:
                # Convert Pydantic model to dict
                conversation_dict = db_conversation.model_dump(
                    exclude={"created_at", "updated_at"}
                )
                conversation_dict["updated_at"] = datetime.now().isoformat()

                # Check if conversation exists
                cursor.execute(
                    "SELECT id FROM conversations WHERE canvas_conversation_id = ?",
                    (db_conversation.canvas_conversation_id,),
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing conversation
                    conversation_id = existing["id"]
                    placeholders = ", ".join(
                        [f"{k} = ?" for k in conversation_dict.keys()]
                    )
                    values = list(conversation_dict.values())

                    cursor.execute(
                        f"UPDATE conversations SET {placeholders} WHERE id = ?",
                        values + [conversation_id],
                    )
                else:
                    # Insert new conversation
                    columns = ", ".join(conversation_dict.keys())
                    placeholders = ", ".join(["?" for _ in conversation_dict.keys()])

                    cursor.execute(
                        f"INSERT INTO conversations ({columns}) VALUES ({placeholders})",
                        list(conversation_dict.values()),
                    )

                conn.commit()
                conversation_count += 1
                processed_conversations.add(conv_id)  # Mark as processed

            except Exception as e:
                conn.rollback()
                logger.error(f"Error persisting conversation {conv_id}: {e}")
            finally:
                conn.close()

        except Exception as e:
            logger.error(
                f"Error processing conversation {getattr(raw_conv, 'id', 'N/A')}: {e}"
            )
            continue

    logger.info(f"Successfully synced {conversation_count} conversations")
    return conversation_count
