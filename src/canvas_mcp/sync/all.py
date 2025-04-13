"""
Canvas Sync All

This module provides functionality for synchronizing all data between
the Canvas API and the local database asynchronously.
"""

import asyncio  # Add asyncio import
import logging
from typing import TYPE_CHECKING, Any

# Configure logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from canvas_mcp.sync.service import SyncService


async def sync_all(
    sync_service: "SyncService", user_id: str | None = None, term_id: int | None = -1
) -> dict[str, int]:
    """
    Synchronize all data from Canvas to the local database asynchronously.

    Args:
        sync_service: The sync service instance.
        user_id: Optional user ID to filter courses.
        term_id: Optional term ID to filter courses
                 (default is -1, which only selects the most recent term).

    Returns:
        Dictionary with counts of synced items.
    """
    logger.info("Starting async sync process...")
    start_time = asyncio.get_event_loop().time()

    # First sync courses (must be sequential as others depend on it)
    logger.info("Syncing courses...")
    try:
        course_ids = await sync_service.sync_courses(user_id, term_id)
        courses_synced_count = len(course_ids)
        logger.info(f"Synced {courses_synced_count} courses.")
    except Exception as e:
        logger.error(f"Critical error during course sync: {e}", exc_info=True)
        return {
            "courses": 0,
            "assignments": 0,
            "modules": 0,
            "announcements": 0,
            "conversations": 0,
        }

    if not course_ids:
        logger.warning("No courses synced, skipping dependent sync operations.")
        # Return zero counts for everything
        return {
            "courses": 0,
            "assignments": 0,
            "modules": 0,
            "announcements": 0,
            "conversations": 0,
        }

    # Then sync other data in parallel
    logger.info(
        "Starting parallel sync for assignments, modules, announcements, conversations..."
    )
    sync_tasks = [
        sync_service.sync_assignments(course_ids),
        sync_service.sync_modules(course_ids),
        sync_service.sync_announcements(course_ids),
        sync_service.sync_conversations(),  # Assumes this is independent or fetches all needed context
    ]
    results = await asyncio.gather(*sync_tasks, return_exceptions=True)

    # Process results safely
    keys = ["assignments", "modules", "announcements", "conversations"]
    counts = {}
    for i, res in enumerate(results):
        key = keys[i]
        if isinstance(res, Exception):
            logger.error(f"Error during {key} sync: {res}", exc_info=res)
            counts[key] = 0  # Record 0 count on error
        elif isinstance(res, int):
            counts[key] = res
            logger.info(f"Synced {res} {key}.")
        else:
            logger.error(f"Unexpected result type for {key} sync: {type(res)}")
            counts[key] = 0

    end_time = asyncio.get_event_loop().time()
    logger.info(f"Finished all sync operations in {end_time - start_time:.2f} seconds.")

    final_counts = {"courses": courses_synced_count, **counts}
    logger.info(f"Sync summary: {final_counts}")
    return final_counts


# _get_assignment_type remains synchronous as it's pure logic
def _get_assignment_type(sync_service, assignment: Any) -> str:
    """
    Determine the type of an assignment.

    Args:
        assignment: Canvas assignment object

    Returns:
        Assignment type string
    """
    if not hasattr(assignment, "submission_types"):
        return "assignment"

    submission_types = getattr(assignment, "submission_types", [])
    name_lower = getattr(assignment, "name", "").lower()

    if "online_quiz" in submission_types:
        return "quiz"
    elif "discussion_topic" in submission_types:
        return "discussion"
    elif any(t in name_lower for t in ["exam", "midterm", "final"]):
        return "exam"
    else:
        return "assignment"
