"""
Tests for Canvas API client functionality.
"""
from datetime import datetime
from unittest.mock import MagicMock

from canvas_mcp.canvas_client import CanvasClient, parse_canvas_datetime
from canvas_mcp.models import Course


def test_parse_canvas_datetime():
    """Test parsing of Canvas datetime strings."""
    # Test valid datetime
    dt_str = "2023-09-15T23:59:59Z"
    result = parse_canvas_datetime(dt_str)
    assert isinstance(result, datetime)
    assert result.year == 2023
    assert result.month == 9
    assert result.day == 15
    assert result.hour == 23
    assert result.minute == 59
    assert result.second == 59

    # Test None input
    assert parse_canvas_datetime(None) is None

    # Test empty string
    assert parse_canvas_datetime("") is None


def test_canvas_client_initialization(mock_canvas_api):
    """Test Canvas client initialization."""
    # Create client with mock
    client = CanvasClient(api_url="https://canvas.example.com", api_key="test_token")

    # Check Canvas API was initialized properly
    mock_canvas_api.assert_called_once_with("https://canvas.example.com", "test_token")
    assert client.canvas is not None


def test_sync_courses_integration(mock_canvas_client, mock_user, db_session):
    """Test syncing courses from Canvas to the database."""
    # Set up client with mock
    client = CanvasClient(db_session_factory=lambda: db_session)
    client.canvas = mock_canvas_client

    # Configure mock user
    mock_user.id = 12345

    # Configure mock responses with concrete values instead of MagicMock objects
    mock_course1 = MagicMock()
    mock_course1.id = 101
    mock_course1.name = "Test Course 1"
    mock_course1.course_code = "TEST101"
    mock_course1.enrollment_term_id = 1
    mock_course1.public_description = "Test description 1"
    mock_course1.syllabus_body = "Test syllabus 1"
    mock_course1.teachers = []

    # Configure Canvas API mocks
    mock_canvas_client.get_current_user.return_value = mock_user
    mock_user.get_courses.return_value = [mock_course1]
    mock_canvas_client.get_course.return_value = mock_course1

    # Execute the sync
    result = client.sync_courses()

    # Verify the courses were saved in the database
    courses_in_db = db_session.query(Course).filter(
        Course.canvas_course_id == 101
    ).all()
    assert len(courses_in_db) > 0

    # Verify the sync result is a list of course IDs
    assert isinstance(result, list)
    assert len(result) > 0
