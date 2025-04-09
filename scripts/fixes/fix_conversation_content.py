#!/usr/bin/env python3
"""
Script to fix conversation content and date formatting issues in the database.
This script will:
1. Connect directly to the Canvas API to fetch conversation content
2. Update conversations in the database that have empty content
3. Fix date formatting for all conversations to ensure consistency
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
from canvas_mcp.utils.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fix_conversation_content")


def fix_conversation_content(db_manager, canvas):
    """Fix conversations with empty content."""
    logger.info("Fixing conversations with empty content...")

    # Get conversations with empty content
    conn, cursor = db_manager.connect()
    try:
        cursor.execute(
            """
            SELECT id, canvas_conversation_id, title, content, posted_by, posted_at
            FROM conversations
            WHERE content = '' OR content IS NULL
            ORDER BY id DESC
            """
        )
        empty_content_convs = [dict(row) for row in cursor.fetchall()]
        logger.info(
            f"Found {len(empty_content_convs)} conversations with empty content"
        )

        # Process each conversation
        fixed_count = 0
        for conv in empty_content_convs:
            logger.info(
                f"Processing conversation ID {conv['id']} (Canvas ID: {conv['canvas_conversation_id']})"
            )

            try:
                # Fetch the conversation from Canvas API
                canvas_conv = canvas.get_conversation(conv["canvas_conversation_id"])

                if (
                    not canvas_conv
                    or not hasattr(canvas_conv, "messages")
                    or not canvas_conv.messages
                ):
                    logger.warning(f"No messages found for conversation {conv['id']}")
                    continue

                # Get the first message
                message = canvas_conv.messages[0]

                # Try to extract content
                content = None

                # Try different sources
                if isinstance(message, dict) and message.get("body"):
                    content = message.get("body")
                elif hasattr(message, "body") and message.body:
                    content = message.body
                elif hasattr(canvas_conv, "last_message") and canvas_conv.last_message:
                    content = canvas_conv.last_message

                if not content:
                    logger.warning(
                        f"Could not find content for conversation {conv['id']}"
                    )
                    continue

                # Update the database
                cursor.execute(
                    """
                    UPDATE conversations
                    SET content = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (content, datetime.datetime.now().isoformat(), conv["id"]),
                )
                conn.commit()
                fixed_count += 1
                logger.info(f"Fixed content for conversation {conv['id']}")

            except Exception as e:
                logger.error(f"Error fixing conversation {conv['id']}: {e}")
                conn.rollback()

        logger.info(
            f"Fixed content for {fixed_count} out of {len(empty_content_convs)} conversations"
        )

    finally:
        conn.close()


def fix_date_formatting(db_manager):
    """Fix date formatting for all conversations."""
    logger.info("Fixing date formatting for all conversations...")

    # Get all conversations
    conn, cursor = db_manager.connect()
    try:
        cursor.execute(
            """
            SELECT id, canvas_conversation_id, title, posted_at
            FROM conversations
            ORDER BY id DESC
            """
        )
        all_convs = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(all_convs)} total conversations")

        # Process each conversation
        fixed_count = 0
        for conv in all_convs:
            try:
                posted_at = conv["posted_at"]

                # Skip if already in ISO format with timezone
                if isinstance(posted_at, str) and (
                    "+" in posted_at or "Z" in posted_at
                ):
                    continue

                # Parse the date
                if isinstance(posted_at, str):
                    try:
                        # Try to parse the date
                        parsed_date = datetime.datetime.fromisoformat(
                            posted_at.replace("Z", "+00:00")
                        )
                    except ValueError:
                        try:
                            # Try other formats
                            parsed_date = datetime.datetime.strptime(
                                posted_at, "%Y-%m-%d %H:%M:%S.%f"
                            )
                        except ValueError:
                            try:
                                parsed_date = datetime.datetime.strptime(
                                    posted_at, "%Y-%m-%d %H:%M:%S"
                                )
                            except ValueError:
                                logger.warning(
                                    f"Could not parse date {posted_at} for conversation {conv['id']}"
                                )
                                continue

                    # Add timezone if missing
                    if not parsed_date.tzinfo:
                        parsed_date = parsed_date.replace(tzinfo=datetime.UTC)

                    # Format as ISO with timezone
                    iso_date = parsed_date.isoformat()

                    # Update the database
                    cursor.execute(
                        """
                        UPDATE conversations
                        SET posted_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (iso_date, datetime.datetime.now().isoformat(), conv["id"]),
                    )
                    conn.commit()
                    fixed_count += 1
                    logger.info(
                        f"Fixed date for conversation {conv['id']}: {posted_at} -> {iso_date}"
                    )

            except Exception as e:
                logger.error(f"Error fixing date for conversation {conv['id']}: {e}")
                conn.rollback()

        logger.info(
            f"Fixed dates for {fixed_count} out of {len(all_convs)} conversations"
        )

    finally:
        conn.close()


def main():
    """Main function to fix conversation issues."""
    try:
        # Initialize Canvas API
        logger.info(f"Connecting to Canvas API at {config.API_URL}")
        canvas = Canvas(config.API_URL, config.API_KEY)

        # Get current user
        user = canvas.get_current_user()
        logger.info(f"Connected as user: {user.name} (ID: {user.id})")

        # Initialize database manager
        db_manager = DatabaseManager("data/canvas_mcp.db")

        # Fix conversation content
        fix_conversation_content(db_manager, canvas)

        # Fix date formatting
        fix_date_formatting(db_manager)

        logger.info("Finished fixing conversation issues")

    except Exception as e:
        logger.exception(f"Error fixing conversation issues: {e}")


if __name__ == "__main__":
    main()
