"""
Canvas MCP Sync Tools

This module contains tools for triggering data synchronization.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_sync_tools(mcp: FastMCP) -> None:
    """Register sync tools with the MCP server."""

    @mcp.tool()
    async def sync_canvas_data(ctx: Context) -> dict[str, Any]:
        """
        Synchronize all data from Canvas to the local database asynchronously.

        This process fetches the latest information for courses, assignments,
        modules, announcements, and conversations from the Canvas API and
        updates the local database. It can take some time depending on the
        amount of data.

        Args:
            ctx: Request context containing resources like sync_service.

        Returns:
            Dictionary with counts of synced items (e.g., {"courses": 10, "assignments": 55}).
        """
        try:
            # Get the sync service from the lifespan context
            sync_service = ctx.request_context.lifespan_context["sync_service"]

            logger.info("Starting Canvas data synchronization via tool...")
            # Call the async sync_all method on the service instance
            result = await sync_service.sync_all()
            logger.info(f"Canvas data synchronization completed. Result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error during Canvas data synchronization: {e}", exc_info=True)
            return {"error": f"Synchronization failed: {str(e)}"}