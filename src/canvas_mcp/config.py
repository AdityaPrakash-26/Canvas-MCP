"""
Configuration Management for Canvas MCP

This module centralizes configuration loading and management for the Canvas MCP server.
It handles environment variables, path logic, and constant definitions.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure paths
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_DIR / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"

# Allow overriding the database path for testing
if os.environ.get("CANVAS_MCP_TEST_DB"):
    DB_PATH = Path(os.environ.get("CANVAS_MCP_TEST_DB"))
    logger.info(f"Using test database: {DB_PATH}")

# Ensure directories exist
os.makedirs(DB_PATH.parent, exist_ok=True)

# Canvas API configuration
API_KEY = os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

# Initialize database if it doesn't exist
if not DB_PATH.exists():
    import sys

    sys.path.append(str(PROJECT_DIR))
    from init_db import create_database

    create_database(str(DB_PATH))
    logger.info(f"Database initialized at {DB_PATH}")

# Export configuration variables
__all__ = ["DB_PATH", "API_KEY", "API_URL", "PROJECT_DIR"]
