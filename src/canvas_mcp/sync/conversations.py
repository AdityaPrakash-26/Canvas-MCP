"""
Canvas Conversations Sync

This module provides functionality for synchronizing conversation data between
the Canvas API and the local database.
"""

import logging
from datetime import datetime

from canvas_mcp.models import DBConversation

# Configure logging
logger = logging.getLogger(__name__)


def sync_conversations(sync_service, course_ids: list[int] | None = None) -> int:
    """
    Synchronize conversation data from Canvas to the local database.

    Args:
        course_ids: Optional list of local course IDs to sync

    Returns:
        Number of conversations synced
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available")
        return 0

    # Get courses to sync
    conn, cursor = sync_service.db_manager.connect()
    try:
        if course_ids is None:
            # Get all courses
            cursor.execute("SELECT * FROM courses")
            courses_to_sync = [dict(row) for row in cursor.fetchall()]
        else:
            # Get specific courses
            courses_to_sync = []
            for course_id in course_ids:
                cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
                course = cursor.fetchone()
                if course:
                    courses_to_sync.append(dict(course))
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

    # Get term start date for filtering
    conn, cursor = sync_service.db_manager.connect()
    try:
        # Get the current term's start date
        cursor.execute(
            """
            SELECT start_date FROM terms
            WHERE id = (SELECT term_id FROM courses WHERE id = ? LIMIT 1)
            """,
            (courses_to_sync[0]["id"],),
        )
        term_row = cursor.fetchone()
        term_start_date = term_row["start_date"] if term_row else None
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting term start date: {e}")
        term_start_date = None
    finally:
        conn.close()

    # Create a mapping of course names to local IDs
    course_name_to_id = {}
    for course in courses_to_sync:
        course_name_to_id[course["course_name"]] = course["id"]

    # Fetch all conversations
    raw_conversations = sync_service.api_adapter.get_conversations_raw()
    if not raw_conversations:
        logger.info("No conversations found")
        return 0

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
            conv_detail = sync_service.api_adapter.get_conversation_detail_raw(conv_id)
            if (
                not conv_detail
                or not hasattr(conv_detail, "messages")
                or not conv_detail.messages
            ):
                continue

            # Get the most recent message
            message = conv_detail.messages[0]

            # Parse the created_at timestamp
            message_created_at_str = getattr(message, "created_at", None)
            message_created_at = None

            if message_created_at_str:
                try:
                    # Try to parse the timestamp
                    from datetime import datetime

                    if isinstance(message_created_at_str, str):
                        # Try ISO format first
                        try:
                            message_created_at = datetime.fromisoformat(
                                message_created_at_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            # Try other common formats
                            import dateutil.parser

                            message_created_at = dateutil.parser.parse(
                                message_created_at_str
                            )
                    else:
                        # If it's already a datetime object, use it directly
                        message_created_at = message_created_at_str
                except Exception as e:
                    logger.warning(
                        f"Error parsing timestamp {message_created_at_str}: {e}"
                    )
                    # Use current time as fallback
                    message_created_at = datetime.now()
            else:
                # Use current time as fallback if no timestamp is available
                message_created_at = datetime.now()

            # Skip if message is older than term start date
            if (
                term_start_date
                and message_created_at
                and message_created_at < term_start_date
            ):
                continue

            # Get message body
            message_body = getattr(message, "body", None)

            # Clean up HTML if present
            if message_body and "<" in message_body and ">" in message_body:
                try:
                    # Try to import BeautifulSoup
                    try:
                        from bs4 import BeautifulSoup

                        soup = BeautifulSoup(message_body, "html.parser")
                        message_body = soup.get_text(separator=" ", strip=True)
                    except ImportError:
                        # If BeautifulSoup is not available, use a simple regex approach
                        import re

                        message_body = re.sub(r"<[^>]+>", " ", message_body)
                        message_body = re.sub(r"\s+", " ", message_body).strip()
                except Exception as e:
                    logger.warning(f"Error cleaning HTML from message: {e}")

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
                "content": message_body,  # Direct field name, no alias needed
                "posted_by": author_name,
                "posted_at": message_created_at,  # Direct field name, no alias needed
                "created_at": datetime.now().isoformat(),
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
            logger.error(f"Error processing conversation: {e}")

    logger.info(f"Successfully synced {conversation_count} conversations")
    return conversation_count


def _persist_conversations(
    sync_service, conn, cursor, valid_conversations: list[DBConversation]
) -> int:
    """
    Persist conversations to the database.

    Args:
        conn: Database connection
        cursor: Database cursor
        valid_conversations: List of validated conversation models

    Returns:
        Number of conversations persisted
    """
    count = 0

    for db_conversation in valid_conversations:
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
                placeholders = ", ".join([f"{k} = ?" for k in conversation_dict.keys()])
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

            count += 1
        except Exception as e:
            logger.error(
                f"Error persisting conversation {db_conversation.canvas_conversation_id}: {e}"
            )

    return count
