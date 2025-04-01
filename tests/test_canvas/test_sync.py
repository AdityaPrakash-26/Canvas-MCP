"""
Tests for Canvas API synchronization functionality.
"""
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.models import (
    Course,
    Assignment,
    Module,
    ModuleItem,
    Syllabus,
    Announcement
)


@pytest.fixture
def canvas_client(mock_canvas_client):
    """Create a Canvas client with mock API."""
    client = CanvasClient("https://canvas.example.com", "test_token")
    client.canvas = mock_canvas_client
    return client


def test_sync_course(canvas_client, mock_course, db_session):
    """Test syncing a course from Canvas to the database."""
    # Execute the sync
    result = canvas_client.sync_course(mock_course, db_session)
    
    # Verify the course was created in the database
    course = db_session.query(Course).filter_by(canvas_course_id=mock_course.id).first()
    assert course is not None
    assert course.course_name == mock_course.name
    assert course.course_code == mock_course.course_code
    
    # Verify the syllabus was created
    syllabus = db_session.query(Syllabus).filter_by(course_id=course.id).first()
    assert syllabus is not None
    assert syllabus.content == mock_course.syllabus_body
    
    # Verify the sync result
    assert result["status"] == "success"
    assert "course_id" in result
    assert result["course_id"] == course.id


def test_sync_assignments(canvas_client, mock_course, mock_assignment, db_session, sample_course):
    """Test syncing assignments from Canvas to the database."""
    # Execute the sync
    result = canvas_client.sync_assignments(mock_course, sample_course.id, db_session)
    
    # Verify the assignment was created in the database
    assignment = db_session.query(Assignment).filter_by(canvas_assignment_id=mock_assignment.id).first()
    assert assignment is not None
    assert assignment.title == mock_assignment.name
    assert assignment.description == mock_assignment.description
    assert assignment.course_id == sample_course.id
    
    # Verify the sync result
    assert result["status"] == "success"
    assert "count" in result
    assert result["count"] == 1
    

def test_sync_modules(canvas_client, mock_course, mock_module, mock_module_item, db_session, sample_course):
    """Test syncing modules from Canvas to the database."""
    # Execute the sync
    result = canvas_client.sync_modules(mock_course, sample_course.id, db_session)
    
    # Verify the module was created in the database
    module = db_session.query(Module).filter_by(canvas_module_id=mock_module.id).first()
    assert module is not None
    assert module.name == mock_module.name
    assert module.position == mock_module.position
    assert module.course_id == sample_course.id
    
    # Verify the module item was created
    module_item = db_session.query(ModuleItem).filter_by(
        canvas_module_item_id=mock_module_item.id
    ).first()
    assert module_item is not None
    assert module_item.title == mock_module_item.title
    assert module_item.item_type == mock_module_item.type
    assert module_item.module_id == module.id
    
    # Verify the sync result
    assert result["status"] == "success"
    assert "modules_count" in result
    assert result["modules_count"] == 1
    assert "items_count" in result
    assert result["items_count"] == 1


def test_sync_announcements(canvas_client, mock_course, mock_announcement, db_session, sample_course):
    """Test syncing announcements from Canvas to the database."""
    # Mock the Canvas client's get_announcements method to return our mock announcement
    canvas_client.get_announcements = MagicMock(return_value=[mock_announcement])
    
    # Execute the sync
    result = canvas_client.sync_announcements(mock_course, sample_course.id, db_session)
    
    # Verify the announcement was created in the database
    announcement = db_session.query(Announcement).filter_by(
        canvas_announcement_id=mock_announcement.id
    ).first()
    assert announcement is not None
    assert announcement.title == mock_announcement.title
    assert announcement.message == mock_announcement.message
    assert announcement.course_id == sample_course.id
    
    # Verify the sync result
    assert result["status"] == "success"
    assert "count" in result
    assert result["count"] == 1


def test_sync_all(canvas_client, mock_user, mock_course, db_session):
    """Test syncing all Canvas data to the database."""
    # Mock the individual sync methods to isolate the test
    canvas_client.user = mock_user
    canvas_client.get_courses = MagicMock(return_value=[mock_course])
    canvas_client.sync_course = MagicMock(return_value={"status": "success", "course_id": 1})
    canvas_client.sync_assignments = MagicMock(return_value={"status": "success", "count": 5})
    canvas_client.sync_modules = MagicMock(return_value={"status": "success", "modules_count": 3, "items_count": 10})
    canvas_client.sync_announcements = MagicMock(return_value={"status": "success", "count": 2})
    
    # Execute the sync
    result = canvas_client.sync_all(db_session)
    
    # Verify the methods were called with the expected parameters
    canvas_client.get_courses.assert_called_once()
    canvas_client.sync_course.assert_called_once_with(mock_course, db_session)
    canvas_client.sync_assignments.assert_called_once()
    canvas_client.sync_modules.assert_called_once()
    canvas_client.sync_announcements.assert_called_once()
    
    # Verify the sync result
    assert result["status"] == "success"
    assert "courses_count" in result
    assert result["courses_count"] == 1
    assert "assignments_count" in result
    assert result["assignments_count"] == 5
    assert "modules_count" in result
    assert result["modules_count"] == 3
    assert "module_items_count" in result
    assert result["module_items_count"] == 10
    assert "announcements_count" in result
    assert result["announcements_count"] == 2


def test_sync_error_handling(canvas_client, mock_course, db_session, sample_course):
    """Test error handling during synchronization."""
    # Mock the sync_assignments method to raise an exception
    canvas_client.sync_assignments = MagicMock(side_effect=Exception("Test error"))
    
    # Execute the sync
    result = canvas_client.sync_all(db_session)
    
    # Verify the error is captured in the result
    assert result["status"] == "error"
    assert "error" in result
    assert "Test error" in result["error"]
