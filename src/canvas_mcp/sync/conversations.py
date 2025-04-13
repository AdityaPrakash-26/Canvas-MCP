"""
Canvas Conversations Sync

This module provides functionality for synchronizing conversation data between
the Canvas API and the local database asynchronously.
"""

import asyncio
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from canvas_mcp.models import DBConversation
from canvas_mcp.utils.db_manager import run_db_persist_in_thread
from canvas_mcp.utils.formatters import convert_html_to_markdown

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SYNC_DAYS = 21


async def sync_conversations(sync_service: "SyncService", sync_days: int = DEFAULT_SYNC_DAYS) -> int:
    """
    Synchronize conversation data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        sync_days: Number of past days to sync conversations from.

    Returns:
        Number of conversations synced/updated.
    """
    if not sync_service.api_adapter.is_available():
        logger.error("Canvas API adapter is not available for conversation sync")
        return 0

    # Calculate the cutoff date
    cutoff_date = datetime.now(UTC) - timedelta(days=sync_days)
    logger.info(f"Syncing conversations since: {cutoff_date}")

    # Get course mapping (name -> local_id)
    conn_map, cursor_map = sync_service.db_manager.connect()
    try:
        cursor_map.execute("SELECT id, course_name FROM courses")
        course_name_to_id = {row["course_name"]: row["id"] for row in cursor_map.fetchall()}
    except Exception as e:
        logger.error(f"Error getting course mapping for conversations: {e}")
        return 0
    finally:
        conn_map.close()

    if not course_name_to_id:
        logger.warning("No courses found in DB to map conversations")
        return 0

    # --- Fetch Stage (All Conversations Summary) ---
    logger.info("Fetching conversation summaries from Canvas API...")
    try:
        # Use semaphore for the initial fetch
        async with sync_service.api_semaphore:
            raw_conversations = await asyncio.to_thread(
                sync_service.api_adapter.get_conversations_raw, per_page=100 # Fetch summaries with pagination
            )
    except Exception as e:
        logger.error(f"Failed to fetch conversation summaries: {e}", exc_info=True)
        return 0

    if not raw_conversations:
        logger.info("No conversation summaries found from Canvas API.")
        return 0
    logger.info(f"Fetched {len(raw_conversations)} conversation summaries.")

    # --- Filter & Prepare Detail Fetch ---
    detail_fetch_tasks = []
    valid_conv_summaries = {} # canvas_conv_id -> raw_conv summary object
    conv_context_map = {} # canvas_conv_id -> matching_local_course_id

    processed_conversations_ids = set() # Track processed conversations to avoid duplicates

    for raw_conv in raw_conversations:
        try:
            conv_id = getattr(raw_conv, "id", None)
            if not conv_id or conv_id in processed_conversations_ids:
                continue

            # Check timestamp before fetching details
            message_created_at = _get_conversation_timestamp(raw_conv)
            if not message_created_at or message_created_at < cutoff_date:
                # logger.debug(f"Skipping conv {conv_id}: date {message_created_at} older than cutoff {cutoff_date}")
                continue

            # Find matching course based on context_name
            context_name = getattr(raw_conv, "context_name", None)
            if not context_name: continue

            matching_course_id = None
            # Simple substring match - might need refinement for accuracy
            for course_name, local_id in course_name_to_id.items():
                if course_name in context_name:
                    matching_course_id = local_id
                    break
            if not matching_course_id: continue # Skip if no matching course

            # Prepare to fetch details
            valid_conv_summaries[conv_id] = raw_conv
            conv_context_map[conv_id] = matching_course_id
            task = asyncio.create_task(_fetch_conversation_detail(sync_service, conv_id))
            detail_fetch_tasks.append(task)
            processed_conversations_ids.add(conv_id) # Avoid duplicate detail fetches

        except Exception as e:
            logger.error(f"Error pre-processing conversation summary {getattr(raw_conv, 'id', 'N/A')}: {e}", exc_info=True)

    logger.info(f"Prepared {len(detail_fetch_tasks)} tasks to fetch conversation details.")

    # --- Parallel Fetch Stage (Details) ---
    detail_results_or_exceptions = await asyncio.gather(*detail_fetch_tasks, return_exceptions=True)
    logger.info("Finished gathering conversation details.")

    # --- Process & Validate Details ---
    all_valid_conversations: list[DBConversation] = []
    conv_ids_processed = list(valid_conv_summaries.keys()) # Get IDs in the order tasks were created

    for i, result in enumerate(detail_results_or_exceptions):
        if i >= len(conv_ids_processed):
             logger.error(f"Index mismatch processing conversation detail results ({i})")
             continue
        conv_id = conv_ids_processed[i]
        raw_conv_summary = valid_conv_summaries[conv_id]
        local_course_id = conv_context_map[conv_id]

        if isinstance(result, Exception):
            logger.error(f"Failed fetching details for conversation {conv_id}: {result}")
            continue
        if result is None or not hasattr(result, "messages") or not result.messages:
            logger.warning(f"No valid messages found in details for conversation {conv_id}")
            continue

        conv_detail = result
        message = conv_detail.messages[0] # Get the most recent message
        message_created_at = _get_conversation_timestamp(raw_conv_summary, message) # Get best timestamp

        # Final check on date (in case summary date was missing/wrong)
        if not message_created_at or message_created_at < cutoff_date:
            logger.debug(f"Skipping conv {conv_id} after detail fetch: date {message_created_at} older than cutoff {cutoff_date}")
            continue

        try:
            # Get message body
            message_body = _get_message_body(message, raw_conv_summary)
            if message_body:
                message_body = convert_html_to_markdown(message_body) # Keep HTML conversion
            else:
                 message_body = "[No message content available]"
                 logger.warning(f"No message body found for conversation {conv_id}, using default")

            # Get author name
            author_name = _get_author_name(message, conv_detail)

            # Prepare data for validation
            conversation_data = {
                "id": conv_id, # Alias for canvas_conversation_id
                "course_id": local_course_id,
                "title": getattr(raw_conv_summary, "subject", "No Subject"),
                "content": message_body,
                "posted_by": author_name,
                "posted_at": message_created_at.isoformat() if message_created_at else None,
            }

            db_conversation = DBConversation.model_validate(conversation_data)
            all_valid_conversations.append(db_conversation)

        except Exception as e:
            logger.error(f"Validation error for conversation {conv_id}: {e}", exc_info=True)

    logger.info(f"Processed details, {len(all_valid_conversations)} valid conversations found.")

    # --- Persist Stage ---
    persisted_count = await run_db_persist_in_thread(
        sync_service.db_manager,
        _persist_conversations,
        sync_service,
        all_valid_conversations
    )

    logger.info(f"Finished conversation sync. Persisted/updated {persisted_count} conversations.")
    return persisted_count


