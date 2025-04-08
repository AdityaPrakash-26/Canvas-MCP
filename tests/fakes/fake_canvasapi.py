"""
Fake implementation of the canvasapi library for testing.

This module provides fake implementations of Canvas API objects
that return realistic but static data for testing purposes.
"""

import json
from pathlib import Path
from typing import Any

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeCanvasObject:
    """Base class for fake Canvas API objects."""

    def __init__(self, attributes: dict[str, Any]):
        """
        Initialize with attributes dictionary.

        Args:
            attributes: Dictionary of attributes to set on the object
        """
        for key, value in attributes.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access for missing attributes.

        Args:
            name: Attribute name

        Returns:
            None for missing attributes

        Raises:
            AttributeError: If attribute starts with _ (Python internal)
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'"
            )
        return None


class FakeUser(FakeCanvasObject):
    """Fake implementation of Canvas User object."""

    def get_conversations(self, **kwargs) -> list["FakeConversation"]:
        """
        Get conversations for this user.

        Args:
            **kwargs: Optional filtering parameters
                - scope: Filter by scope (unread, starred, archived)
                - filter: Filter by type (sent, received, all)

        Returns:
            List of FakeConversation objects
        """
        # Load conversations from fixture
        conversations_data = _load_fixture("conversations.json")
        conversations = [
            FakeConversation(conv_data) for conv_data in conversations_data
        ]

        # Apply filters
        if kwargs.get("scope"):
            scope = kwargs["scope"]
            if scope == "unread":
                conversations = [
                    c
                    for c in conversations
                    if getattr(c, "workflow_state", "") == "unread"
                ]
            elif scope == "starred":
                conversations = [
                    c for c in conversations if getattr(c, "starred", False)
                ]
            elif scope == "archived":
                conversations = [
                    c
                    for c in conversations
                    if getattr(c, "workflow_state", "") == "archived"
                ]

        return conversations

    def get_courses(self, **kwargs) -> list["FakeCourse"]:
        """
        Get courses for this user.

        Args:
            **kwargs: Optional filtering parameters
                - enrollment_state: Filter by enrollment state
                - enrollment_type: Filter by enrollment type
                - include: Additional information to include
                - state: Filter by course state

        Returns:
            List of FakeCourse objects
        """
        # Load courses from fixture
        courses_data = _load_fixture("courses.json")
        courses = [FakeCourse(course_data) for course_data in courses_data]

        # Apply filters
        if kwargs.get("enrollment_state"):
            enrollment_state = kwargs["enrollment_state"]
            filtered_courses = []

            for course in courses:
                course_enrollment_state = None

                # Get enrollment state from the course
                if hasattr(course, "enrollments") and course.enrollments:
                    course_enrollment_state = course.enrollments[0].get(
                        "enrollment_state"
                    )

                # If enrollment state matches or course has no enrollment state and we're looking for active
                if course_enrollment_state == enrollment_state or (
                    course_enrollment_state is None and enrollment_state == "active"
                ):
                    filtered_courses.append(course)

            courses = filtered_courses

        if kwargs.get("enrollment_type"):
            enrollment_type = kwargs["enrollment_type"]
            courses = [
                c
                for c in courses
                if getattr(c, "enrollment_role", "") == enrollment_type
            ]

        if kwargs.get("state"):
            state = kwargs["state"]
            courses = [c for c in courses if getattr(c, "workflow_state", "") == state]

        return courses


