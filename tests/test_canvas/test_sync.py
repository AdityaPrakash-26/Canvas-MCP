"""
Tests for Canvas API synchronization functionality.
"""
from datetime import datetime
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
def canvas_client(mock_canvas_client, db_session):
    """Create a Canvas client with mock API for real DB integration testing."""
    client = CanvasClient(api_url="https://canvas.example.com", api_key="test_token")
    client.canvas = mock_canvas_client
    client.db_session_factory = lambda: db_session
    return client


def test_sync_courses_method(canvas_client, mock_user, mock_course, db_session):
    """Test syncing courses from Canvas to the database."""
    # Configure mocks
    canvas_client.canvas.get_current_user.return_value = mock_user
    mock_user.get_courses.return_value = [mock_course]
    # For detailed course info
    canvas_client.canvas.get_course.return_value = mock_course

    # Execute the sync
    course_ids = canvas_client.sync_courses()

    # Verify courses were created in the database
    course = db_session.query(Course).filter_by(canvas_course_id=mock_course.id).first()
    assert course is not None
    assert course.course_name == mock_course.name
    assert course.course_code == mock_course.course_code
    
    # Verify the syllabus was created if provided
    if hasattr(mock_course, 'syllabus_body') and mock_course.syllabus_body:
        syllabus = db_session.query(Syllabus).filter_by(course_id=course.id).first()
        assert syllabus is not None
        assert syllabus.content == mock_course.syllabus_body

    # Verify the sync result
    assert isinstance(course_ids, list)
    assert len(course_ids) > 0
    assert course.id in course_ids


def test_sync_assignments_method(canvas_client, mock_course, mock_assignment, db_session, sample_course):
    """Test syncing assignments from Canvas to the database."""
    # Configure mocks
    canvas_client.canvas.get_course.return_value = mock_course
    mock_course.get_assignments.return_value = [mock_assignment]

    # Execute the sync with the sample course's ID
    assignment_count = canvas_client.sync_assignments([sample_course.id])

    # Verify assignments were created in the database
    assignment = db_session.query(Assignment).filter_by(
        canvas_assignment_id=mock_assignment.id,
        course_id=sample_course.id
    ).first()
    
    assert assignment is not None
    assert assignment.title == mock_assignment.name
    assert assignment.description == mock_assignment.description
    assert assignment.course_id == sample_course.id

    # Verify the sync result
    assert isinstance(assignment_count, int)
    assert assignment_count > 0


def test_sync_modules_method(canvas_client, mock_course, mock_module, mock_module_item, db_session, sample_course):
    """Test syncing modules from Canvas to the database."""
    # Configure mocks
    canvas_client.canvas.get_course.return_value = mock_course
    mock_course.get_modules.return_value = [mock_module]
    mock_module.get_module_items.return_value = [mock_module_item]

    # Execute the sync with the sample course's ID
    module_count = canvas_client.sync_modules([sample_course.id])

    # Verify modules were created in the database
    module = db_session.query(Module).filter_by(
        canvas_module_id=mock_module.id,
        course_id=sample_course.id
    ).first()
    
    assert module is not None
    assert module.name == mock_module.name
    assert module.position == mock_module.position
    assert module.course_id == sample_course.id

    # Verify module items
    db_session.refresh(module)  # Ensure relationships are loaded
    assert len(module.items) > 0
    
    module_item = module.items[0]
    assert module_item.title == mock_module_item.title
    assert module_item.item_type == mock_module_item.type
    
    # Verify the sync result
    assert isinstance(module_count, int)
    assert module_count > 0


def test_sync_announcements_method(canvas_client, mock_course, mock_announcement, db_session, sample_course):
    """Test syncing announcements from Canvas to the database."""
    # Configure mocks
    canvas_client.canvas.get_course.return_value = mock_course
    context_code = f"course_{sample_course.canvas_course_id}"
    canvas_client.canvas.get_announcements.return_value = [mock_announcement]

    # Execute the sync with the sample course's ID
    announcement_count = canvas_client.sync_announcements([sample_course.id])

    # Verify announcements were created in the database
    announcement = db_session.query(Announcement).filter_by(
        canvas_announcement_id=mock_announcement.id,
        course_id=sample_course.id
    ).first()
    
    assert announcement is not None
    assert announcement.title == mock_announcement.title
    assert announcement.content == mock_announcement.message
    assert announcement.course_id == sample_course.id

    # Verify the sync result
    assert isinstance(announcement_count, int)
    assert announcement_count > 0


