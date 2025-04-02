"""
Configuration file for pytest.
"""
import os
import sys
import tempfile
from typing import Generator, Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

from canvas_mcp.database import Base, init_db
from canvas_mcp.models import (
    Announcement,
    Assignment,
    CalendarEvent,
    Course,
    Module,
    ModuleItem,
    Syllabus,
)

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Database fixtures
@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    """Create a temporary SQLite database engine for testing."""
    # Create a temporary file for the test database
    temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = temp_db_file.name
    temp_db_file.close()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    
    # Initialize the database
    init_db(engine)
    
    yield engine
    
    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    yield session
    
    session.close()


# Mock Canvas API fixtures
@pytest.fixture
def mock_canvas() -> MagicMock:
    """Create a mock Canvas API client."""
    canvas = MagicMock()
    return canvas


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock Canvas user."""
    user = MagicMock()
    user.id = 12345
    return user


@pytest.fixture
def mock_course() -> MagicMock:
    """Create a mock Canvas course."""
    course = MagicMock()
    course.id = 67890
    course.name = "Test Course"
    course.course_code = "TST101"
    course.enrollment_term_id = 1
    course.start_at = "2023-08-28T00:00:00Z"
    course.end_at = "2023-12-15T00:00:00Z"
    course.teachers = [{"display_name": "Professor Smith"}]
    course.public_description = "Test course description"
    course.syllabus_body = "<p>Test syllabus content</p>"
    return course


@pytest.fixture
def mock_assignment() -> MagicMock:
    """Create a mock Canvas assignment."""
    assignment = MagicMock()
    assignment.id = 54321
    assignment.name = "Test Assignment"
    assignment.description = "Test assignment description"
    assignment.due_at = "2023-09-15T23:59:59Z"
    assignment.points_possible = 100
    assignment.submission_types = ["online_upload"]
    assignment.unlock_at = None
    assignment.lock_at = None
    return assignment


@pytest.fixture
def mock_module() -> MagicMock:
    """Create a mock Canvas module."""
    module = MagicMock()
    module.id = 98765
    module.name = "Test Module"
    module.position = 1
    module.unlock_at = None
    module.require_sequential_progress = False
    return module


@pytest.fixture
def mock_module_item() -> MagicMock:
    """Create a mock Canvas module item."""
    item = MagicMock()
    item.id = 43210
    item.title = "Test Module Item"
    item.type = "Assignment"
    item.position = 1
    item.content_id = 54321
    item.page_url = None
    item.external_url = None
    return item


@pytest.fixture
def mock_announcement() -> MagicMock:
    """Create a mock Canvas announcement."""
    announcement = MagicMock()
    announcement.id = 24680
    announcement.title = "Test Announcement"
    announcement.message = "Test announcement message"
    announcement.posted_at = "2023-08-30T10:00:00Z"
    announcement.author = {"display_name": "Professor Smith"}
    announcement.announcement = True
    return announcement


# Test data fixtures
@pytest.fixture
def sample_course(db_session: Session) -> Course:
    """Create a sample course in the database for testing."""
    from datetime import datetime, date
    
    course = Course(
        canvas_course_id=67890,
        course_code="TST101",
        course_name="Test Course",
        instructor="Professor Smith",
        description="Test course description",
        start_date=date(2023, 8, 28),
        end_date=date(2023, 12, 15)
    )
    db_session.add(course)
    db_session.commit()
    return course


@pytest.fixture
def sample_assignment(db_session: Session, sample_course: Course) -> Assignment:
    """Create a sample assignment in the database for testing."""
    from datetime import datetime
    from canvas_mcp.canvas_client import parse_canvas_datetime
    
    # Parse ISO date format or create a datetime directly
    due_date = datetime(2023, 9, 15, 23, 59, 59)
    
    assignment = Assignment(
        course_id=sample_course.id,
        canvas_assignment_id=54321,
        title="Test Assignment",
        description="Test assignment description",
        assignment_type="assignment",
        due_date=due_date,
        points_possible=100
    )
    db_session.add(assignment)
    db_session.commit()
    return assignment


@pytest.fixture
def sample_module(db_session: Session, sample_course: Course) -> Module:
    """Create a sample module in the database for testing."""
    module = Module(
        course_id=sample_course.id,
        canvas_module_id=98765,
        name="Test Module",
        position=1
    )
    db_session.add(module)
    db_session.commit()
    return module


@pytest.fixture
def sample_module_item(db_session: Session, sample_module: Module) -> ModuleItem:
    """Create a sample module item in the database for testing."""
    module_item = ModuleItem(
        module_id=sample_module.id,
        canvas_module_item_id=43210,
        title="Test Module Item",
        item_type="Assignment",
        position=1,
        content_id=54321
    )
    db_session.add(module_item)
    db_session.commit()
    return module_item


@pytest.fixture
def sample_syllabus(db_session: Session, sample_course: Course) -> Syllabus:
    """Create a sample syllabus in the database for testing."""
    syllabus = Syllabus(
        course_id=sample_course.id,
        content="<p>Test syllabus content</p>"
    )
    db_session.add(syllabus)
    db_session.commit()
    return syllabus


@pytest.fixture
def sample_announcement(db_session: Session, sample_course: Course) -> Announcement:
    """Create a sample announcement in the database for testing."""
    from datetime import datetime
    
    announcement = Announcement(
        course_id=sample_course.id,
        canvas_announcement_id=24680,
        title="Test Announcement",
        content="Test announcement message",  # Changed from message to content to match model
        posted_at=datetime(2023, 8, 30, 10, 0, 0),
        posted_by="Professor Smith"  # Changed from author to posted_by to match model
    )
    db_session.add(announcement)
    db_session.commit()
    return announcement
