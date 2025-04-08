"""
Canvas API interaction helpers.

This module contains functions for interacting with the Canvas API.
These functions handle the direct API calls, pagination, and error handling.
"""

import logging
from typing import Any

# Create a logger for this module
logger = logging.getLogger(__name__)

# Type alias for Canvas API objects
CanvasObject = Any  # The actual type depends on the canvasapi library


def fetch_courses(
    canvas, enrollment_state: str = "active", user=None
) -> list[CanvasObject]:
    """
    Fetch courses from the Canvas API.

    Args:
        canvas: Canvas API client instance
        enrollment_state: Filter courses by enrollment state (default: "active")
        user: Optional user object to fetch courses for (default: current user)

    Returns:
        List of Canvas course objects
    """
    try:
        if user is None:
            user = canvas.get_current_user()

        # Get courses from Canvas directly using the user object
        # Only get courses with the specified enrollment state
        courses = list(user.get_courses(enrollment_state=enrollment_state))
        logger.info(
            f"Successfully fetched {len(courses)} courses with state '{enrollment_state}'"
        )
        return courses
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return []


def fetch_assignments(canvas, course_id: int) -> list[CanvasObject]:
    """
    Fetch assignments for a course from the Canvas API.

    Args:
        canvas: Canvas API client instance
        course_id: Canvas course ID

    Returns:
        List of Canvas assignment objects
    """
    try:
        course = canvas.get_course(course_id)
        assignments = list(course.get_assignments())
        logger.info(
            f"Successfully fetched {len(assignments)} assignments for course {course_id}"
        )
        return assignments
    except Exception as e:
        logger.error(f"Error fetching assignments for course {course_id}: {e}")
        return []


def fetch_modules(canvas, course_id: int) -> list[CanvasObject]:
    """
    Fetch modules for a course from the Canvas API.

    Args:
        canvas: Canvas API client instance
        course_id: Canvas course ID

    Returns:
        List of Canvas module objects
    """
    try:
        course = canvas.get_course(course_id)
        modules = list(course.get_modules())
        logger.info(
            f"Successfully fetched {len(modules)} modules for course {course_id}"
        )
        return modules
    except Exception as e:
        logger.error(f"Error fetching modules for course {course_id}: {e}")
        return []


def fetch_module_items(canvas_module: CanvasObject) -> list[CanvasObject]:
    """
    Fetch items for a module from the Canvas API.

    Args:
        canvas_module: Canvas module object

    Returns:
        List of Canvas module item objects
    """
    try:
        items = list(canvas_module.get_module_items())
        logger.info(
            f"Successfully fetched {len(items)} items for module {canvas_module.id}"
        )
        return items
    except Exception as e:
        logger.error(
            f"Error fetching items for module {getattr(canvas_module, 'id', 'unknown')}: {e}"
        )
        return []


def fetch_announcements(canvas, course_id: int) -> list[CanvasObject]:
    """
    Fetch announcements for a course from the Canvas API.

    Args:
        canvas: Canvas API client instance
        course_id: Canvas course ID

    Returns:
        List of Canvas announcement objects
    """
    try:
        course = canvas.get_course(course_id)
        announcements = list(course.get_discussion_topics(only_announcements=True))
        logger.info(
            f"Successfully fetched {len(announcements)} announcements for course {course_id}"
        )
        return announcements
    except Exception as e:
        logger.error(f"Error fetching announcements for course {course_id}: {e}")
        return []


def fetch_files(canvas, course_id: int) -> list[CanvasObject]:
    """
    Fetch files for a course from the Canvas API.

    Args:
        canvas: Canvas API client instance
        course_id: Canvas course ID

    Returns:
        List of Canvas file objects
    """
    try:
        course = canvas.get_course(course_id)
        files = list(course.get_files())
        logger.info(f"Successfully fetched {len(files)} files for course {course_id}")
        return files
    except Exception as e:
        logger.error(f"Error fetching files for course {course_id}: {e}")
        return []


def fetch_assignment_details(
    canvas, course_id: int, assignment_id: int
) -> CanvasObject | None:
    """
    Fetch detailed information about a specific assignment.

    Args:
        canvas: Canvas API client instance
        course_id: Canvas course ID
        assignment_id: Canvas assignment ID

    Returns:
        Canvas assignment object or None if not found
    """
    try:
        course = canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)
        logger.info(f"Successfully fetched details for assignment {assignment_id}")
        return assignment
    except Exception as e:
        logger.error(f"Error fetching details for assignment {assignment_id}: {e}")
        return None
