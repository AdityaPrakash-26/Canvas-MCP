"""
Tests for Canvas API client functionality.
"""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from canvas_mcp.canvas_client import CanvasClient, parse_canvas_datetime


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
    client = CanvasClient("https://canvas.example.com", "test_token")
    
    # Check Canvas API was initialized properly
    mock_canvas_api.assert_called_once_with("https://canvas.example.com", "test_token")
    assert client.canvas is not None


def test_get_current_user(mock_canvas_client):
    """Test getting the current user."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Test the method
    user = client.get_current_user()
    
    # Check that Canvas API was called properly
    mock_canvas_client.get_current_user.assert_called_once()
    assert user == mock_canvas_client.get_current_user.return_value


@pytest.mark.parametrize("include_hidden", [True, False])
def test_get_courses(mock_canvas_client, mock_user, include_hidden):
    """Test getting courses from Canvas."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    client.user = mock_user
    
    # Test the method
    courses = client.get_courses(include_hidden=include_hidden)
    
    # Check that Canvas API was called properly
    mock_user.get_courses.assert_called_once_with(include_hidden=include_hidden)
    assert courses == [mock_user.get_courses.return_value[0]]


def test_get_course_by_id(mock_canvas_client):
    """Test getting a specific course by ID."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Configure the mock
    course_id = 12345
    mock_canvas_client.get_course.return_value = MagicMock(id=course_id)
    
    # Test the method
    course = client.get_course_by_id(course_id)
    
    # Check that Canvas API was called properly
    mock_canvas_client.get_course.assert_called_once_with(course_id)
    assert course.id == course_id


def test_get_assignments(mock_canvas_client, mock_course):
    """Test getting assignments for a course."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Test the method
    assignments = client.get_assignments(mock_course)
    
    # Check that Canvas API was called properly
    mock_course.get_assignments.assert_called_once()
    assert assignments == mock_course.get_assignments.return_value


def test_get_modules(mock_canvas_client, mock_course):
    """Test getting modules for a course."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Test the method
    modules = client.get_modules(mock_course)
    
    # Check that Canvas API was called properly
    mock_course.get_modules.assert_called_once()
    assert modules == mock_course.get_modules.return_value


def test_get_module_items(mock_canvas_client, mock_module):
    """Test getting items for a module."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Test the method
    items = client.get_module_items(mock_module)
    
    # Check that Canvas API was called properly
    mock_module.get_module_items.assert_called_once()
    assert items == mock_module.get_module_items.return_value


def test_get_announcements(mock_canvas_client, mock_course, mock_announcement):
    """Test getting announcements for a course."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Configure mock to return an announcement
    mock_announcement.announcement = True
    mock_course.get_discussion_topics.return_value = [mock_announcement]
    
    # Test the method
    announcements = client.get_announcements(mock_course)
    
    # Check that Canvas API was called properly
    mock_course.get_discussion_topics.assert_called_once()
    assert len(announcements) == 1
    assert announcements[0] == mock_announcement


def test_get_discussions(mock_canvas_client, mock_course):
    """Test getting discussions for a course."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    
    # Configure mock to return a discussion (not an announcement)
    discussion = MagicMock()
    discussion.announcement = False
    mock_course.get_discussion_topics.return_value = [discussion]
    
    # Test the method
    discussions = client.get_discussions(mock_course)
    
    # Check that Canvas API was called properly
    mock_course.get_discussion_topics.assert_called_once()
    assert len(discussions) == 1
    assert discussions[0] == discussion
