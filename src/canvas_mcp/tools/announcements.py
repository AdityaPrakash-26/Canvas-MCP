"""
Canvas MCP Announcement Tools

This module contains tools for accessing announcement information.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from canvas_mcp.utils.formatters import format_communications

logger = logging.getLogger(__name__)


def register_announcement_tools(mcp: FastMCP) -> None:
    """Register announcement tools with the MCP server."""

    @mcp.tool()
    def get_communications(
        ctx: Context, limit: int = 50, num_weeks: int = 3
    ) -> list[dict[str, Any]]:
        """
        Get all communications (announcements and conversations) from all courses.

        Args:
            ctx: Request context containing resources
            limit: Maximum number of communications to return
            num_weeks: Number of weeks to look back for communications (default: 3)

        Returns:
            List of communications (announcements and conversations)
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            # Calculate the date for filtering by weeks
            cutoff_date = (datetime.now() - timedelta(weeks=num_weeks)).isoformat()

            # Check if conversations table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='conversations';
                """
            )
            conversations_table_exists = cursor.fetchone() is not None

            if conversations_table_exists:
                # Query both announcements and conversations from all courses
                cursor.execute(
                    """
                    SELECT
                        'announcement' as source_type,
                        a.id,
                        a.title,
                        a.content,
                        a.posted_by,
                        a.posted_at,
                        c.course_name as course_name
                    FROM
                        announcements a
                    JOIN
                        courses c ON a.course_id = c.id
                    WHERE
                        a.posted_at >= ?
                    UNION ALL
                    SELECT
                        'conversation' as source_type,
                        cv.id,
                        cv.title,
                        cv.content,
                        cv.posted_by,
                        cv.posted_at,
                        c.course_name as course_name
                    FROM
                        conversations cv
                    JOIN
                        courses c ON cv.course_id = c.id
                    WHERE
                        cv.posted_at >= ?
                    ORDER BY
                        posted_at DESC
                    LIMIT ?
                    """,
                    (cutoff_date, cutoff_date, limit),
                )
            else:
                # Only query announcements if conversations table doesn't exist
                cursor.execute(
                    """
                    SELECT
                        'announcement' as source_type,
                        a.id,
                        a.title,
                        a.content,
                        a.posted_by,
                        a.posted_at,
                        c.course_name as course_name
                    FROM
                        announcements a
                    JOIN
                        courses c ON a.course_id = c.id
                    WHERE
                        a.posted_at >= ?
                    ORDER BY
                        posted_at DESC
                    LIMIT ?
                    """,
                    (cutoff_date, limit),
                )

            rows = cursor.fetchall()
            communications = db_manager.rows_to_dicts(rows)

            # Format communications for display
            return format_communications(communications)
        finally:
            conn.close()
