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
    def get_course_communications(
        ctx: Context, course_id: int, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Get all communications (announcements and conversations) for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            limit: Maximum number of communications to return

        Returns:
            List of communications (announcements and conversations)
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            # First get the course name
            cursor.execute(
                """
                SELECT course_name FROM courses WHERE id = ?
                """,
                (course_id,),
            )
            course_row = cursor.fetchone()
            course_name = course_row["course_name"] if course_row else "Unknown Course"

            # Query both announcements and conversations
            cursor.execute(
                """
                SELECT
                    'announcement' as source_type,
                    id,
                    title,
                    content,
                    posted_by,
                    posted_at,
                    ? as course_name
                FROM
                    announcements
                WHERE
                    course_id = ?
                UNION ALL
                SELECT
                    'conversation' as source_type,
                    id,
                    title,
                    content,
                    posted_by,
                    posted_at,
                    ? as course_name
                FROM
                    conversations
                WHERE
                    course_id = ?
                ORDER BY
                    posted_at DESC
                LIMIT ?
                """,
                (course_name, course_id, course_name, course_id, limit),
            )

            rows = cursor.fetchall()
            return db_manager.rows_to_dicts(rows)
        finally:
            conn.close()

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