class FakeCourse(FakeCanvasObject):
    """Fake implementation of Canvas Course object."""

    def get_assignments(self, **kwargs) -> list["FakeAssignment"]:
        """
        Get assignments for this course.

        Args:
            **kwargs: Optional filtering parameters
                - assignment_ids: List of assignment IDs to retrieve
                - include: Additional information to include
                - search_term: Search assignments by this term
                - bucket: Filter by assignment bucket (future, overdue, etc.)

        Returns:
            List of FakeAssignment objects
        """
        # Load assignments from fixture based on course ID
        assignments_data = _load_fixture(f"assignments_{self.id}.json")
        if not assignments_data:
            # Fall back to generic assignments if course-specific ones not found
            assignments_data = _load_fixture("assignments.json")

        assignments = [
            FakeAssignment(assignment_data) for assignment_data in assignments_data
        ]

        # Apply filters
        if kwargs.get("assignment_ids"):
            assignment_ids = [str(id) for id in kwargs["assignment_ids"]]
            assignments = [
                a for a in assignments if str(getattr(a, "id", "")) in assignment_ids
            ]

        if kwargs.get("search_term"):
            search_term = kwargs["search_term"].lower()
            assignments = [
                a for a in assignments if search_term in getattr(a, "name", "").lower()
            ]

        if kwargs.get("bucket"):
            # This would require more complex logic to implement properly
            # For now, we'll just return all assignments for any bucket
            pass

        return assignments

    def get_modules(self, **kwargs) -> list["FakeModule"]:
        """
        Get modules for this course.

        Args:
            **kwargs: Optional filtering parameters
                - include: Additional information to include
                - search_term: Search modules by this term

        Returns:
            List of FakeModule objects
        """
        # Load modules from fixture based on course ID
        modules_data = _load_fixture(f"modules_{self.id}.json")
        if not modules_data:
            # Fall back to generic modules if course-specific ones not found
            modules_data = _load_fixture("modules.json")

        modules = [FakeModule(module_data) for module_data in modules_data]

        # Apply filters
        if kwargs.get("search_term"):
            search_term = kwargs["search_term"].lower()
            modules = [
                m for m in modules if search_term in getattr(m, "name", "").lower()
            ]

        return modules

    def get_discussion_topics(self, **kwargs) -> list["FakeDiscussionTopic"]:
        """
        Get discussion topics (announcements) for this course.

        Args:
            **kwargs: Optional filtering parameters
                - only_announcements: Only return announcements
                - search_term: Search topics by this term

        Returns:
            List of FakeDiscussionTopic objects
        """
        # Load announcements from fixture based on course ID
        if kwargs.get("only_announcements"):
            announcements_data = _load_fixture(f"announcements_{self.id}.json")
            if not announcements_data:
                # Fall back to generic announcements if course-specific ones not found
                announcements_data = _load_fixture("announcements.json")
        else:
            # For regular discussion topics
            announcements_data = _load_fixture(f"discussions_{self.id}.json")
            if not announcements_data:
                # Fall back to generic discussions if course-specific ones not found
                announcements_data = _load_fixture("discussions.json")
                # If still no data, use announcements as fallback
                if not announcements_data:
                    announcements_data = _load_fixture(f"announcements_{self.id}.json")
                    if not announcements_data:
                        announcements_data = _load_fixture("announcements.json")

        topics = [
            FakeDiscussionTopic(announcement_data)
            for announcement_data in announcements_data
        ]

        # Apply filters
        if kwargs.get("search_term"):
            search_term = kwargs["search_term"].lower()
            topics = [
                t for t in topics if search_term in getattr(t, "title", "").lower()
            ]

        return topics

    def get_files(self, **kwargs) -> list["FakeFile"]:
        """
        Get files for this course.

        Args:
            **kwargs: Optional filtering parameters
                - content_types: Filter by content type
                - search_term: Search files by this term
                - sort: Sort files by this field

        Returns:
            List of FakeFile objects
        """
        # Load files from fixture based on course ID
        files_data = _load_fixture(f"files_{self.id}.json")
        if not files_data:
            # Fall back to generic files if course-specific ones not found
            files_data = _load_fixture("files.json")

        files = [FakeFile(file_data) for file_data in files_data]

        # Apply filters
        if kwargs.get("content_types"):
            content_types = kwargs["content_types"]
            if isinstance(content_types, str):
                content_types = [content_types]
            files = [
                f for f in files if getattr(f, "content-type", "") in content_types
            ]

        if kwargs.get("search_term"):
            search_term = kwargs["search_term"].lower()
            files = [
                f
                for f in files
                if search_term in getattr(f, "display_name", "").lower()
            ]

        return files


class FakeAssignment(FakeCanvasObject):
    """Fake implementation of Canvas Assignment object."""

    pass


class FakeModule(FakeCanvasObject):
    """Fake implementation of Canvas Module object."""

    def get_module_items(self, **kwargs) -> list["FakeModuleItem"]:
        """
        Get items for this module.

        Args:
            **kwargs: Optional filtering parameters
                - include: Additional information to include
                - search_term: Search items by this term

        Returns:
            List of FakeModuleItem objects
        """
        # Load module items from fixture based on module ID
        items_data = _load_fixture(f"module_items_{self.id}.json")
        if not items_data:
            # Fall back to generic module items if module-specific ones not found
            items_data = _load_fixture("module_items.json")

        items = [FakeModuleItem(item_data) for item_data in items_data]

        # Apply filters
        if kwargs.get("search_term"):
            search_term = kwargs["search_term"].lower()
            items = [i for i in items if search_term in getattr(i, "title", "").lower()]

        return items


