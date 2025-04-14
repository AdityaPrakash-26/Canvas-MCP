"""
Canvas MCP Course Tools

This module contains tools for accessing course information.
"""
import json
import logging
from typing import Any
from mcp.server.fastmcp import Context, FastMCP


logger = logging.getLogger(__name__)


def register_course_tools(mcp: FastMCP) -> None:
    """Register course tools with the MCP server."""

    @mcp.tool()
    def get_course_list(ctx: Context) -> list[dict[str, Any]]:
        """
        Get list of all courses in the database.

        Args:
            ctx: Request context containing resources

        Returns:
            List of course information
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]
        cache = ctx.request_context.lifespan_context.get("cache")
        cache_key = "courses"

        if cache is None:
            logger.error("Cache is not available")
        else:
            logger.info("Cache connected successfully")
            cached_data = cache.get(cache_key)
            if cached_data:
                print("Memcached hit: course_list")
                return json.loads(cached_data.decode())

        conn, cursor = db_manager.connect()

        try:
            cursor.execute("""
            SELECT
                c.id,
                c.canvas_course_id,
                c.course_code,
                c.course_name,
                c.instructor,
                c.start_date,
                c.end_date
            FROM
                courses c
            ORDER BY
                c.start_date DESC
            """)

            rows = cursor.fetchall()
            result =  db_manager.rows_to_dicts(rows)

            if cache:
                logger.info("Setting courses in cache")
                result_json = json.dumps(result)
                cache.set(cache_key, result_json, expire=86400)  # Cache for 1 day
                logger.info(f"Courses cached successfully: {result_json[:100]}...")  # Log the first 100 chars

            return result
        finally:
            conn.close()
