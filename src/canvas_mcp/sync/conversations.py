"""
Canvas Conversations Sync

This module provides functionality for synchronizing conversation data between
the Canvas API and the local database.
"""

import logging
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

    # Fetch Stage
    logger.info("Fetching conversations from Canvas API...")

    # Get courses to sync
    conn, cursor = sync_service.db_manager.connect()
    try:
        # Get all courses
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
    course_name_to_id = {}
    for course in courses_to_sync:
        course_name_to_id[course["course_name"]] = course["id"]

    # Fetch all conversations
    logger.info("Fetching conversations from Canvas API")
    raw_conversations = sync_service.api_adapter.get_conversations_raw()
    if not raw_conversations:
        logger.info("No conversations found")
        return 0

    logger.info(f"Found {len(raw_conversations)} conversations from Canvas API")
    # Log a sample conversation to debug
    if raw_conversations:
        sample_conv = raw_conversations[0]
        logger.info(
            f"Sample conversation: ID={getattr(sample_conv, 'id', 'Unknown')}, Subject={getattr(sample_conv, 'subject', 'Unknown')}"
        )
        logger.info(f"Sample conversation attributes: {dir(sample_conv)}")

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
            if not conv_detail:
                logger.warning(f"No details found for conversation {conv_id}")
                continue

            if not hasattr(conv_detail, "messages"):
                logger.warning(f"Conversation {conv_id} has no messages attribute")
                logger.info(f"Conversation detail attributes: {dir(conv_detail)}")
                continue

            if not conv_detail.messages:
                logger.warning(f"Conversation {conv_id} has empty messages list")
                continue

            logger.info(
                f"Found {len(conv_detail.messages)} messages for conversation {conv_id}"
            )

            # Get the most recent message
            message = conv_detail.messages[0]
            logger.info(f"Processing message: {getattr(message, 'id', 'Unknown')}")
            logger.info(f"Message attributes: {dir(message)}")

            # Parse the created_at timestamp
            message_created_at_str = getattr(message, "created_at", None)
            logger.info(
                f"Raw message timestamp: {message_created_at_str} (type: {type(message_created_at_str)})"
            )
            message_created_at = None

            # Try to get the 'created_at' attribute from different places
            # Handle both object attributes and dictionary keys
            timestamp_sources = [
                (
                    "message['created_at']",
                    message.get("created_at", None)
                    if isinstance(message, dict)
                    else None,
                ),
                (
                    "message['created_date']",
                    message.get("created_date", None)
                    if isinstance(message, dict)
                    else None,
                ),
                (
                    "message.created_at",
                    getattr(message, "created_at", None)
                    if not isinstance(message, dict)
                    else None,
                ),
                (
                    "message.created_date",
                    getattr(message, "created_date", None)
                    if not isinstance(message, dict)
                    else None,
                ),
                (
                    "raw_conv.last_message_at",
                    getattr(raw_conv, "last_message_at", None),
                ),
                (
                    "raw_conv.last_authored_message_at",
                    getattr(raw_conv, "last_authored_message_at", None),
                ),
            ]

            # Log all possible timestamp sources
            for source_name, source_value in timestamp_sources:
                logger.info(
                    f"Timestamp source {source_name}: {source_value} (type: {type(source_value)})"
                )

            # Try each source until we find a valid timestamp
            for source_name, source_value in timestamp_sources:
                if source_value:
                    try:
                        if isinstance(source_value, str):
                            # Try ISO format first
                            try:
                                message_created_at = datetime.fromisoformat(
                                    source_value.replace("Z", "+00:00")
                                )
                                logger.info(
                                    f"Successfully parsed timestamp from {source_name}: {message_created_at}"
                                )
                                break
                            except ValueError:
                                # Try other common formats
                                try:
                                    import dateutil.parser

                                    message_created_at = dateutil.parser.parse(
                                        source_value
                                    )
                                    logger.info(
                                        f"Successfully parsed timestamp from {source_name} using dateutil: {message_created_at}"
                                    )
                                    break
                                except ImportError:
                                    # Fallback if dateutil is not available
                                    for fmt in [
                                        "%Y-%m-%dT%H:%M:%S",
                                        "%Y-%m-%d %H:%M:%S",
                                    ]:
                                        try:
                                            message_created_at = datetime.strptime(
                                                source_value, fmt
                                            )
                                            logger.info(
                                                f"Successfully parsed timestamp from {source_name} using format {fmt}: {message_created_at}"
                                            )
                                            break
                                        except ValueError:
                                            continue
                        elif isinstance(source_value, datetime):
                            # If it's already a datetime object, use it directly
                            message_created_at = source_value
                            logger.info(
                                f"Using datetime object directly from {source_name}: {message_created_at}"
                            )
                            break
                    except Exception as e:
                        logger.warning(
                            f"Error parsing timestamp from {source_name} ({source_value}): {e}"
                        )

            # If we still don't have a timestamp, use the current time as a last resort
            if not message_created_at:
                logger.warning(
                    "Could not parse any timestamp, using current time as fallback"
                )
                message_created_at = datetime.now()

            logger.info(f"Final timestamp to use: {message_created_at}")

            # Skip if message is older than term start date
            logger.info(
                f"Checking timestamp comparison: message_created_at ({type(message_created_at)}) < term_start_date ({type(term_start_date)})"
            )
            if (
                term_start_date
                and message_created_at
                and message_created_at < term_start_date
            ):
                logger.info(
                    f"Skipping conversation {conv_id} - message date {message_created_at} is older than cutoff {term_start_date}"
                )
                continue

            # Try to get message body from different sources
            # Since message is a dictionary, we need to use get() instead of getattr()
            body_sources = [
                (
                    "message['body']",
                    message.get("body", None) if isinstance(message, dict) else None,
                ),
                (
                    "message['message']",
                    message.get("message", None) if isinstance(message, dict) else None,
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
                ("raw_conv.last_message", getattr(raw_conv, "last_message", None)),
                (
                    "message.text",
                    getattr(message, "text", None)
                    if not isinstance(message, dict)
                    else None,
                ),
            ]

            # Log all possible body sources
            for source_name, source_value in body_sources:
                logger.info(
                    f"Body source {source_name}: {source_value[:100] if source_value else None}"
                )

            # Try each source until we find a valid body
            message_body = None
            for source_name, source_value in body_sources:
                if source_value:
                    message_body = source_value
                    logger.info(f"Using message body from {source_name}")
                    break

            logger.info(
                f"Raw message body: {message_body[:100] if message_body else None}"
            )

            # Clean up HTML if present
            if message_body and "<" in message_body and ">" in message_body:
                try:
                    # Try to import BeautifulSoup
                    try:
                        from bs4 import BeautifulSoup

                        soup = BeautifulSoup(message_body, "html.parser")
                        cleaned_body = soup.get_text(separator=" ", strip=True)
                        logger.info(
                            f"Cleaned HTML with BeautifulSoup: {cleaned_body[:100]}"
                        )
                        message_body = cleaned_body
                    except ImportError:
                        # If BeautifulSoup is not available, use a simple regex approach
                        import re

                        cleaned_body = re.sub(r"<[^>]+>", " ", message_body)
                        cleaned_body = re.sub(r"\s+", " ", cleaned_body).strip()
                        logger.info(f"Cleaned HTML with regex: {cleaned_body[:100]}")
                        message_body = cleaned_body
                except Exception as e:
                    logger.warning(f"Error cleaning HTML from message: {e}")

            # If we still don't have a message body, use a default
            if not message_body:
                logger.warning("No message body found, using default")
                message_body = "[No message content available]"

            # Get author name from participants
            author_id = getattr(message, "author_id", None)
            author_name = None

            if hasattr(conv_detail, "participants"):
                for participant in conv_detail.participants:
                    if getattr(participant, "id", None) == author_id:
                        author_name = getattr(participant, "name", None)
                        break

            # If we couldn't find the author name, use a default
            if not author_name:
                author_name = "Instructor"

            # Prepare data for validation
            conversation_data = {
                "id": conv_id,
                "course_id": matching_course_id,
                "title": getattr(raw_conv, "subject", "No Subject"),
                "content": message_body or "",  # Ensure content is never None
                "posted_by": author_name,
                "posted_at": message_created_at,  # Direct field name, no alias needed
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            logger.info(f"Prepared conversation data: {conversation_data}")
            logger.info(f"Timestamp for DB: {message_created_at}")

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

                    logger.info(f"Inserting new conversation: {conversation_dict}")

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
            # Add more detailed logging for the TypeError
            if isinstance(e, TypeError) and "datetime.datetime" in str(e):
                logger.error(
                    f"TypeError details: term_start_date={term_start_date} ({type(term_start_date)}), "
                    f"message_created_at={message_created_at} ({type(message_created_at)})"
                )
            continue

    logger.info(f"Successfully synced {conversation_count} conversations")
    return conversation_count
