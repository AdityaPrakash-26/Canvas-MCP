"""
Mock MCP Server for Testing

This module provides a simplified mock of the MCP server for testing tools.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MockContext:
    """Mock context for testing tools."""

    request_context: SimpleNamespace


class MockMCP:
    """Mock MCP server for testing tools."""

    def __init__(self, name: str):
        """Initialize the mock MCP server."""
        self.name = name
        self.tools = {}
        self.lifespan_context = {}

    def tool(self):
        """Decorator for registering tools."""

        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator

    def register_tool(self, name: str, func: Callable):
        """Register a tool with the mock MCP server."""
        self.tools[name] = func

    def execute_tool(self, name: str, ctx: MockContext, **kwargs):
        """Execute a registered tool."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not registered")

        return self.tools[name](ctx, **kwargs)

    def set_lifespan_context(self, context: dict[str, Any]):
        """Set the lifespan context for the mock MCP server."""
        self.lifespan_context = context

    def create_context(self) -> MockContext:
        """Create a mock context with the lifespan context."""
        request_context = SimpleNamespace(lifespan_context=self.lifespan_context)
        return MockContext(request_context=request_context)


def create_mock_mcp(name: str = "MockMCP") -> MockMCP:
    """Create a mock MCP server for testing."""
    return MockMCP(name)
