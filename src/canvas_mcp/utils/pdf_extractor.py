"""
PDF Content Extraction Utilities

This module provides utilities for extracting text content from PDF files,
either from local files or URLs. It's used for processing PDF syllabi
and other PDF documents in the Canvas MCP server.

This module is deprecated. Please use file_extractor.py instead, which
provides more comprehensive and unified file extraction capabilities.
"""

import os
import tempfile
from typing import Optional
import logging
import warnings

import requests
import pdfplumber

# Configure logging
logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "pdf_extractor.py is deprecated and will be removed in a future version. "
    "Please use file_extractor.py instead.",
    DeprecationWarning,
    stacklevel=2
)

# Forward imports from file_extractor for backward compatibility
from canvas_mcp.utils.file_extractor import (
    extract_text_from_pdf_url,
    extract_text_from_pdf_file,
)

def extract_text_from_pdf(source: str, max_pages: int = 50) -> Optional[str]:
    """
    Extract text from a PDF file or URL.
    This function is deprecated. Use file_extractor.extract_text_from_file instead.

    Args:
        source: Path to the PDF file or URL
        max_pages: Maximum number of pages to extract (default: 50)

    Returns:
        Extracted text as a string or None if extraction failed
    """
    warnings.warn(
        "extract_text_from_pdf is deprecated. Use file_extractor.extract_text_from_file instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if source.lower().startswith(('http://', 'https://')):
        return extract_text_from_pdf_url(source, max_pages)
    else:
        return extract_text_from_pdf_file(source, max_pages)
