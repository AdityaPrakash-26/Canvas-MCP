"""
Canvas Sync All

This module provides functionality for synchronizing all data between
the Canvas API and the local database.
"""

import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# No imports needed for sync functions as they're accessed via sync_service


def sync_all(
    sync_service, user_id: str | None = None, term_id: int | None = -1
) -> dict[str, int]:
    """
    Synchronize all data from Canvas to the local database.

    Args:
        user_id: Optional user ID to filter courses
        term_id: Optional term ID to filter courses
                 (default is -1, which only selects the most recent term)

    Returns:
        Dictionary with counts of synced items
    """
    # First sync courses
    course_ids = sync_service.sync_courses(user_id, term_id)

    # Then sync other data
    assignment_count = sync_service.sync_assignments(course_ids)
    module_count = sync_service.sync_modules(course_ids)
    announcement_count = sync_service.sync_announcements(course_ids)
    conversation_count = sync_service.sync_conversations()

    return {
        "courses": len(course_ids),
        "assignments": assignment_count,
        "modules": module_count,
        "announcements": announcement_count,
        "conversations": conversation_count,
    }


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

    if "online_quiz" in assignment.submission_types:
        return "quiz"
    elif "discussion_topic" in assignment.submission_types:
        return "discussion"
    elif any(t in assignment.name.lower() for t in ["exam", "midterm", "final"]):
        return "exam"
    else:
        return "assignment"
