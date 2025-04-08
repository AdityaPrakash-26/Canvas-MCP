"""
Canvas MCP Syllabus Tools

This module contains tools for accessing syllabus information.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_syllabus_tools(mcp: FastMCP) -> None:
    """Register syllabus tools with the MCP server."""

    @mcp.tool()
    def get_syllabus(
        ctx: Context, course_id: int, format: str = "raw"
    ) -> dict[str, Any]:
        """
        Get the syllabus for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            format: Format to return ("raw" for HTML, "parsed" for extracted text)

        Returns:
            Dictionary with syllabus content
        """
        # Get database manager from the lifespan context
        db_manager = ctx.request_context.lifespan_context["db_manager"]

        conn, cursor = db_manager.connect()

        try:
            # Get course information
            cursor.execute(
                """
            SELECT
                c.course_code,
                c.course_name,
                c.instructor
            FROM
                courses c
            WHERE
                c.id = ?
            """,
                (course_id,),
            )

            course_row = cursor.fetchone()
            course = (
                db_manager.row_to_dict(course_row)
                if course_row
                else {"course_code": "", "course_name": "", "instructor": ""}
            )

            # Get syllabus content
            cursor.execute(
                """
            SELECT
                s.content,
                s.content_type,
                s.parsed_content,
                s.is_parsed
            FROM
                syllabi s
            WHERE
                s.course_id = ?
            """,
                (course_id,),
            )

            syllabus_row = cursor.fetchone()
            syllabus = (
                db_manager.row_to_dict(syllabus_row)
                if syllabus_row
                else {
                    "content": "",
                    "content_type": "html",
                    "parsed_content": "",
                    "is_parsed": False,
                }
            )

            # Determine which content to return based on format
            content = syllabus.get("content", "")
            if format == "parsed" and syllabus.get("is_parsed"):
                content = syllabus.get("parsed_content", "")

            # Return combined result
            return {
                "course_code": course.get("course_code", ""),
                "course_name": course.get("course_name", ""),
                "instructor": course.get("instructor", ""),
                "content": content,
                "content_type": syllabus.get("content_type", "html"),
                "format": format,
            }
        finally:
            conn.close()

    @mcp.tool()
    def get_syllabus_file(
        ctx: Context, course_id: int, extract_content: bool = True
    ) -> dict[str, Any]:
        """
        Attempt to find a syllabus file for a specific course.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            extract_content: Whether to extract and store content from the syllabus file

        Returns:
            Dictionary with syllabus file information or error
        """
        try:
            # Get API adapter and database manager from the lifespan context
            api_adapter = ctx.request_context.lifespan_context["api_adapter"]
            db_manager = ctx.request_context.lifespan_context["db_manager"]

            # Check if Canvas API is available
            if not api_adapter.is_available():
                logger.warning("Canvas API not available in get_syllabus_file")
                return {
                    "success": False,
                    "course_id": course_id,
                    "error": "Canvas API connection not available",
                }

            # Get the Canvas course ID from the local course ID
            conn, cursor = db_manager.connect()
            try:
                cursor.execute(
                    "SELECT canvas_course_id FROM courses WHERE id = ?", (course_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "course_id": course_id,
                        "error": f"Course with ID {course_id} not found in database",
                    }
                canvas_course_id = row["canvas_course_id"]
            finally:
                conn.close()

            # Get course from Canvas
            canvas_course = api_adapter.get_course_raw(canvas_course_id)
            if not canvas_course:
                return {
                    "success": False,
                    "course_id": course_id,
                    "error": f"Course with ID {canvas_course_id} not found in Canvas",
                }

            # Get files from the course
            raw_files = api_adapter.get_files_raw(canvas_course)

            # Process files
            files = []
            for file in raw_files:
                file_name = (
                    file.display_name
                    if hasattr(file, "display_name")
                    else (
                        file.filename if hasattr(file, "filename") else "Unnamed File"
                    )
                )

                files.append(
                    {
                        "name": file_name,
                        "url": file.url if hasattr(file, "url") else None,
                        "content_type": file.content_type
                        if hasattr(file, "content_type")
                        else None,
                        "size": file.size if hasattr(file, "size") else None,
                        "created_at": file.created_at
                        if hasattr(file, "created_at")
                        else None,
                        "updated_at": file.updated_at
                        if hasattr(file, "updated_at")
                        else None,
                        "source": "files",
                    }
                )

            # Look for files with "syllabus" in the name
            syllabus_files = []
            for file in files:
                if "syllabus" in file["name"].lower():
                    syllabus_files.append(file)

            if not syllabus_files:
                return {
                    "success": False,
                    "course_id": course_id,
                    "error": "No syllabus file found",
                }

            # Get the first syllabus file found
            syllabus_file = syllabus_files[0]
            result = {
                "success": True,
                "course_id": course_id,
                "syllabus_file": syllabus_file,
                "all_syllabus_files": syllabus_files,
            }

            # Extract content if requested
            if extract_content and "url" in syllabus_file:
                file_url = syllabus_file["url"]
                file_type = None
                if "content_type" in syllabus_file:
                    if "pdf" in syllabus_file["content_type"].lower():
                        file_type = "pdf"
                    elif "word" in syllabus_file["content_type"].lower():
                        file_type = "docx"

                # Import here to avoid circular imports
                from canvas_mcp.utils.file_extractor import extract_text_from_file

                extraction_result = extract_text_from_file(file_url, file_type)
                if extraction_result["success"]:
                    result["extracted_text"] = extraction_result["text"]
                    result["extraction_success"] = True

                    # Store the extracted content in the database
                    conn, cursor = db_manager.connect()
                    try:
                        # Check if syllabus exists
                        cursor.execute(
                            "SELECT id FROM syllabi WHERE course_id = ?", (course_id,)
                        )
                        syllabus_row = cursor.fetchone()

                        if syllabus_row:
                            # Update existing syllabus
                            cursor.execute(
                                """
                            UPDATE syllabi
                            SET content = ?, content_type = ?, parsed_content = ?, is_parsed = 1
                            WHERE course_id = ?
                            """,
                                (
                                    syllabus_file.get("name", ""),
                                    file_type or "unknown",
                                    extraction_result["text"],
                                    course_id,
                                ),
                            )
                        else:
                            # Insert new syllabus
                            cursor.execute(
                                """
                            INSERT INTO syllabi (course_id, content, content_type, parsed_content, is_parsed)
                            VALUES (?, ?, ?, ?, 1)
                            """,
                                (
                                    course_id,
                                    syllabus_file.get("name", ""),
                                    file_type or "unknown",
                                    extraction_result["text"],
                                ),
                            )
                        conn.commit()
                        result["database_updated"] = True
                    except Exception as e:
                        logger.error(f"Error updating syllabus in database: {str(e)}")
                        result["database_error"] = str(e)
                    finally:
                        conn.close()
                else:
                    result["extraction_success"] = False
                    result["extraction_error"] = extraction_result.get(
                        "error", "Unknown extraction error"
                    )

            return result
        except Exception as e:
            logger.error(f"Error in get_syllabus_file: {str(e)}")
            return {
                "success": False,
                "course_id": course_id,
                "error": f"Error searching for syllabus file: {e}",
            }