async def _fetch_conversation_detail(sync_service: "SyncService", conv_id: int) -> Any | None:
    """Helper async function to wrap the threaded API call for conversation details."""
    async with sync_service.api_semaphore:
        logger.debug(f"Semaphore acquired for fetching detail: conversation {conv_id}")
        try:
            detail = await asyncio.to_thread(
                sync_service.api_adapter.get_conversation_detail_raw,
                conv_id
            )
            return detail
        except Exception as e:
            logger.error(f"Error in thread fetching detail for conversation {conv_id}: {e}", exc_info=True)
            return None


def _get_conversation_timestamp(raw_conv: Any, message: Any | None = None) -> datetime | None:
    """Gets the best available timestamp for a conversation."""
    timestamp_str = None
    # 1. Try conversation-level timestamp (most reliable for overall last activity)
    if hasattr(raw_conv, "last_message_at") and raw_conv.last_message_at:
        timestamp_str = raw_conv.last_message_at
    # 2. Fallback to message-level timestamp if available
    elif message and hasattr(message, "created_at") and message.created_at:
        timestamp_str = message.created_at
    # 3. Fallback to conversation workflow_state change date (less ideal)
    elif hasattr(raw_conv, "workflow_state") and hasattr(raw_conv, "updated_at") and raw_conv.updated_at:
         timestamp_str = raw_conv.updated_at # Use updated_at as a proxy

    if timestamp_str:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse timestamp string: {timestamp_str} for conv {getattr(raw_conv, 'id', 'N/A')}")

    logger.warning(f"Could not determine timestamp for conversation {getattr(raw_conv, 'id', 'N/A')}")
    return None


def _get_message_body(message: Any, raw_conv_summary: Any) -> str | None:
    """Gets the message body, trying message object first, then summary."""
    # Try message object (dict or object)
    if isinstance(message, dict) and "body" in message:
        return message["body"]
    elif hasattr(message, "body") and message.body:
        return message.body
    # Fallback to summary object
    elif hasattr(raw_conv_summary, "last_message") and raw_conv_summary.last_message:
        return raw_conv_summary.last_message
    return None