class FakeModuleItem(FakeCanvasObject):
    """Fake implementation of Canvas ModuleItem object."""

    pass


class FakeDiscussionTopic(FakeCanvasObject):
    """Fake implementation of Canvas DiscussionTopic object."""

    pass


class FakeFile(FakeCanvasObject):
    """Fake implementation of Canvas File object."""

    pass


class FakeConversation(FakeCanvasObject):
    """Fake implementation of Canvas Conversation object."""

    pass


class FakeCanvas:
    """Fake implementation of canvasapi.Canvas class."""

    def __init__(self, api_url: str, api_key: str):
        """
        Initialize the fake Canvas API client.

        Args:
            api_url: Canvas API URL
            api_key: Canvas API key
        """
        self.api_url = api_url
        self.api_key = api_key

    def get_current_user(self) -> FakeUser:
        """
        Get the current user.

        Returns:
            FakeUser object representing the current user
        """
        # Load user data from fixture
        user_data = _load_fixture("current_user.json")
        if not user_data:
            # Create a default user if fixture not found
            user_data = {
                "id": 1,
                "name": "Test User",
                "email": "test@example.com",
                "login_id": "test_user",
            }

        return FakeUser(user_data)

    def get_course(self, course_id: int | str) -> FakeCourse:
        """
        Get a specific course by ID.

        Args:
            course_id: Course ID

        Returns:
            FakeCourse object
        """
        # Load courses from fixture
        courses_data = _load_fixture("courses.json")

        # Find the course with the matching ID
        for course_data in courses_data:
            if str(course_data.get("id")) == str(course_id):
                return FakeCourse(course_data)

        # If not found, raise exception like the real API would
        raise Exception(f"Course not found: {course_id}")

    def get_user(self, user_id: int | str) -> FakeUser:
        """
        Get a specific user by ID.

        Args:
            user_id: User ID

        Returns:
            FakeUser object
        """
        # For simplicity, just return the current user
        # The user_id parameter is ignored
        return self.get_current_user()

    def get_conversations(self, **kwargs) -> list[FakeConversation]:
        """
        Get conversations from the Canvas API.

        Args:
            **kwargs: Optional filtering parameters

        Returns:
            List of FakeConversation objects
        """
        # Load conversations from fixture
        conversations_data = _load_fixture("conversations.json")
        return [FakeConversation(conv_data) for conv_data in conversations_data]

    def get_conversation(self, conversation_id: int | str) -> FakeConversation:
        """
        Get a specific conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            FakeConversation object
        """
        # First try to load the exact conversation ID
        conversation_data = _load_fixture(f"conversation_{conversation_id}.json")

        # If not found, try with the test conversation IDs (2001, 2002, 2003)
        if not conversation_data:
            # Map real conversation IDs to test conversation IDs
            # This allows us to use the test fixtures for any conversation ID
            test_ids = [2001, 2002, 2003]
            test_id = test_ids[hash(str(conversation_id)) % len(test_ids)]
            conversation_data = _load_fixture(f"conversation_{test_id}.json")

            # If we found a test conversation, update its ID to match the requested ID
            if conversation_data:
                conversation_data["id"] = int(conversation_id)

        if not conversation_data:
            # If still not found, raise exception like the real API would
            raise Exception(f"Conversation not found: {conversation_id}")

        return FakeConversation(conversation_data)


def _load_fixture(filename: str) -> Any:
    """
    Load data from a fixture file.

    Args:
        filename: Name of the fixture file

    Returns:
        Parsed JSON data or empty list if file not found
    """
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        return []

    with open(filepath) as f:
        return json.load(f)


# Create a patch function to replace the real canvasapi with our fake version
def patch_canvasapi():
    """
    Patch the canvasapi module with our fake implementation.

    This function should be called before importing any code that uses canvasapi.
    """
    import sys

    # Create a fake canvasapi module
    class FakeCanvasAPIModule:
        Canvas = FakeCanvas

    # Add it to sys.modules
    sys.modules["canvasapi"] = FakeCanvasAPIModule
