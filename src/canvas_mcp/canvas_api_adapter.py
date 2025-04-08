"""
Canvas API Adapter

This module provides a dedicated adapter for interacting with the Canvas API.
It handles API-specific errors and returns raw data structures.
"""

import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# Make Canvas available for patching in tests
try:
    from canvasapi import Canvas
    from canvasapi.exceptions import CanvasException
except ImportError:
    # Create dummy classes for tests to patch
    class Canvas:
        def __init__(self, api_url, api_key):
            self.api_url = api_url
            self.api_key = api_key

    class CanvasException(Exception):
        pass


class CanvasApiAdapter:
    """
    Adapter for interacting with the Canvas LMS API.

    This class is responsible for making all direct calls to the Canvas API
    and handling API-specific errors.
    """

    def __init__(self, canvas_api_client: Canvas | None = None):
        """
        Initialize the Canvas API adapter.

        Args:
            canvas_api_client: Optional Canvas API client instance
        """
        self.canvas = canvas_api_client
        self.api_url = (
            getattr(canvas_api_client, "api_url", None) if canvas_api_client else None
        )

    def is_available(self) -> bool:
        """
        Check if the Canvas API client is available.

        Returns:
            True if the client is available, False otherwise
        """
        return self.canvas is not None

    def get_current_user_raw(self) -> Any | None:
        """
        Get the current user from the Canvas API.

        Returns:
            Raw Canvas user object or None if not available
        """
        if not self.canvas:
            logger.warning("Canvas API client not available")
            return None

        try:
            return self.canvas.get_current_user()
        except CanvasException as e:
            logger.error(f"Canvas API error getting current user: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting current user: {e}")
            return None

    def get_courses_raw(self, user: Any, enrollment_state: str = "active") -> list[Any]:
        """
        Get courses for a user from the Canvas API.

        Args:
            user: Canvas user object
            enrollment_state: Enrollment state filter (default: "active")

        Returns:
            List of raw Canvas course objects
        """
        if not self.canvas or not user:
            logger.warning("Canvas API client or user not available")
            return []

        try:
            return list(user.get_courses(enrollment_state=enrollment_state))
        except CanvasException as e:
            logger.error(f"Canvas API error getting courses: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error getting courses: {e}")
            return []

    def get_course_raw(self, course_id: int) -> Any | None:
        """
        Get a specific course from the Canvas API.

        Args:
            course_id: Canvas course ID

        Returns:
            Raw Canvas course object or None if not found
        """
        if not self.canvas:
            logger.warning("Canvas API client not available")
            return None

        try:
            return self.canvas.get_course(course_id)
        except CanvasException as e:
            logger.error(f"Canvas API error getting course {course_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting course {course_id}: {e}")
            return None

    def get_assignments_raw(self, course: Any) -> list[Any]:
        """
        Get assignments for a course from the Canvas API.

        Args:
            course: Canvas course object

        Returns:
            List of raw Canvas assignment objects
        """
        if not self.canvas or not course:
            logger.warning("Canvas API client or course not available")
            return []

        try:
            return list(course.get_assignments())
        except CanvasException as e:
            logger.error(
                f"Canvas API error getting assignments for course {course.id}: {e}"
            )
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error getting assignments for course {course.id}: {e}"
            )
            return []

    def get_assignment_raw(self, course: Any, assignment_id: int) -> Any | None:
        """
        Get a specific assignment from the Canvas API.

        Args:
            course: Canvas course object
            assignment_id: Canvas assignment ID

        Returns:
            Raw Canvas assignment object or None if not found
        """
        if not self.canvas or not course:
            logger.warning("Canvas API client or course not available")
            return None

        try:
            return course.get_assignment(assignment_id)
        except CanvasException as e:
            logger.error(f"Canvas API error getting assignment {assignment_id}: {e}")
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error getting assignment {assignment_id}: {e}"
            )
            return None

    def get_modules_raw(self, course: Any) -> list[Any]:
        """
        Get modules for a course from the Canvas API.

        Args:
            course: Canvas course object

        Returns:
            List of raw Canvas module objects
        """
        if not self.canvas or not course:
            logger.warning("Canvas API client or course not available")
            return []

        try:
            return list(course.get_modules())
        except CanvasException as e:
            logger.error(
                f"Canvas API error getting modules for course {course.id}: {e}"
            )
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error getting modules for course {course.id}: {e}"
            )
            return []

    def get_module_items_raw(self, module: Any) -> list[Any]:
        """
        Get items for a module from the Canvas API.

        Args:
            module: Canvas module object

        Returns:
            List of raw Canvas module item objects
        """
        if not self.canvas or not module:
            logger.warning("Canvas API client or module not available")
            return []

        try:
            return list(module.get_module_items())
        except CanvasException as e:
            logger.error(f"Canvas API error getting items for module {module.id}: {e}")
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error getting items for module {module.id}: {e}"
            )
            return []

    def get_announcements_raw(self, course: Any) -> list[Any]:
        """
        Get announcements for a course from the Canvas API.

        Args:
            course: Canvas course object

        Returns:
            List of raw Canvas announcement objects
        """
        if not self.canvas or not course:
            logger.warning("Canvas API client or course not available")
            return []

        try:
            return list(course.get_discussion_topics(only_announcements=True))
        except CanvasException as e:
            logger.error(
                f"Canvas API error getting announcements for course {course.id}: {e}"
            )
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error getting announcements for course {course.id}: {e}"
            )
            return []

    def get_files_raw(self, course: Any) -> list[Any]:
        """
        Get files for a course from the Canvas API.

        Args:
            course: Canvas course object

        Returns:
            List of raw Canvas file objects
        """
        if not self.canvas or not course:
            logger.warning("Canvas API client or course not available")
            return []

        try:
            return list(course.get_files())
        except CanvasException as e:
            logger.error(f"Canvas API error getting files for course {course.id}: {e}")
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error getting files for course {course.id}: {e}"
            )
            return []
