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
    def get_course_announcements(course_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get announcements for a specific course.

        Args:
            course_id: Course ID
            limit: Maximum number of announcements to return

        Returns:
            List of announcements
        """
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

            announcements = db_manager.rows_to_dicts(cursor.fetchall())

            # Enhance announcements with additional context
            for announcement in announcements:
                # Extract links from the content
                try:
                    announcement["links"] = extract_links_from_content(
                        announcement.get("content", "")
                    )
                except Exception as e:
                    logger.error(f"Error extracting links from announcement: {e}")
                    announcement["links"] = []

                # Add content preview if content is long
                if announcement.get("content"):
                    preview_length = 500
                    stripped_content = re.sub(r"<[^>]+>", "", announcement["content"])
                    announcement["content_preview"] = stripped_content[:preview_length] + (
                        "..." if len(stripped_content) > preview_length else ""
                    )

            return announcements
        finally:
            conn.close()
