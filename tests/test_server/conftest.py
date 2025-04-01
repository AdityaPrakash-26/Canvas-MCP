"""
Server-specific test fixtures.
"""
import asyncio
from typing import Generator, Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP

from canvas_mcp.server import create_app, setup_routes


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI application for testing."""
    return create_app()


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_mcp_server() -> Generator[FastMCP, None, None]:
    """Create a mock MCP server."""
    # Create a mock MCP server
    mcp_server = FastMCP("test_id", "Test Server")
    
    # Register tools and resources
    # (Add mock tools and resources as needed for specific tests)
    
    yield mcp_server


@pytest_asyncio.fixture
async def async_test_client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create an async test client for the FastAPI application."""
    # Set up any async resources needed
    client = TestClient(app)
    
    yield client
    
    # Clean up any async resources
