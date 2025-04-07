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
            # Get canvas client from the lifespan context
            canvas_client = ctx.request_context.lifespan_context["canvas_client"]
            
            files = canvas_client.extract_files_from_course(course_id, file_type)

            # Add extraction URLs if needed
            result = []
            for file in files:
                # Add a property to identify if this might be a syllabus
                is_syllabus = "syllabus" in file.get("name", "").lower()

                result.append(
                    {
                        "name": file.get("name", "Unnamed File"),
                        "url": file.get("url", ""),
                        "content_type": file.get("content_type", ""),
                        "size": file.get("size", ""),
                        "created_at": file.get("created_at", ""),
                        "updated_at": file.get("updated_at", ""),
                        "source": file.get("source", "unknown"),
                        "is_syllabus": is_syllabus,
                    }
                )

            return result
        except Exception as e:
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
