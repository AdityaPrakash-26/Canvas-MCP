"""
Canvas MCP Calendar Tools

This module contains tools for accessing calendar event information.
"""

import logging
from typing import Any
from cachetools import cached, TTLCache

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)

# Create a cache with a time-to-live of 10 minutes
cache = TTLCache(maxsize=100, ttl=600)

def register_calendar_tools(mcp: FastMCP) -> None:
    """Register calendar tools with the MCP server."""

    @mcp.tool()
    @cached(cache)
    def get_course_calendar_events(
        ctx: Context, course_id: int, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Get all calendar events for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            limit: Maximum number of events to return

        Returns:
            List of calendar events
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        # Get database connection
        conn, cursor = db_manager.connect()

        try:
            # Get course name
            cursor.execute("SELECT course_name FROM courses WHERE id = ?", (course_id,))
            course_row = cursor.fetchone()
            if not course_row:
                return [{"error": f"Course with ID {course_id} not found"}]

            course_name = course_row["course_name"]

            # Get calendar events for the course
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    description,
                    event_date,
                    event_type,
                    source_type,
                    source_id,
                    location_name,
                    location_address
                FROM
                    calendar_events
                WHERE
                    course_id = ?
                ORDER BY
                    event_date DESC
                LIMIT ?
                """,
                (course_id, limit),
            )
            events = cursor.fetchall()

            # Format the results
            result = []
            for event in events:
                result.append(
                    {
                        "id": event["id"],
                        "title": event["title"],
                        "description": event["description"],
                        "date": event["event_date"],
                        "event_type": event["event_type"],
                        "source_type": event["source_type"],
                        "location": event["location_name"],
                        "location_address": event["location_address"],
                        "course_name": course_name,
                    }
                )

            return result
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            return [{"error": f"Error getting calendar events: {e}"}]
        finally:
            conn.close()
