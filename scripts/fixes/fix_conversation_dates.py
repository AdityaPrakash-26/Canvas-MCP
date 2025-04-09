#!/usr/bin/env python3
"""
Script to fix conversation dates in the database.
This script will:
1. Connect directly to the Canvas API to fetch the actual conversation dates
2. Update conversations in the database with the correct dates from Canvas
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
logger = logging.getLogger("fix_conversation_dates")


def fix_conversation_dates(db_manager, canvas):
    """Fix conversation dates to use the actual Canvas dates."""
    logger.info("Fixing conversation dates...")

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
            logger.info(
                f"Processing conversation ID {conv['id']} (Canvas ID: {conv['canvas_conversation_id']})"
            )

            try:
                # Fetch the conversation from Canvas API
                canvas_conv = canvas.get_conversation(conv["canvas_conversation_id"])

                if not canvas_conv:
                    logger.warning(
                        f"Could not fetch conversation {conv['id']} from Canvas API"
                    )
                    continue

                # Try to get the actual date from Canvas
                # First try last_message_at which is when the message was sent
                canvas_date = None

                if (
                    hasattr(canvas_conv, "last_message_at")
                    and canvas_conv.last_message_at
                ):
                    canvas_date = canvas_conv.last_message_at
                    logger.info(f"Using last_message_at: {canvas_date}")
                elif hasattr(canvas_conv, "created_at") and canvas_conv.created_at:
                    canvas_date = canvas_conv.created_at
                    logger.info(f"Using created_at: {canvas_date}")

                # If we have messages, try to get the date from the first message
                if (
                    not canvas_date
                    and hasattr(canvas_conv, "messages")
                    and canvas_conv.messages
                ):
                    message = canvas_conv.messages[0]
                    if isinstance(message, dict) and message.get("created_at"):
                        canvas_date = message.get("created_at")
                        logger.info(f"Using message.created_at: {canvas_date}")
                    elif hasattr(message, "created_at") and message.created_at:
                        canvas_date = message.created_at
                        logger.info(f"Using message.created_at: {canvas_date}")

                if not canvas_date:
                    logger.warning(f"Could not find date for conversation {conv['id']}")
                    continue

                # Parse the Canvas date
                if isinstance(canvas_date, str):
                    # Canvas dates are typically in ISO format with Z suffix
                    try:
                        parsed_date = datetime.datetime.fromisoformat(
                            canvas_date.replace("Z", "+00:00")
                        )
                        # Convert to ISO format string
                        iso_date = parsed_date.isoformat()
                    except ValueError as e:
                        logger.error(f"Error parsing Canvas date {canvas_date}: {e}")
                        continue
                else:
                    # If it's already a datetime, just convert to ISO
                    iso_date = canvas_date.isoformat()

                # Compare with current date in DB
                current_db_date = conv["posted_at"]
                logger.info(f"Current DB date: {current_db_date}")
                logger.info(f"Canvas date: {iso_date}")

                # Update the database with the correct date
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
                    f"Fixed date for conversation {conv['id']}: {current_db_date} -> {iso_date}"
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
    """Main function to fix conversation dates."""
    try:
        # Initialize Canvas API
        logger.info(f"Connecting to Canvas API at {config.API_URL}")
        canvas = Canvas(config.API_URL, config.API_KEY)

        # Get current user
        user = canvas.get_current_user()
        logger.info(f"Connected as user: {user.name} (ID: {user.id})")

        # Initialize database manager
        db_manager = DatabaseManager("data/canvas_mcp.db")

        # Fix conversation dates
        fix_conversation_dates(db_manager, canvas)

        logger.info("Finished fixing conversation dates")

    except Exception as e:
        logger.exception(f"Error fixing conversation dates: {e}")


if __name__ == "__main__":
    main()
