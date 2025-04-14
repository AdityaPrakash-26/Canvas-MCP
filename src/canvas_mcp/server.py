"""
Canvas MCP Server

This module provides the main server for Canvas MCP.
It integrates with the Canvas API and local SQLite database to provide
structured access to course information.
"""
import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

import canvas_mcp.config as config
from canvas_mcp.canvas_api_adapter import CanvasApiAdapter
from canvas_mcp.sync import SyncService
from canvas_mcp.utils.db_manager import DatabaseManager

try:
    from canvasapi import Canvas
except ImportError:
    # Create a dummy Canvas class for tests to patch
    class Canvas:
        def __init__(self, api_url, api_key):
            self.api_url = api_url
            self.api_key = api_key


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("canvas_mcp")


async def cancel_all_tasks():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def close_io_streams():
    sys.stdout.close()
    sys.stderr.close()
    sys.stdin.close()


def handle_shutdown_signal(signum, frame):
    print("Signal received, shutting down...")
    asyncio.run(cancel_all_tasks())
    close_io_streams()
    asyncio.get_event_loop().stop()
    sys.exit(0)


# Define the lifespan context type
@dataclass
class LifespanContext:
    db_manager: DatabaseManager
    api_adapter: CanvasApiAdapter
    sync_service: SyncService


@asynccontextmanager
async def app_lifespan(_: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage application lifecycle with resources"""
    # Initialize resources on startup
    logger.info(f"Initializing resources with database: {config.DB_PATH}")

    # Create database manager
    db_manager = DatabaseManager(config.DB_PATH)

    # Create Canvas API adapter
    try:
        # Initialize Canvas API client
        canvas_api_client = Canvas(config.API_URL, config.API_KEY)
        api_adapter = CanvasApiAdapter(canvas_api_client)
        logger.info("Canvas API adapter initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Canvas API adapter: {e}")
        # Create a dummy adapter that will use database-only operations
        api_adapter = CanvasApiAdapter(None)
        logger.warning(
            "Created database-only Canvas API adapter due to initialization error"
        )

    # Create Sync Service
    sync_service = SyncService(db_manager, api_adapter)
    logger.info("Sync service initialized successfully")

    # Create the lifespan context dictionary
    lifespan_context = {
        "db_manager": db_manager,
        "api_adapter": api_adapter,
        "sync_service": sync_service,
    }

    try:
        # Yield the context to the server
        yield lifespan_context
    finally:
        # Cleanup on shutdown (if needed)
        logger.info("Shutting down Canvas MCP server")

        await cancel_all_tasks()

        if hasattr(sync_service, "shutdown"):
            logger.info("Shutting down SyncService...")
            await sync_service.shutdown()

        if hasattr(db_manager, "shutdown"):
            logger.info("Shutting down DatabaseManager...")
            db_manager.shutdown()

        logger.info("Shutdown complete.")

# Create an MCP server with lifespan
mcp = FastMCP(
    "Canvas MCP",
    dependencies=[
        "canvasapi>=3.3.0",
        "structlog>=24.1.0",
        "python-dotenv>=1.0.1",
        "pdfplumber>=0.7.0",
        "beautifulsoup4>=4.12.0",
        "python-docx>=0.8.11",
    ],
    description="A Canvas integration for accessing course information, assignments, and resources.",
    lifespan=app_lifespan,
)

# Register tool modules
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.tools.assignments import register_assignment_tools
from canvas_mcp.tools.calendar import register_calendar_tools
from canvas_mcp.tools.courses import register_course_tools
from canvas_mcp.tools.files import register_file_tools
from canvas_mcp.tools.modules import register_module_tools
from canvas_mcp.tools.search import register_search_tools
from canvas_mcp.tools.syllabus import register_syllabus_tools
from canvas_mcp.tools.sync import register_sync_tools

# Register all tools
register_sync_tools(mcp)
register_course_tools(mcp)
register_assignment_tools(mcp)
register_module_tools(mcp)
register_syllabus_tools(mcp)
register_announcement_tools(mcp)
register_file_tools(mcp)
register_search_tools(mcp)
register_calendar_tools(mcp)


if __name__ == "__main__":
    mcp.run()
