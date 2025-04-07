"""
Canvas MCP Module Tools

This module contains tools for accessing module information.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_module_tools(mcp: FastMCP) -> None:
    """Register module tools with the MCP server."""

    @mcp.tool()
    def get_course_modules(
        ctx: Context, course_id: int, include_items: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all modules for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            include_items: Whether to include module items

        Returns:
            List of modules
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]
        
        conn, cursor = db_manager.connect()

        try:
            cursor.execute(
                """
            SELECT
                m.id,
                m.canvas_module_id,
                m.name,
                m.description,
                m.unlock_date,
                m.position
            FROM
                modules m
            WHERE
                m.course_id = ?
            ORDER BY
                m.position ASC
            """,
                (course_id,),
            )

            modules = db_manager.rows_to_dicts(cursor.fetchall())

            # Include module items if requested
            if include_items:
                for module in modules:
                    cursor.execute(
                        """
                    SELECT
                        mi.id,
                        mi.canvas_item_id,
                        mi.title,
                        mi.item_type,
                        mi.position,
                        mi.url,
                        mi.page_url,
                        mi.content_details
                    FROM
                        module_items mi
                    WHERE
                        mi.module_id = ?
                    ORDER BY
                        mi.position ASC
                    """,
                        (module["id"],),
                    )

                    module["items"] = db_manager.rows_to_dicts(cursor.fetchall())

            return modules
        finally:
            conn.close()
