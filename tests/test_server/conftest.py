"""
Server-specific test fixtures.
"""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from canvas_mcp.database import init_db
from canvas_mcp.models import (
    Announcement,
    Assignment,
    Course,
    Module,
    ModuleItem,
    Syllabus,
    UserCourse,
)


@pytest.fixture
def server_session(db_engine):
    """Create a session for server tests with preloaded test data."""
    # Create a session factory bound to the test engine
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    
    # Populate the session with test data
    _populate_test_data(session)
    
    # Patch SessionLocal in the server module to use our test session
    with patch('canvas_mcp.server.SessionLocal', TestingSessionLocal):
        yield session
    
    session.close()


@pytest.fixture
def mock_canvas_client():
    """Mock the canvas_client instance within the server module."""
    with patch('canvas_mcp.server.canvas_client') as mock_client:
        yield mock_client


def _populate_test_data(session):
    """Create test data for server tests."""
    # Current time for assignments
    now = datetime.now()
    
    # Courses
    course1 = Course(
        id=1, # Explicitly set IDs for predictable FKs
        canvas_course_id=12345,
        course_code="CS101",
        course_name="Introduction to Computer Science",
        instructor="Professor Smith",
        description="An introduction to computer science concepts",
        start_date=datetime(2025, 1, 15),
        end_date=datetime(2025, 5, 15)
    )
    course2 = Course(
        id=2,
        canvas_course_id=67890,
        course_code="MATH200",
        course_name="Calculus II",
        instructor="Professor Johnson",
        description="Advanced calculus topics",
        start_date=datetime(2025, 1, 15),
        end_date=datetime(2025, 5, 15)
    )
    session.add_all([course1, course2])
    session.flush() # Assign IDs

    # Syllabi
    syllabus1 = Syllabus(
        id=1, course_id=course1.id, content="<p>This is the CS101 syllabus</p>",
        parsed_content="This is the CS101 syllabus in plain text format.", is_parsed=True
    )
    syllabus2 = Syllabus(
        id=2, course_id=course2.id, content="<p>This is the MATH200 syllabus</p>"
        # No parsed content for this one initially
    )
    session.add_all([syllabus1, syllabus2])

    # Assignments
    assignment1 = Assignment(
        id=1, course_id=course1.id, canvas_assignment_id=101, title="Programming Assignment 1",
        description="Write a simple program in Python", assignment_type="assignment",
        due_date=now + timedelta(days=5), points_possible=100
    )
    assignment2 = Assignment(
        id=2, course_id=course1.id, canvas_assignment_id=102, title="Midterm Exam",
        description="Covers material from weeks 1-7", assignment_type="exam",
        due_date=now + timedelta(days=20), points_possible=200
    )
    assignment3 = Assignment(
        id=3, course_id=course2.id, canvas_assignment_id=201, title="Calculus Problem Set 1",
        description="Problems 1-20 from Chapter 3", assignment_type="assignment",
        due_date=now + timedelta(days=8), points_possible=50
    )
    # Assignment with past due date (should not appear in upcoming)
    assignment4 = Assignment(
        id=4, course_id=course1.id, canvas_assignment_id=100, title="Past Assignment 0",
        description="Already due", assignment_type="assignment",
        due_date=now - timedelta(days=2), points_possible=10
    )
    session.add_all([assignment1, assignment2, assignment3, assignment4])

    # Modules
    module1 = Module(
        id=1, course_id=course1.id, canvas_module_id=301, name="Week 1: Introduction",
        description="Intro concepts", position=1
    )
    module2 = Module(
        id=2, course_id=course1.id, canvas_module_id=302, name="Week 2: Variables",
        description="Data types", position=2
    )
    session.add_all([module1, module2])
    session.flush() # Assign IDs

    # Module Items
    item1 = ModuleItem(
        id=1, module_id=module1.id, canvas_item_id=1001, title="Intro Lecture Notes", 
        item_type="File", position=1, content_details="Some details about the file."
    )
    item2 = ModuleItem(
        id=2, module_id=module1.id, canvas_item_id=1002, title="Setup Python Environment", 
        item_type="Page", position=2, page_url="setup-python"
    )
    item3 = ModuleItem( # Link to an assignment
        id=3, module_id=module2.id, canvas_item_id=1003, title=assignment1.title, 
        item_type="Assignment", position=1, content_id=assignment1.canvas_assignment_id
    )
    session.add_all([item1, item2, item3])

    # Announcements
    announce1 = Announcement(
        id=1, course_id=course1.id, canvas_announcement_id=2001, title="Welcome to CS101",
        content="Read the syllabus.", posted_by="Professor Smith", posted_at=datetime(2025, 1, 10, 9, 0)
    )
    announce2 = Announcement(
         id=2, course_id=course1.id, canvas_announcement_id=2002, title="Office Hours Updated",
         content="Thursdays 2-4pm.", posted_by="Professor Smith", posted_at=datetime(2025, 1, 15, 14, 30)
    )
    session.add_all([announce1, announce2])

    session.commit()
    return None
