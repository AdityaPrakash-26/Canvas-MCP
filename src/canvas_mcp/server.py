"""
Canvas MCP Server

This module provides the main server for Canvas MCP.
It integrates with the Canvas API and local SQLite database to provide
structured access to course information.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

import canvas_mcp.config as config
from canvas_mcp.utils.db_manager import DatabaseManager

try:
    from .canvas_client import CanvasClient
except ImportError:
    from canvas_mcp.canvas_client import CanvasClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("canvas_mcp")


# Define the lifespan context type
@dataclass
class LifespanContext:
    db_manager: DatabaseManager
    canvas_client: CanvasClient


@asynccontextmanager
async def app_lifespan(_: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage application lifecycle with resources"""
    # Initialize resources on startup
    logger.info(f"Initializing resources with database: {config.DB_PATH}")

    # Create database manager
    db_manager = DatabaseManager(config.DB_PATH)

    # Create Canvas client
    try:
        canvas_client = CanvasClient(db_manager, config.API_KEY, config.API_URL)
        logger.info("Canvas client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Canvas client: {e}")
        # Create a dummy client that will use database-only operations
        canvas_client = CanvasClient(db_manager, None, None)
        logger.warning(
            "Created database-only Canvas client due to initialization error"
        )

    # Create the lifespan context dictionary
    lifespan_context = {
        "db_manager": db_manager,
        "canvas_client": canvas_client,
    }

    try:
        # Yield the context to the server
        yield lifespan_context
    finally:
        # Cleanup on shutdown (if needed)
        logger.info("Shutting down Canvas MCP server")


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
from canvas_mcp.tools.sync import register_sync_tools
from canvas_mcp.tools.courses import register_course_tools
from canvas_mcp.tools.assignments import register_assignment_tools
from canvas_mcp.tools.modules import register_module_tools
from canvas_mcp.tools.syllabus import register_syllabus_tools
from canvas_mcp.tools.announcements import register_announcement_tools
from canvas_mcp.tools.files import register_file_tools
from canvas_mcp.tools.search import register_search_tools

# Register all tools
register_sync_tools(mcp)
register_course_tools(mcp)
register_assignment_tools(mcp)
register_module_tools(mcp)
register_syllabus_tools(mcp)
register_announcement_tools(mcp)
register_file_tools(mcp)
register_search_tools(mcp)


if __name__ == "__main__":
    mcp.run()
