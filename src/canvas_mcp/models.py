"""
Pydantic models for Canvas MCP data.

This module defines the data models used for validating and transforming data
between the Canvas API and the local database.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DBCourse(BaseModel):
    """Model for a course in the database."""

    canvas_course_id: int = Field(..., alias="id")
    course_code: str
    course_name: str = Field(..., alias="name")
    instructor: str | None = None
    description: str | None = None
    start_date: datetime | None = Field(None, alias="start_at")
    end_date: datetime | None = Field(None, alias="end_at")
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("course_name", "course_code")
    @classmethod
    def validate_required_text(cls, v: str | None) -> str:
        """Ensure required text fields are not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Field cannot be None or empty")
        return v

    @field_validator("instructor")
    @classmethod
    def extract_instructor(cls, v: str | None, values: dict[str, Any]) -> str | None:
        """Extract instructor name from course data if not provided."""
        if v is not None:
            return v

        # Try to extract from other fields if available
        # This is a placeholder - in a real implementation, you might
        # extract from teachers list or other course attributes
        return None


class DBSyllabus(BaseModel):
    """Model for a syllabus in the database."""

    course_id: int
    content: str | None = None
    content_type: str = "html"
    parsed_content: str | None = None
    is_parsed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"


class DBAssignment(BaseModel):
    """Model for an assignment in the database."""

    course_id: int
    canvas_assignment_id: int = Field(..., alias="id")
    title: str = Field(..., alias="name")
    description: str | None = None
    assignment_type: str | None = None
    due_date: datetime | None = Field(None, alias="due_at")
    available_from: datetime | None = Field(None, alias="unlock_at")
    available_until: datetime | None = Field(None, alias="lock_at")
    points_possible: float | None = None
    submission_types: str | None = None
    source_type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Ensure title is not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Title cannot be None or empty")
        return v

    @field_validator("submission_types")
    @classmethod
    def convert_submission_types(cls, v: Any) -> str | None:
        """Convert submission_types from list to comma-separated string."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return ",".join(v)
        return str(v)


class DBModule(BaseModel):
    """Model for a module in the database."""

    course_id: int
    canvas_module_id: int = Field(..., alias="id")
    name: str
    description: str | None = None
    unlock_date: datetime | None = Field(None, alias="unlock_at")
    position: int | None = None
    require_sequential_progress: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str:
        """Ensure name is not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Name cannot be None or empty")
        return v

    @field_validator("require_sequential_progress")
    @classmethod
    def convert_bool(cls, v: Any) -> bool:
        """Convert various values to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return v != 0
        if isinstance(v, str):
            return v.lower() in ("true", "t", "yes", "y", "1")
        return bool(v)


class DBModuleItem(BaseModel):
    """Model for a module item in the database."""

    # module_id will be set during persistence, not validation from API
    module_id: int | None = None # Made optional for initial validation
    canvas_module_id: int | None = None # Temporary field for linking
    canvas_item_id: int = Field(..., alias="id")
    title: str | None = None
    item_type: str | None = Field(None, alias="type")
    position: int | None = None
    url: str | None = Field(None, alias="external_url")
    page_url: str | None = None
    content_details: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"


class DBAnnouncement(BaseModel):
    """Model for an announcement in the database."""

    course_id: int
    canvas_announcement_id: int = Field(..., alias="id")
    title: str
    content: str | None = Field(None, alias="message")
    posted_by: str | None = Field(None, alias="author_name")
    posted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Ensure title is not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Title cannot be None or empty")
        return v


class DBConversation(BaseModel):
    """Model for a conversation in the database."""

    course_id: int
    canvas_conversation_id: int = Field(..., alias="id")
    title: str
    content: str | None = None
    posted_by: str | None = None  # Will store author name, not ID
    posted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Ensure title is not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Title cannot be None or empty")
        return v

    @field_validator("posted_by")
    @classmethod
    def extract_author(cls, v: str | None) -> str | None:
        """Extract author name from announcement data if not provided."""
        if v is not None:
            return v

        # In a real implementation, you might extract from author object
        # This is a placeholder
        return None


class DBCalendarEvent(BaseModel):
    """Model for a calendar event in the database."""

    course_id: int
    title: str
    description: str | None = None
    event_type: str
    source_type: str
    source_id: int
    event_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = datetime.now()

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Ensure title is not None or empty."""
        if v is None or v.strip() == "":
            raise ValueError("Title cannot be None or empty")
        return v
