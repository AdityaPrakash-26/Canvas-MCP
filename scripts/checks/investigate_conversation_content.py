#!/usr/bin/env python3
"""
Script to investigate why specific conversations don't have content.
This script will fetch specific conversations from the Canvas API and
examine their structure to understand why content isn't being extracted.
"""

import datetime
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Canvas MCP components
from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("investigate_conversation_content")


def get_conversation_from_db(db_manager, conversation_id):
    """Get conversation details from the database."""
    conn, cursor = db_manager.connect()
    try:
        cursor.execute(
            """
            SELECT c.*, courses.course_name
            FROM conversations c
            JOIN courses ON c.course_id = courses.id
            WHERE c.id = ?
            """,
            (conversation_id,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def investigate_conversation(api_adapter, db_manager, conversation_id):
    """
    Investigate a specific conversation to understand why content is missing.

    Args:
        api_adapter: Canvas API adapter
        db_manager: Database manager
        conversation_id: Local database ID of the conversation to investigate
    """
    # Get conversation from database
    db_conversation = get_conversation_from_db(db_manager, conversation_id)
    if not db_conversation:
        logger.error(f"Conversation ID {conversation_id} not found in database")
        return

    logger.info(f"Investigating conversation ID {conversation_id}")
    logger.info(f"Database record: {db_conversation}")

    # Get the Canvas conversation ID
    canvas_conversation_id = db_conversation.get("canvas_conversation_id")
    if not canvas_conversation_id:
        logger.error(f"No Canvas conversation ID found for local ID {conversation_id}")
        return

    # Fetch the conversation from Canvas API
    logger.info(f"Fetching conversation {canvas_conversation_id} from Canvas API")
    conversation = api_adapter.get_conversation_detail_raw(canvas_conversation_id)

    if not conversation:
        logger.error(
            f"Failed to fetch conversation {canvas_conversation_id} from Canvas API"
        )
        return

    # Log conversation attributes
    logger.info(f"Canvas conversation attributes: {dir(conversation)}")

    # Check for messages
    if not hasattr(conversation, "messages"):
        logger.error(f"Conversation {canvas_conversation_id} has no messages attribute")
        return

    if not conversation.messages:
        logger.error(f"Conversation {canvas_conversation_id} has empty messages list")
        return

    # Examine the first message
    message = conversation.messages[0]
    logger.info(f"First message attributes: {dir(message)}")

    # Try to extract body from different sources
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
            getattr(message, "body", None) if not isinstance(message, dict) else None,
        ),
        (
            "message.message",
            getattr(message, "message", None)
            if not isinstance(message, dict)
            else None,
        ),
        ("conversation.last_message", getattr(conversation, "last_message", None)),
        (
            "message.text",
            getattr(message, "text", None) if not isinstance(message, dict) else None,
        ),
    ]

    # Log all possible body sources
    for source_name, source_value in body_sources:
        logger.info(
            f"Body source {source_name}: {source_value[:100] if source_value else None}"
        )

    # Check participants
    if hasattr(conversation, "participants"):
        logger.info(f"Participants: {conversation.participants}")

        # Try to find the author
        author_id = getattr(message, "author_id", None)
        if author_id:
            logger.info(f"Author ID: {author_id}")
            for participant in conversation.participants:
                if getattr(participant, "id", None) == author_id:
                    logger.info(f"Author: {getattr(participant, 'name', None)}")
                    break

    # Compare with what's in the database
    logger.info(f"Database content: {db_conversation.get('content')}")

    # Analyze date fields
    logger.info("Date field analysis:")
    db_posted_at = db_conversation.get("posted_at")
    logger.info(f"- DB posted_at: {db_posted_at} (type: {type(db_posted_at)})")

    # Try to parse the date from the database
    if isinstance(db_posted_at, str):
        try:
            parsed_date = datetime.datetime.fromisoformat(
                db_posted_at.replace("Z", "+00:00")
            )
            logger.info(f"- Parsed DB date: {parsed_date} (type: {type(parsed_date)})")
        except ValueError as e:
            logger.error(f"- Error parsing DB date: {e}")

    # Check date fields in the Canvas API response
    date_fields = ["created_at", "last_message_at", "last_authored_message_at"]
    for field in date_fields:
        if hasattr(conversation, field):
            value = getattr(conversation, field)
            logger.info(f"- Canvas {field}: {value} (type: {type(value)})")

            # If it's a message, check its date fields too
            if hasattr(message, field):
                msg_value = getattr(message, field)
                logger.info(f"- Message {field}: {msg_value} (type: {type(msg_value)})")

    # Provide a summary
    logger.info("Summary:")
    logger.info(f"- Conversation ID: {conversation_id}")
    logger.info(f"- Canvas Conversation ID: {canvas_conversation_id}")
    logger.info(f"- Title: {db_conversation.get('title')}")
    logger.info(f"- Course: {db_conversation.get('course_name')}")
    logger.info(f"- Has content in DB: {bool(db_conversation.get('content'))}")

    # Determine if any content was found in the API response
    content_found = any(source_value for _, source_value in body_sources)
    logger.info(f"- Content found in API response: {content_found}")

    return {
        "db_conversation": db_conversation,
        "canvas_conversation": conversation,
        "content_found": content_found,
        "body_sources": body_sources,
    }


