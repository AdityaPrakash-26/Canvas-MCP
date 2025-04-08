"""
Canvas MCP Announcement Tools

This module contains tools for accessing announcement information.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_announcement_tools(mcp: FastMCP) -> None:
    """Register announcement tools with the MCP server."""

    @mcp.tool()
    def get_course_announcements(
        ctx: Context, course_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get announcements for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            limit: Maximum number of announcements to return

        Returns:
            List of announcements
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            cursor.execute(
                """
            SELECT
                a.id,
                a.canvas_announcement_id,
                a.title,
                a.content,
                a.posted_by,
                a.posted_at
            FROM
                announcements a
            WHERE
                a.course_id = ?
            ORDER BY
                a.posted_at DESC
            LIMIT ?
            """,
                (course_id, limit),
            )

            rows = cursor.fetchall()
            return db_manager.rows_to_dicts(rows)
        finally:
            conn.close()
