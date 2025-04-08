"""
Canvas Sync Service

This module provides the main orchestrator for synchronizing data between
the Canvas API and the local database.
"""

import logging
from functools import wraps

from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.utils.db_manager import DatabaseManager

# Import helper functions
from canvas_mcp.sync.announcements import _persist_announcements
from canvas_mcp.sync.assignments import _get_courses_to_sync, _persist_assignments
from canvas_mcp.sync.courses import (
    _filter_courses_by_term,
    _persist_courses_and_syllabi,
)
from canvas_mcp.sync.modules import _persist_modules_and_items

# Import public methods
from canvas_mcp.sync.all import _get_assignment_type, sync_all
from canvas_mcp.sync.announcements import sync_announcements
from canvas_mcp.sync.assignments import sync_assignments
from canvas_mcp.sync.courses import sync_courses
from canvas_mcp.sync.modules import sync_modules

# Configure logging
logger = logging.getLogger(__name__)


class SyncService:
    """
    Service for synchronizing data between Canvas API and the local database.

    This class orchestrates the data flow between the Canvas API adapter,
    Pydantic models for validation, and the database for persistence.
    """

    def __init__(self, db_manager: DatabaseManager, api_adapter: CanvasApiAdapter):
        """
        Initialize the sync service.

        Args:
            db_manager: Database manager for database operations
            api_adapter: Canvas API adapter for API interactions
        """
        self.db_manager = db_manager
        self.api_adapter = api_adapter

        # Bind methods to the instance
        self.sync_all = sync_all.__get__(self)
        self.sync_announcements = sync_announcements.__get__(self)
        self.sync_assignments = sync_assignments.__get__(self)
        self.sync_courses = sync_courses.__get__(self)
        self.sync_modules = sync_modules.__get__(self)
        self._get_assignment_type = _get_assignment_type.__get__(self)
        self._filter_courses_by_term = _filter_courses_by_term.__get__(self)

        # Wrap database methods with connection management
        self._persist_announcements = self._wrap_with_connection(_persist_announcements)
        self._get_courses_to_sync = self._wrap_with_connection(_get_courses_to_sync)
        self._persist_assignments = self._wrap_with_connection(_persist_assignments)
        self._persist_courses_and_syllabi = self._wrap_with_connection(
            _persist_courses_and_syllabi
        )
        self._persist_modules_and_items = self._wrap_with_connection(
            _persist_modules_and_items
        )

    def _wrap_with_connection(self, func):
        """Wrap a function with database connection management."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.db_manager.with_connection(func)(self, *args, **kwargs)

        return wrapper

    # Backward compatibility methods have been removed as part of the refactoring