def analyze_date_formatting(db_manager):
    """Analyze date formatting issues in the database."""
    logger.info("\n=== ANALYZING DATE FORMATTING ISSUES ===\n")

    conn, cursor = db_manager.connect()
    try:
        # Get a sample of conversations with their dates
        cursor.execute(
            """
            SELECT id, canvas_conversation_id, title, posted_at, posted_by
            FROM conversations
            ORDER BY id DESC
            LIMIT 10
            """
        )
        rows = cursor.fetchall()
        sample_convs = [dict(row) for row in rows]

        for i, conv in enumerate(sample_convs):
            logger.info(f"\nConversation {i + 1}/{len(sample_convs)}")
            logger.info(f"Database ID: {conv['id']}")
            logger.info(f"Title: {conv['title']}")
            logger.info(f"Posted by: {conv['posted_by']}")
            logger.info(f"Posted at (raw): {conv['posted_at']}")
            logger.info(f"Posted at (type): {type(conv['posted_at'])}")

            # Try to parse the date
            try:
                if isinstance(conv["posted_at"], str):
                    parsed_date = datetime.datetime.fromisoformat(
                        conv["posted_at"].replace("Z", "+00:00")
                    )
                    logger.info(f"Parsed date: {parsed_date}")
                else:
                    logger.info(f"Date is not a string: {conv['posted_at']}")
            except Exception as e:
                logger.error(f"Error parsing date: {e}")

    finally:
        conn.close()


def main():
    """Main function to investigate conversations without content."""
    try:
        # Initialize Canvas API adapter
        api_adapter = CanvasApiAdapter()

        # Initialize database manager
        db_manager = DatabaseManager("data/canvas_mcp.db")

        # Analyze date formatting issues
        analyze_date_formatting(db_manager)

        # List of conversation IDs to investigate (from the database)
        conversation_ids = [32, 33, 34, 35, 36]  # These are the ones with empty content

        # Also include a conversation that has content for comparison
        conversation_ids.append(1)  # This one has content

        results = {}
        for conv_id in conversation_ids:
            results[conv_id] = investigate_conversation(
                api_adapter, db_manager, conv_id
            )
            print("\n" + "=" * 80 + "\n")  # Separator between conversations

        # Summary of findings
        print("\nSummary of findings:")
        for conv_id, result in results.items():
            if result:
                db_conv = result["db_conversation"]
                print(
                    f"Conversation {conv_id} ({db_conv.get('title')}): "
                    + f"Content in DB: {bool(db_conv.get('content'))}, "
                    + f"Content in API: {result['content_found']}"
                )

    except Exception as e:
        logger.exception(f"Error investigating conversations: {e}")


if __name__ == "__main__":
    main()
