"""
Canvas MCP Sync Tools

This module contains tools for synchronizing data from Canvas LMS to the local database.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_sync_tools(mcp: FastMCP) -> None:
    """Register sync tools with the MCP server."""

    @mcp.tool()
    def sync_canvas_data(ctx: Context) -> dict[str, Any]:
        """
        Synchronize data from Canvas LMS to the local database.

        Args:
            ctx: Request context containing resources

        Returns:
            Dictionary with counts of synced items
        """
        try:
            # Get the sync service from the lifespan context
            sync_service = ctx.request_context.lifespan_context["sync_service"]
            result = sync_service.sync_all()
            return result
        except ImportError:
            return {"error": "canvasapi module is required for this operation"}
        except Exception as e:
            logger.error(f"Error syncing Canvas data: {e}")
            return {"error": str(e)}
