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

    @mcp.tool()
    def get_course_communications(
        ctx: Context, course_id: int, limit: int = 20, num_weeks: int = 3
    ) -> list[dict[str, Any]]:
        """
        Get all communications (announcements and conversations) for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            limit: Maximum number of communications to return
            num_weeks: Number of weeks to look back for communications (default: 3)

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
                        course_id = ? AND
                        posted_at >= ?
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
                        course_id = ? AND
                        posted_at >= ?
                    ORDER BY
                        posted_at DESC
                    LIMIT ?
                    """,
                    (
                        course_name,
                        course_id,
                        cutoff_date,
                        course_name,
                        course_id,
                        cutoff_date,
                        limit,
                    ),
                )
            else:
                # Only query announcements if conversations table doesn't exist
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
                        course_id = ? AND
                        posted_at >= ?
                    ORDER BY
                        posted_at DESC
                    LIMIT ?
                    """,
                    (
                        course_name,
                        course_id,
                        cutoff_date,
                        limit,
                    ),
                )

            rows = cursor.fetchall()
            communications = db_manager.rows_to_dicts(rows)

            # Format communications for display
            return format_communications(communications)
        finally:
            conn.close()

    @mcp.tool()
    def get_course_announcements(
        ctx: Context, course_id: int, limit: int = 10, num_weeks: int = 2
    ) -> list[dict[str, Any]]:
        """
        Get announcements for a specific course.

        DEPRECATED: Use get_course_communications or get_all_communications instead.
        This tool will be removed in a future version.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            limit: Maximum number of announcements to return
            num_weeks: Number of weeks to look back for announcements (default: 2)

        Returns:
            List of announcements
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            # Calculate the date for filtering by weeks
            cutoff_date = (datetime.now() - timedelta(weeks=num_weeks)).isoformat()

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
                a.course_id = ? AND
                a.posted_at >= ?
            ORDER BY
                a.posted_at DESC
            LIMIT ?
            """,
                (course_id, cutoff_date, limit),
            )

            rows = cursor.fetchall()
            announcements = db_manager.rows_to_dicts(rows)

            # Format announcements for display
            return format_communications(announcements)
        finally:
            conn.close()
