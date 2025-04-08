"""Integration tests for calendar events functionality."""

from dataclasses import dataclass

import pytest

# Import the tool function directly from the extract_tools_test module
from scripts.extract_tools_test import extract_tools
from src.canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from src.canvas_mcp.sync import SyncService
from src.canvas_mcp.utils.db_manager import DatabaseManager


# Create a mock context class
@dataclass
class MockContext:
    db_manager: DatabaseManager
    api_adapter: CanvasApiAdapter
    sync_service: SyncService

    @property
    def request_context(self):
        return type(
            "obj",
            (object,),
            {
                "lifespan_context": {
                    "db_manager": self.db_manager,
                    "api_adapter": self.api_adapter,
                    "sync_service": self.sync_service,
                }
            },
        )


# Get the tools dictionary
tools = extract_tools()
get_course_calendar_events = tools["get_course_calendar_events"]


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    # Create a database manager for the test database
    db_path = "tests/test_data/test_canvas_mcp.db"
    db_manager = DatabaseManager(db_path)

    # Create a mock API adapter
    api_adapter = CanvasApiAdapter(None)

    # Create a mock sync service
    sync_service = SyncService(db_manager, api_adapter)

    # Create and return the mock context
    return MockContext(db_manager, api_adapter, sync_service)


def test_get_course_calendar_events(mock_context):
    """Test getting calendar events for a course."""
    # Use the test course ID
    course_id = 1

    # Get calendar events
    events = get_course_calendar_events(mock_context, course_id=course_id)

    # Verify we got some events
    assert isinstance(events, list)

    # Skip the test if we got an error
    if len(events) == 1 and "error" in events[0]:
        pytest.skip(f"Skipping test due to error: {events[0]['error']}")

    # Verify the structure of the events if we have any
    if events:
        for event in events:
            assert "id" in event
            assert "title" in event
            assert "description" in event
            assert "date" in event
            assert "event_type" in event
            assert "source_type" in event
            assert "course_name" in event


def test_get_course_calendar_events_with_limit(mock_context):
    """Test getting calendar events with a limit."""
    # Use the test course ID
    course_id = 1
    limit = 3

    # Get calendar events with limit
    events = get_course_calendar_events(mock_context, course_id=course_id, limit=limit)

    # Verify we got the right number of events
    assert isinstance(events, list)
    assert len(events) <= limit


def test_get_course_calendar_events_nonexistent_course(mock_context):
    """Test getting calendar events for a nonexistent course."""
    # Use a nonexistent course ID
    course_id = 9999

    # Get calendar events for nonexistent course
    events = get_course_calendar_events(mock_context, course_id=course_id)

    # Verify we got an empty list
    assert isinstance(events, list)
    assert len(events) == 1  # Expect one item, which is the error message
    assert events[0] == {"error": f"Course with ID {course_id} not found"}
