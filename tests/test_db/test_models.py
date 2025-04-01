"""
Tests for database models using SQLAlchemy.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from canvas_mcp.models import (
    Assignment,
    Course,
    Module,
    ModuleItem,
    Syllabus,
    Announcement,
    CalendarEvent,
    Discussion,
    Grade,
    Lecture,
    File,
)


def test_course_model(db_session):
    """Test Course model creation and constraints."""
    # Test basic course creation
    course = Course(
        canvas_course_id=12345,
        course_code="CS101",
        course_name="Introduction to Computer Science",
        instructor="Dr. Smith",
        description="Learn the basics of computer science",
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(days=90)).date()
    )
    db_session.add(course)
    db_session.commit()
    
    # Test retrieval
    retrieved = db_session.query(Course).filter_by(canvas_course_id=12345).one()
    assert retrieved.course_name == "Introduction to Computer Science"
    assert retrieved.course_code == "CS101"
    
    # Test unique constraint on canvas_course_id
    duplicate = Course(
        canvas_course_id=12345,  # Same as existing course
        course_code="CS102",
        course_name="Another Course",
        instructor="Dr. Jones",
        description="Another course description",
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(days=90)).date()
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_assignment_model(db_session, sample_course):
    """Test Assignment model creation and relationships."""
    # Test assignment creation
    assignment = Assignment(
        course_id=sample_course.id,
        canvas_assignment_id=12345,
        title="Midterm Project",
        description="A comprehensive project",
        assignment_type="project",
        due_date=datetime.now() + timedelta(days=14),
        points_possible=50
    )
    db_session.add(assignment)
    db_session.commit()
    
    # Test retrieval
    retrieved = db_session.query(Assignment).filter_by(canvas_assignment_id=12345).one()
    assert retrieved.title == "Midterm Project"
    assert retrieved.points_possible == 50
    
    # Test relationship with course
    assert retrieved.course.id == sample_course.id
    assert retrieved.course.course_name == sample_course.course_name
    
    # Test course.assignments relationship
    course = db_session.query(Course).filter_by(id=sample_course.id).one()
    assert len(course.assignments) == 2  # One from sample_assignment fixture, one from this test
    assert any(a.title == "Midterm Project" for a in course.assignments)


def test_module_and_items(db_session, sample_course):
    """Test Module and ModuleItem models and their relationships."""
    # Create a module
    module = Module(
        course_id=sample_course.id,
        canvas_module_id=54321,
        name="Week 1",
        position=1
    )
    db_session.add(module)
    db_session.commit()
    
    # Create module items
    items = [
        ModuleItem(
            module_id=module.id,
            canvas_module_item_id=100 + i,
            title=f"Item {i}",
            item_type="Assignment" if i % 2 == 0 else "Page",
            position=i,
            content_id=200 + i
        )
        for i in range(1, 4)
    ]
    db_session.add_all(items)
    db_session.commit()
    
    # Test retrieval
    retrieved_module = db_session.query(Module).filter_by(canvas_module_id=54321).one()
    assert retrieved_module.name == "Week 1"
    assert len(retrieved_module.items) == 3
    
    # Test ordering by position
    sorted_items = sorted(retrieved_module.items, key=lambda x: x.position)
    assert [item.title for item in sorted_items] == ["Item 1", "Item 2", "Item 3"]
    
    # Test course relationship
    assert retrieved_module.course.id == sample_course.id


def test_syllabus_model(db_session, sample_course):
    """Test Syllabus model and relationship with Course."""
    # Create a syllabus
    syllabus = Syllabus(
        course_id=sample_course.id,
        content="<h1>Course Syllabus</h1><p>This is the course syllabus.</p>"
    )
    db_session.add(syllabus)
    db_session.commit()
    
    # Test retrieval
    retrieved = db_session.query(Syllabus).filter_by(course_id=sample_course.id).one()
    assert "<h1>Course Syllabus</h1>" in retrieved.content
    
    # Test course relationship
    assert retrieved.course.id == sample_course.id
    
    # Test course.syllabus relationship
    course = db_session.query(Course).filter_by(id=sample_course.id).one()
    assert course.syllabus is not None
    assert course.syllabus.content == syllabus.content


def test_announcement_model(db_session, sample_course):
    """Test Announcement model and relationship with Course."""
    # Create an announcement
    announcement = Announcement(
        course_id=sample_course.id,
        canvas_announcement_id=9876,
        title="Important Announcement",
        message="Class is canceled tomorrow",
        posted_at=datetime.now(),
        author="Professor Smith"
    )
    db_session.add(announcement)
    db_session.commit()
    
    # Test retrieval
    retrieved = db_session.query(Announcement).filter_by(canvas_announcement_id=9876).one()
    assert retrieved.title == "Important Announcement"
    assert retrieved.author == "Professor Smith"
    
    # Test course relationship
    assert retrieved.course.id == sample_course.id
    
    # Test course.announcements relationship
    course = db_session.query(Course).filter_by(id=sample_course.id).one()
    assert len(course.announcements) >= 1
    assert any(a.title == "Important Announcement" for a in course.announcements)