def _get_author_name(message: Any, conv_detail: Any) -> str:
    """Gets the author name from participants, matching by message author_id."""
    default_author = "Instructor" # Default assumption
    author_id = getattr(message, "author_id", None)

    if hasattr(conv_detail, "participants") and conv_detail.participants:
        participants = conv_detail.participants
        # Handle list of dicts or list of objects
        if isinstance(participants[0], dict):
            if author_id:
                 for p in participants:
                     if p.get("id") == author_id and "name" in p:
                         return p["name"]
            # Fallback to first participant if no author_id match
            elif "name" in participants[0]:
                 return participants[0]["name"]
        else: # Assuming list of objects
            if author_id:
                for p in participants:
                    if getattr(p, "id", None) == author_id:
                        return getattr(p, "name", default_author)
            # Fallback to first participant
            elif participants:
                 return getattr(participants[0], "name", default_author)

    return default_author


def _persist_conversations(
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    sync_service: "SyncService",
    valid_conversations: list[DBConversation],
) -> int:
    """
    Persist conversations in a single transaction using batch operations.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        sync_service: The sync service instance.
        valid_conversations: List of validated conversation models.

    Returns:
        Number of conversations synced/updated.
    """
    if not valid_conversations:
        return 0

    processed_count = 0
    now_iso = datetime.now().isoformat()

    # 1. Fetch existing conversation IDs
    existing_map: dict[int, int] = {} # canvas_conversation_id -> local_id
    canvas_ids_in_batch = {c.canvas_conversation_id for c in valid_conversations}
    try:
        if canvas_ids_in_batch:
            placeholders = ','.join('?' * len(canvas_ids_in_batch))
            sql = f"SELECT id, canvas_conversation_id FROM conversations WHERE canvas_conversation_id IN ({placeholders})"
            cursor.execute(sql, list(canvas_ids_in_batch))
            for row in cursor.fetchall():
                existing_map[row['canvas_conversation_id']] = row['id']
    except sqlite3.Error as e:
        logger.error(f"Failed to query existing conversations: {e}")
        raise

    # 2. Prepare data
    insert_data = []
    update_data = []
    for db_conv in valid_conversations:
        item_dict = db_conv.model_dump(exclude={"created_at", "updated_at"})
        item_dict["updated_at"] = now_iso

        if db_conv.canvas_conversation_id in existing_map:
            item_dict["local_id"] = existing_map[db_conv.canvas_conversation_id]
            update_data.append(item_dict)
        else:
            insert_tuple = (
                item_dict.get("course_id"),
                item_dict.get("canvas_conversation_id"),
                item_dict.get("title"),
                item_dict.get("content"),
                item_dict.get("posted_by"),
                item_dict.get("posted_at"),
                item_dict.get("updated_at"),
            )
            insert_data.append(insert_tuple)

    # 3. Batch insert
    if insert_data:
        cols = "course_id, canvas_conversation_id, title, content, posted_by, posted_at, updated_at"
        phs = ", ".join(["?"] * len(insert_data[0]))
        sql = f"INSERT INTO conversations ({cols}) VALUES ({phs})"
        try:
            cursor.executemany(sql, insert_data)
            processed_count += cursor.rowcount
            logger.debug(f"Batch inserted {cursor.rowcount} conversations.")
        except sqlite3.Error as e:
            logger.error(f"Batch conversation insert failed: {e}")
            raise

    # 4. Looped update
    update_count = 0
    if update_data:
        logger.debug(f"Updating {len(update_data)} conversations individually...")
        for item_dict in update_data:
            local_id = item_dict.pop("local_id")
            canvas_id = item_dict.get("canvas_conversation_id")
            try:
                set_clause = ", ".join([f"{k} = ?" for k in item_dict if k != 'canvas_conversation_id'])
                values = [v for k, v in item_dict.items() if k != 'canvas_conversation_id']
                values.append(local_id)
                sql = f"UPDATE conversations SET {set_clause} WHERE id = ?"
                cursor.execute(sql, values)
                update_count += cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Failed to update conversation {canvas_id} (local ID {local_id}): {e}")
    processed_count += update_count
    logger.debug(f"Updated {update_count} conversations.")

    return processed_count
