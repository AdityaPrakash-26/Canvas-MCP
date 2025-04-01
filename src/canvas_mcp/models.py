"""
SQLAlchemy ORM models for the Canvas MCP database schema.
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# Helper function to convert ORM object to dictionary
def orm_to_dict(obj):
    if obj is None:
        return {}
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    canvas_course_id = Column(Integer, unique=True, nullable=False, index=True)
    course_code = Column(String, nullable=True)
    course_name = Column(String, nullable=False)
    instructor = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    syllabus = relationship("Syllabus", back_populates="course", uselist=False, cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="course", cascade="all, delete-orphan")
    user_courses = relationship("UserCourse", back_populates="course", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="course", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="course", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="course", cascade="all, delete-orphan")
    lectures = relationship("Lecture", back_populates="course", cascade="all, delete-orphan")
    files = relationship("File", back_populates="course", cascade="all, delete-orphan")


class Syllabus(Base):
    __tablename__ = "syllabi"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    parsed_content = Column(Text, nullable=True)
    is_parsed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="syllabus")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint('course_id', 'canvas_assignment_id', name='uq_course_assignment'),
        Index('idx_assignments_course_id', 'course_id'),
        Index('idx_assignments_due_date', 'due_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_assignment_id = Column(Integer, nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assignment_type = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    points_possible = Column(Float, nullable=True)
    submission_types = Column(String, nullable=True) # Store as comma-separated string or JSON? Using String for simplicity.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="assignments")


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint('course_id', 'canvas_module_id', name='uq_course_module'),
        Index('idx_modules_course_id', 'course_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_module_id = Column(Integer, nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    unlock_date = Column(DateTime, nullable=True)
    position = Column(Integer, nullable=True)
    require_sequential_progress = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="modules")
    items = relationship("ModuleItem", back_populates="module", cascade="all, delete-orphan", order_by="ModuleItem.position")


class ModuleItem(Base):
    __tablename__ = "module_items"
    __table_args__ = (
        Index('idx_module_items_module_id', 'module_id'),
        Index('idx_module_items_canvas_item_id', 'canvas_item_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    canvas_item_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    item_type = Column(String, nullable=False) # e.g., 'Assignment', 'Page', 'File', 'Discussion', 'Quiz', 'ExternalUrl'
    content_id = Column(Integer, nullable=True) # ID of the associated content (Assignment ID, Page ID, etc.)
    position = Column(Integer, nullable=True)
    url = Column(String, nullable=True) # External URL if item_type is 'ExternalUrl'
    page_url = Column(String, nullable=True) # URL slug if item_type is 'Page'
    content_details = Column(JSON, nullable=True) # Store extra details from Canvas API if needed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    module = relationship("Module", back_populates="items")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        Index('idx_calendar_events_course_id', 'course_id'),
        Index('idx_calendar_events_event_date', 'event_date'),
        Index('idx_calendar_events_source', 'source_type', 'source_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String, nullable=False) # e.g., 'assignment', 'exam', 'lecture'
    source_type = Column(String, nullable=True) # e.g., 'assignment', 'module'
    source_id = Column(Integer, nullable=True) # e.g., Assignment.id
    event_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    all_day = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="calendar_events")


class UserCourse(Base):
    __tablename__ = "user_courses"
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uq_user_course'),
        Index('idx_user_courses_user_id', 'user_id'),
        Index('idx_user_courses_course_id', 'course_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False) # Assuming user ID is a string
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    indexing_opt_out = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="user_courses")


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        Index('idx_announcements_course_id', 'course_id'),
        Index('idx_announcements_canvas_id', 'canvas_announcement_id'),
        Index('idx_announcements_posted_at', 'posted_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_announcement_id = Column(Integer, nullable=True, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    posted_by = Column(String, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="announcements")


class Discussion(Base):
    __tablename__ = "discussions"
    __table_args__ = (
        Index('idx_discussions_course_id', 'course_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_discussion_id = Column(Integer, nullable=True, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    # Add other relevant fields like author, posted_at, etc.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="discussions")


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        Index('idx_grades_course_id', 'course_id'),
        Index('idx_grades_assignment_id', 'assignment_id'),
        # Add user_id index if storing grades per user
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True) # Link to assignment if applicable
    user_id = Column(String, nullable=False) # Identify the user
    score = Column(Float, nullable=True)
    possible_score = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="grades")
    assignment = relationship("Assignment") # Optional relationship


class Lecture(Base):
    __tablename__ = "lectures"
    __table_args__ = (
        Index('idx_lectures_course_id', 'course_id'),
        Index('idx_lectures_date', 'lecture_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    lecture_date = Column(DateTime, nullable=True)
    notes_content = Column(Text, nullable=True)
    transcript_content = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="lectures")


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        Index('idx_files_course_id', 'course_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_file_id = Column(Integer, nullable=True, unique=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size = Column(Integer, nullable=True)
    url = Column(String, nullable=True) # Canvas URL
    # Consider storing file content blob or path if needed locally
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="files")


# Note: Views ('upcoming_deadlines', 'course_summary') are not directly represented as SQLAlchemy models.
# They can be implemented as complex queries using the ORM or potentially using sqlalchemy.sql views if needed.
# For simplicity, we'll recreate the logic of these views using ORM queries in the server code where needed.