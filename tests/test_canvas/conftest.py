"""
Canvas-specific test fixtures.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_canvas_api():
    """Create a mock for the canvasapi module."""
    with patch('canvas_mcp.canvas_client.Canvas') as mock_canvas:
        yield mock_canvas


@pytest.fixture
def mock_canvas_client(mock_canvas_api, mock_user, mock_course, mock_assignment, mock_module, mock_module_item, mock_announcement):
    """Create a mock Canvas client with pre-configured responses."""
    # Configure the mock Canvas instance
    mock_canvas_instance = mock_canvas_api.return_value
    
    # Configure the mock user
    mock_canvas_instance.get_current_user.return_value = mock_user
    
    # Configure mock courses
    mock_user.get_courses.return_value = [mock_course]
    
    # Configure mock assignments
    mock_course.get_assignments.return_value = [mock_assignment]
    
    # Configure mock modules
    mock_course.get_modules.return_value = [mock_module]
    
    # Configure mock module items
    mock_module.get_module_items.return_value = [mock_module_item]
    
    # Configure mock announcements
    mock_course.get_discussion_topics.return_value = [mock_announcement]
    
    return mock_canvas_instance
