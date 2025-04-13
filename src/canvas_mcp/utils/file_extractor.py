"""
File Content Extraction Utilities

This module provides utilities for extracting content from different file types,
using the MarkItDown library. It handles various formats including URLs.
"""

import logging
from typing import Any

# Import MarkItDown
from markitdown import DocumentConverterResult, MarkItDown

# Configure logging
logger = logging.getLogger(__name__)


def extract_text_from_file(source: str, file_type: str | None = None) -> dict[str, Any]:
    """
    Extract text content from a file or URL using MarkItDown (output is Markdown).

    Args:
        source: Path or URL to the file/resource.
        file_type: (Optional) Hint for file type, used as fallback.

    Returns:
        Dictionary with extracted content and metadata:
            {
                "success": bool,      # Whether extraction was successful
                "file_type": str,     # Detected file type (or fallback)
                "text": str | None,   # Extracted Markdown text (None if failed, "" if empty)
                "error": str | None,  # Error message (None if successful)
                "source": str         # The original source path/URL
            }
    """
    if not source:
        # Return early for invalid input
        return {
            "success": False,
            "error": "No source provided",
            "file_type": None,
            "text": None,
            "source": source,
        }

    try:
        # Instantiate MarkItDown - using basic config for now.
        md = MarkItDown(enable_plugins=False)
        result: DocumentConverterResult | None = md.convert(source)

        if result and result.markdown is not None:
            # Successful conversion with text content
            return {
                "success": True,
                "text": result.markdown,
                "error": None,
                "source": source,
            }
        elif result:
            # Conversion succeeded but produced no text (e.g., empty file, image without OCR)
            logger.info(
                f"MarkItDown conversion for '{source}' succeeded but produced no text content."
            )
            return {
                "success": True,
                "file_type": result.metadata.get("file_type", file_type or "unknown"),
                "text": "",  # Return empty string for successful empty conversion
                "error": None,
                "source": source,
            }

    except Exception as e:
        logger.error(
            f"Exception during MarkItDown conversion for source '{source}': {e}",
            exc_info=True,
        )
        # General exception during the process
        return {
            "success": False,
            "file_type": file_type or "unknown",  # Fallback file type
            "text": None,
            "error": f"Exception during MarkItDown conversion: {str(e)}",
            "source": source,
        }
