"""
Canvas MCP File Tools

This module contains tools for accessing file information.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


def register_file_tools(mcp: FastMCP) -> None:
    """Register file tools with the MCP server."""

    @mcp.tool()
    def get_course_files(
        ctx: Context, course_id: int, file_type: str = None
    ) -> list[dict[str, Any]]:
        """
        Get all files available in a specific course, with optional filtering by file type.

        Args:
            ctx: Request context containing resources
            course_id: Course ID
            file_type: Optional file extension to filter by (e.g., 'pdf', 'docx')

        Returns:
            List of files with URLs
        """
        try:
            # Get API adapter from the lifespan context
            api_adapter = ctx.request_context.lifespan_context["api_adapter"]
            db_manager = ctx.request_context.lifespan_context["db_manager"]

            if not api_adapter.is_available():
                return [{"error": "Canvas API not available"}]

            # Get the Canvas course ID from the local course ID
            conn, cursor = db_manager.connect()
            try:
                cursor.execute(
                    "SELECT canvas_course_id FROM courses WHERE id = ?", (course_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return [
                        {"error": f"Course with ID {course_id} not found in database"}
                    ]
                canvas_course_id = row["canvas_course_id"]
            finally:
                conn.close()

            # Get course from Canvas
            canvas_course = api_adapter.get_course_raw(canvas_course_id)
            if not canvas_course:
                return [
                    {"error": f"Course with ID {canvas_course_id} not found in Canvas"}
                ]

            # Get files from the course
            raw_files = api_adapter.get_files_raw(canvas_course)

            # Process files
            result = []
            for file in raw_files:
                file_name = (
                    file.display_name
                    if hasattr(file, "display_name")
                    else (
                        file.filename if hasattr(file, "filename") else "Unnamed File"
                    )
                )

                # Filter by file type if specified
                if file_type:
                    # Special handling for common file types
                    if file_type.lower() == "docx":
                        # Check for both .docx and .doc extensions
                        if not (
                            file_name.lower().endswith(".docx")
                            or file_name.lower().endswith(".doc")
                        ):
                            continue
                    elif file_type.lower() == "doc":
                        # Check for both .docx and .doc extensions
                        if not (
                            file_name.lower().endswith(".docx")
                            or file_name.lower().endswith(".doc")
                        ):
                            continue
                    elif file_type.lower() == "ppt":
                        # Check for both .ppt and .pptx extensions
                        if not (
                            file_name.lower().endswith(".ppt")
                            or file_name.lower().endswith(".pptx")
                        ):
                            continue
                    elif file_type.lower() == "pptx":
                        # Check for both .ppt and .pptx extensions
                        if not (
                            file_name.lower().endswith(".ppt")
                            or file_name.lower().endswith(".pptx")
                        ):
                            continue
                    elif file_type.lower() == "xls":
                        # Check for both .xls and .xlsx extensions
                        if not (
                            file_name.lower().endswith(".xls")
                            or file_name.lower().endswith(".xlsx")
                        ):
                            continue
                    elif file_type.lower() == "xlsx":
                        # Check for both .xls and .xlsx extensions
                        if not (
                            file_name.lower().endswith(".xls")
                            or file_name.lower().endswith(".xlsx")
                        ):
                            continue
                    else:
                        # For other file types, just check the extension
                        if not file_name.lower().endswith(f".{file_type.lower()}"):
                            continue

                # Add a property to identify if this might be a syllabus
                is_syllabus = "syllabus" in file_name.lower()

                result.append(
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
                        "is_syllabus": is_syllabus,
                    }
                )

            return result
        except Exception as e:
            logger.error(f"Error getting files: {e}")
            return [{"error": f"Error getting files: {e}"}]

    @mcp.tool()
    def extract_text_from_course_file(
        ctx: Context, file_url: str, file_type: str = None
    ) -> dict[str, Any]:
        """
        Extract text from a file.

        Args:
            ctx: Request context containing resources
            file_url: URL of the file
            file_type: Optional file type to override auto-detection ('pdf', 'docx', 'url')

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Import here to avoid circular imports
            from canvas_mcp.utils.file_extractor import extract_text_from_file

            result = extract_text_from_file(file_url, file_type)

            if result["success"]:
                return {
                    "success": True,
                    "file_url": file_url,
                    "file_type": result["file_type"],
                    "text_length": len(result["text"]),
                    "text": result["text"],
                }
            else:
                return {
                    "success": False,
                    "file_url": file_url,
                    "file_type": result.get("file_type"),
                    "error": result.get("error", "Failed to extract text from file"),
                }
        except Exception as e:
            logger.error(f"Error in extract_text_from_course_file: {str(e)}")
            return {
                "success": False,
                "file_url": file_url,
                "error": f"Error extracting text: {str(e)}",
            }
