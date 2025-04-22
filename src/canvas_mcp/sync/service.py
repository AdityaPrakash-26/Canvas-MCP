"""
Canvas Sync Service

This module provides the main orchestrator for synchronizing data between
the Canvas API and the local database.
"""

import asyncio  # Add asyncio import
import logging

from canvas_mcp.canvas_api_adapter import CanvasApiAdapter

# Import public methods
from canvas_mcp.sync.all import _get_assignment_type, sync_all

# Import helper functions
from canvas_mcp.sync.announcements import sync_announcements
from canvas_mcp.sync.assignments import (
    sync_assignments,
)
from canvas_mcp.sync.conversations import sync_conversations
from canvas_mcp.sync.courses import (
    _filter_courses_by_term,
    sync_courses,
)
from canvas_mcp.sync.modules import sync_modules
from canvas_mcp.utils.db_manager import DatabaseManager

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
        # Define semaphore - adjust limit based on known Canvas limits
        # CRITICAL: Determine the actual rate limit of your Canvas instance!
        self.api_semaphore = asyncio.Semaphore(
            10
        )  # Example: Limit to 10 concurrent API calls
        logger.info(f"API concurrency limited to {self.api_semaphore._value} calls.")

        # Bind methods to the instance - these will be converted to async below
        self.sync_all = sync_all.__get__(self)
        self.sync_announcements = sync_announcements.__get__(self)
        self.sync_assignments = sync_assignments.__get__(self)
        self.sync_conversations = sync_conversations.__get__(self)
        self.sync_courses = sync_courses.__get__(self)
        self.sync_modules = sync_modules.__get__(self)

        # Keep helper methods if they don't involve direct DB/API calls or are pure logic
        self._get_assignment_type = _get_assignment_type.__get__(self)
        self._filter_courses_by_term = _filter_courses_by_term.__get__(self)

        # NOTE: Persistence methods (_persist_*) are now plain functions called via run_db_persist_in_thread
        # They are no longer bound to the service instance or wrapped.
        # Helper methods like _get_courses_to_sync will be refactored within their respective modules.

    # The _wrap_with_connection method is no longer needed and is removed.
    # Persistence logic is now handled by run_db_persist_in_thread.
