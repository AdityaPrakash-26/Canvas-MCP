"""
Canvas MCP Search Tools

This module contains tools for searching course content.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_search_tools(mcp: FastMCP) -> None:
    """Register search tools with the MCP server."""

    @mcp.tool()
    def search_course_content(
        ctx: Context, query: str, course_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for content across courses.

        Args:
            ctx: Request context containing resources
            query: Search query
            course_id: Optional course ID to limit search

        Returns:
            List of matching items
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        # Prepare search parameters
        search_term = f"%{query}%"
        params: list[Any] = []
        course_filter = ""

        if course_id is not None:
            course_filter = "AND c.id = ?"
            params.append(course_id)

        # Search in assignments
        cursor.execute(
            f"""
        SELECT
            c.course_code,
            c.course_name,
            a.title,
            a.description,
            'assignment' AS content_type,
            a.id AS content_id
        FROM
            assignments a
        JOIN
            courses c ON a.course_id = c.id
        WHERE
            (a.title LIKE ? OR a.description LIKE ?)
            {course_filter}
        """,
            [search_term, search_term] + params,
        )

        assignments = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

        # Search in modules
        cursor.execute(
            f"""
        SELECT
            c.course_code,
            c.course_name,
            m.name AS title,
            m.description,
            'module' AS content_type,
            m.id AS content_id
        FROM
            modules m
        JOIN
            courses c ON m.course_id = c.id
        WHERE
            (m.name LIKE ? OR m.description LIKE ?)
            {course_filter}
        """,
            [search_term, search_term] + params,
        )

        modules = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

        # Search in module items
        cursor.execute(
            f"""
        SELECT
            c.course_code,
            c.course_name,
            mi.title,
            mi.content_details AS description,
            'module_item' AS content_type,
            mi.id AS content_id
        FROM
            module_items mi
        JOIN
            modules m ON mi.module_id = m.id
        JOIN
            courses c ON m.course_id = c.id
        WHERE
            (mi.title LIKE ? OR mi.content_details LIKE ?)
            {course_filter}
        """,
            [search_term, search_term] + params,
        )

        module_items = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

        # Search in syllabi
        cursor.execute(
            f"""
        SELECT
            c.course_code,
            c.course_name,
            'Syllabus' AS title,
            s.content AS description,
            'syllabus' AS content_type,
            s.id AS content_id
        FROM
            syllabi s
        JOIN
            courses c ON s.course_id = c.id
        WHERE
            s.content LIKE ?
            {course_filter}
        """,
            [search_term] + params,
        )

        syllabi = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

        # Combine results
        results = assignments + modules + module_items + syllabi

        conn.close()
        return results
