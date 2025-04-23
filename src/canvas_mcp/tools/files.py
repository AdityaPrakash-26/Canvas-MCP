"""
Canvas MCP File Tools

This module contains tools for accessing file information and content.
"""

import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

# Import the refactored utility function
from canvas_mcp.utils.file_extractor import extract_text_from_file

logger = logging.getLogger(__name__)


def register_file_tools(mcp: FastMCP) -> None:
    """Register file tools with the MCP server."""

    @mcp.tool()
    def get_course_files(ctx: Context, course_id: int) -> list[dict[str, Any]]:
        """
        Get all files available in a specific course.

        Returns metadata including file names and URLs. Use 'extract_text_from_course_file'
        with the returned URL to get the content of supported file types.

        Args:
            ctx: Request context containing resources
            course_id: Course ID

        Returns:
            List of files with URLs and metadata.
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
        ctx: Context, source_url_or_path: str, file_type: str = None
    ) -> dict[str, Any]:
        """
        Extract text content from a file or URL (output is Markdown formatted text).

        Uses the MarkItDown library internally to attempt conversion for various formats,
        including PDF, DOCX, PPTX, XLSX, HTML, common image/audio types, YouTube URLs, and more.
        Provide the URL obtained from tools like 'get_course_files'.

        Args:
            source_url_or_path: URL or local path of the file/resource.
            file_type: Optional file type hint (generally ignored by MarkItDown).

        Returns:
            Dictionary with extracted Markdown text and metadata, or an error if extraction fails.
            Example Success: {'success': True, 'file_type': 'pdf', 'text': '# Syllabus...', 'source': '...'}
            Example Failure: {'success': False, 'error': 'Failed to convert...', 'source': '...'}
        """
        if not source_url_or_path:
            return {
                "success": False,
                "error": "Missing required parameter: source_url_or_path",
                "source_url_or_path": source_url_or_path,
            }
        try:
            # TODO: if the url contains the word `verifier`, we have to do a two step download by fetching file metadata from the canvas API
            # ex https://canvas.instructure.com/courses/6592~142317/files/6592~13888362?verifier=sKwTGzXkRigupF3vZXvXjrF0UpYXl9pWp39fTPmj&amp;wrap=1

            # Call the refactored utility function from canvas_mcp.utils.file_extractor
            result = extract_text_from_file(source_url_or_path, file_type)

            # Return the result directly as its format matches the expected output
            return result

        except Exception as e:
            logger.error(f"Error in extract_text_from_course_file: {str(e)}")
            return {
                "success": False,
                # Use the input parameter name in the error response
                "source_url_or_path": source_url_or_path,
                "error": f"Unexpected error during text extraction: {str(e)}",
            }
