"""
Canvas MCP Assignment Tools

This module contains tools for accessing assignment information.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from canvas_mcp.utils.formatters import format_deadlines

logger = logging.getLogger(__name__)


def extract_links_from_content(content: str) -> list[dict[str, str]]:
    """
    Extract links from HTML content.

    Args:
        content: HTML content

    Returns:
        List of dictionaries with link information
    """
    if not content:
        return []

    # Extract links using regex
    links = []
    pattern = r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>'
    matches = re.findall(pattern, content, re.IGNORECASE)

    for url, text in matches:
        links.append({"url": url, "text": text.strip()})

    return links


def register_assignment_tools(mcp: FastMCP) -> None:
    """Register assignment tools with the MCP server."""

    @mcp.tool()
    def get_upcoming_deadlines(
        ctx: Context, days: int = 7, course_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get upcoming assignment deadlines.

        Args:
            ctx: Request context containing resources
            days: Number of days to look ahead
            course_id: Optional course ID to filter by

        Returns:
            List of upcoming deadlines
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        # Get database connection
        conn, cursor = db_manager.connect()

        try:
            # Use current date for production use
            now = datetime.now()
            end_date = now + timedelta(days=days)

            # Format dates for SQLite comparison
            now_str = now.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            # Build the query with simple date string comparison for better compatibility
            query = """
            SELECT
                c.course_code,
                c.course_name,
                a.title AS assignment_title,
                a.assignment_type,
                a.due_date,
                a.points_possible
            FROM
                assignments a
            JOIN
                courses c ON a.course_id = c.id
            WHERE
                a.due_date IS NOT NULL
                AND substr(a.due_date, 1, 10) >= ?
                AND substr(a.due_date, 1, 10) <= ?
            """

            params: list[Any] = [now_str, end_date_str]

            # Add course filter if specified
            if course_id is not None:
                query += " AND c.id = ?"
                params.append(course_id)

            query += " ORDER BY a.due_date ASC"

            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            deadlines = db_manager.rows_to_dicts(rows)

            # Format deadlines for display
            return format_deadlines(deadlines)
        finally:
            conn.close()
        # Close the connection

    @mcp.tool()
    def get_course_assignments(ctx: Context, course_id: int) -> list[dict[str, Any]]:
        """
        Get all assignments for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID

        Returns:
            List of assignments
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            cursor.execute(
                """
            SELECT
                a.id,
                a.canvas_assignment_id,
                a.title,
                a.description,
                a.assignment_type,
                a.due_date,
                a.available_from,
                a.available_until,
                a.points_possible,
                a.submission_types
            FROM
                assignments a
            WHERE
                a.course_id = ?
            ORDER BY
                a.due_date ASC
            """,
                (course_id,),
            )

            rows = cursor.fetchall()
            return db_manager.rows_to_dicts(rows)
        finally:
            conn.close()

    @mcp.tool()
    def get_assignment_details(
        ctx: Context,
        course_id: int,
        assignment_name: str,
        include_canvas_data: bool = True,
    ) -> dict[str, Any]:
        """
        Get comprehensive information about a specific assignment by name.
        This function consolidates the functionality of get_course_assignment and get_assignment_by_name.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            assignment_name: Name or partial name of the assignment
            include_canvas_data: Whether to include data from Canvas API if available

        Returns:
            Dictionary with assignment details and related resources
        """
        try:
            # Get database manager and API adapter from the lifespan context
            db_manager = ctx.request_context.lifespan_context["db_manager"]
            api_adapter = ctx.request_context.lifespan_context["api_adapter"]

            if not assignment_name or not course_id:
                return {
                    "error": "Missing required parameters: course_id and assignment_name must be provided"
                }

            conn, cursor = db_manager.connect()

            try:
                # Get course information
                cursor.execute(
                    """
                SELECT
                    c.course_code,
                    c.course_name,
                    c.canvas_course_id
                FROM
                    courses c
                WHERE
                    c.id = ?
                """,
                    (course_id,),
                )
                course_row = cursor.fetchone()
                if not course_row:
                    return {
                        "error": f"Course with ID {course_id} not found",
                        "course_id": course_id,
                    }

                course = db_manager.row_to_dict(course_row)

                # Search for the assignment with fuzzy matching
                search_term = f"%{assignment_name}%"
                cursor.execute(
                    """
                SELECT
                    a.id,
                    a.canvas_assignment_id,
                    a.title,
                    a.description,
                    a.assignment_type,
                    a.due_date,
                    a.available_from,
                    a.available_until,
                    a.points_possible,
                    a.submission_types
                FROM
                    assignments a
                WHERE
                    a.course_id = ? AND (a.title LIKE ? OR a.description LIKE ?)
                ORDER BY
                    CASE WHEN a.title LIKE ? THEN 0 ELSE 1 END,
                    a.due_date ASC
                LIMIT 1
                """,
                    (course_id, search_term, search_term, search_term),
                )

                assignment_row = cursor.fetchone()
                if not assignment_row:
                    return {
                        "error": f"No assignment matching '{assignment_name}' found in course {course_id}",
                        "course_id": course_id,
                        "course_name": course.get("course_name"),
                        "course_code": course.get("course_code"),
                        "assignment_name": assignment_name,
                    }

                assignment = db_manager.row_to_dict(assignment_row)

                # Add course information to the result
                result = {
                    "course_code": course.get("course_code"),
                    "course_name": course.get("course_name"),
                    "assignment": assignment,
                }

                # Get related PDF files
                pdf_files = []
                try:
                    # Get the Canvas course ID from the local course ID
                    canvas_course_id = course.get("canvas_course_id")

                    # Get course from Canvas
                    canvas_course = api_adapter.get_course_raw(canvas_course_id)
                    if not canvas_course:
                        logger.warning(
                            f"Course with ID {canvas_course_id} not found in Canvas"
                        )
                        pdf_files = [{"error": "Course not found in Canvas"}]
                    else:
                        # Get files from the course
                        raw_files = api_adapter.get_files_raw(canvas_course)

                        # Filter for PDF files
                        all_pdfs = []
                        for file in raw_files:
                            file_name = (
                                file.display_name
                                if hasattr(file, "display_name")
                                else (
                                    file.filename
                                    if hasattr(file, "filename")
                                    else "Unnamed File"
                                )
                            )

                            # Check if it's a PDF
                            content_type = getattr(file, "content_type", "")
                            if (
                                "pdf" in content_type.lower()
                                or file_name.lower().endswith(".pdf")
                            ):
                                all_pdfs.append(
                                    {
                                        "name": file_name,
                                        "url": file.url
                                        if hasattr(file, "url")
                                        else None,
                                        "content_type": content_type,
                                        "source": "files",
                                    }
                                )

                        # Filter PDFs that might be related to this assignment
                        for pdf in all_pdfs:
                            if (
                                assignment.get("title") in pdf.get("name", "")
                                or assignment_name.lower()
                                in pdf.get("name", "").lower()
                            ):
                                pdf_files.append(
                                    {
                                        "name": pdf.get("name", ""),
                                        "url": pdf.get("url", ""),
                                        "source": pdf.get("source", ""),
                                    }
                                )
                except Exception as e:
                    logger.error(f"Error retrieving PDF files: {str(e)}")
                    pdf_files = [{"error": f"Error retrieving PDF files: {str(e)}"}]

                result["pdf_files"] = pdf_files

                # Extract links from assignment description
                if assignment.get("description"):
                    try:
                        result["links"] = extract_links_from_content(
                            assignment.get("description", "")
                        )
                    except Exception as e:
                        logger.error(f"Error extracting links: {str(e)}")
                        result["links"] = []
                        result["links_error"] = f"Error extracting links: {str(e)}"

                # Get module information where this assignment might be referenced
                try:
                    cursor.execute(
                        """
                    SELECT
                        m.id,
                        m.name,
                        mi.title,
                        mi.item_type
                    FROM
                        modules m
                    JOIN
                        module_items mi ON m.id = mi.module_id
                    WHERE
                        m.course_id = ? AND mi.content_details LIKE ?
                    """,
                        (course_id, f"%{assignment.get('canvas_assignment_id')}%"),
                    )

                    modules = [db_manager.row_to_dict(row) for row in cursor.fetchall()]
                    if modules:
                        result["modules"] = modules
                except Exception as e:
                    logger.error(f"Error retrieving module information: {str(e)}")
                    result["modules_error"] = (
                        f"Error retrieving module information: {str(e)}"
                    )

            except Exception as e:
                logger.error(
                    f"Database error while retrieving assignment details: {str(e)}"
                )
                return {
                    "error": f"Database error: {str(e)}",
                    "course_id": course_id,
                    "assignment_name": assignment_name,
                }
            finally:
                conn.close()

            # If requested and the assignment was found, try to get additional info from Canvas API
            if include_canvas_data and "error" not in result:
                try:
                    # Get the API adapter from the lifespan context
                    api_adapter = ctx.request_context.lifespan_context["api_adapter"]

                    if not api_adapter.is_available():
                        result["canvas_api_status"] = "unavailable"
                        return result

                    # Get the course from Canvas
                    canvas_course_id = course.get("canvas_course_id")
                    canvas_course = api_adapter.get_course_raw(canvas_course_id)

                    if not canvas_course:
                        result["canvas_api_status"] = "course not found"
                        return result

                    # Get the assignment from Canvas
                    canvas_assignment_id = assignment.get("canvas_assignment_id")
                    canvas_assignment = api_adapter.get_assignment_raw(
                        canvas_course, canvas_assignment_id
                    )

                    if canvas_assignment:
                        # Create a data dictionary with assignment details
                        assignment_data = {
                            "title": canvas_assignment.name,
                            "description": getattr(
                                canvas_assignment, "description", ""
                            ),
                            "due_date": getattr(canvas_assignment, "due_at", None),
                            "points_possible": getattr(
                                canvas_assignment, "points_possible", None
                            ),
                            "submission_types": getattr(
                                canvas_assignment, "submission_types", []
                            ),
                            "canvas_assignment_id": canvas_assignment.id,
                        }

                        # Check for additional details like rubrics
                        if hasattr(canvas_assignment, "rubric"):
                            assignment_data["rubric"] = canvas_assignment.rubric

                        result["canvas_details"] = assignment_data
                    else:
                        result["canvas_api_status"] = "assignment not found"
                except ImportError:
                    # Canvas API not available, continue with database info
                    logger.warning(
                        "Canvas API not available - proceeding with database info only"
                    )
                    result["canvas_api_status"] = "unavailable"
                except Exception as e:
                    logger.error(f"Canvas API error: {str(e)}")
                    result["canvas_api_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Unexpected error in get_assignment_details: {str(e)}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "course_id": course_id,
                "assignment_name": assignment_name,
            }