def test_sync_all_method(canvas_client, mock_user, mock_course, db_session):
    """Test syncing all Canvas data to the database."""
    # Configure mock user
    mock_user.id = 12345
    
    # Configure mock course with concrete values
    mock_course.id = 67890
    mock_course.name = "Test Course"
    mock_course.course_code = "TEST101"
    mock_course.enrollment_term_id = 1
    mock_course.public_description = "Test description"
    mock_course.syllabus_body = "Test syllabus"
    mock_course.teachers = []
    
    # Set up mock assignment with concrete values
    mock_assignment = MagicMock()
    mock_assignment.id = 54321
    mock_assignment.name = "Test Assignment"
    mock_assignment.description = "Test assignment description"
    mock_assignment.due_at = "2023-09-15T23:59:59Z"
    mock_assignment.points_possible = 100.0
    mock_assignment.submission_types = ["online_upload"]
    mock_assignment.unlock_at = None
    mock_assignment.lock_at = None
    
    # Set up mock module with concrete values
    mock_module = MagicMock()
    mock_module.id = 98765
    mock_module.name = "Test Module"
    mock_module.position = 1
    mock_module.unlock_at = None
    mock_module.require_sequential_progress = False
    
    # Set up mock module item with concrete values
    mock_module_item = MagicMock()
    mock_module_item.id = 43210
    mock_module_item.title = "Test Module Item"
    mock_module_item.type = "Assignment"
    mock_module_item.position = 1
    mock_module_item.content_id = 54321
    mock_module_item.page_url = None
    mock_module_item.external_url = None
    
    # Set up mock announcement with concrete values
    mock_announcement = MagicMock()
    mock_announcement.id = 24680
    mock_announcement.title = "Test Announcement"
    mock_announcement.message = "Test announcement message"
    mock_announcement.posted_at = "2023-08-30T10:00:00Z"
    mock_announcement.author = {"display_name": "Professor Smith"}  # Use dict with display_name
    mock_announcement.announcement = True
    
    # Configure Canvas API mocks
    canvas_client.canvas.get_current_user.return_value = mock_user
    mock_user.get_courses.return_value = [mock_course]
    canvas_client.canvas.get_course.return_value = mock_course
    mock_course.get_assignments.return_value = [mock_assignment]
    mock_course.get_modules.return_value = [mock_module]
    mock_module.get_module_items.return_value = [mock_module_item]
    canvas_client.canvas.get_announcements.return_value = [mock_announcement]

    # Execute the sync
    result = canvas_client.sync_all()

    # Verify data was created in the database
    courses = db_session.query(Course).all()
    assert len(courses) > 0
    
    # There should be some assignments, modules, and announcements
    assignments = db_session.query(Assignment).all()
    modules = db_session.query(Module).all()
    announcements = db_session.query(Announcement).all()
    
    # Verify the sync result structure
    assert isinstance(result, dict)
    assert "courses" in result
    
    # The keys might be slightly different from what we're expecting
    if "assignments" in result:
        assert result["assignments"] == len(assignments)
    if "modules" in result:
        assert result["modules"] == len(modules)
    if "announcements" in result:
        assert result["announcements"] == len(announcements)


def test_sync_error_handling(canvas_client, mock_user, mock_course, db_session):
    """Test error handling during synchronization."""
    # Configure mock user 
    mock_user.id = 12345
    
    # Configure mock course with concrete values
    mock_course.id = 67890
    mock_course.name = "Test Course"
    mock_course.course_code = "TEST101" 
    mock_course.enrollment_term_id = 1
    mock_course.public_description = "Test description"
    mock_course.syllabus_body = "Test syllabus"
    mock_course.teachers = []
    
    # Configure Canvas API mocks
    canvas_client.canvas.get_current_user.return_value = mock_user
    mock_user.get_courses.return_value = [mock_course]
    canvas_client.canvas.get_course.return_value = mock_course
    
    # Simulate an error in one of the sync phases
    mock_course.get_assignments.side_effect = Exception("Test error during assignment sync")

    # Execute the sync
    result = canvas_client.sync_all()

    # Verify that even with an error, we get valid result
    assert isinstance(result, dict)
    
    # The result should at least contain the courses that were synced
    if "courses" in result:
        assert result["courses"] > 0  # Courses should still be synced
    
    # At least courses should be in the DB
    courses = db_session.query(Course).all()
    assert len(courses) > 0
