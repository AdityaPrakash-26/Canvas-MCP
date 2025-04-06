"""
PDF Content Extraction Utilities

This module provides utilities for extracting text content from PDF files,
either from local files or URLs. It's used for processing PDF syllabi
and other PDF documents in the Canvas MCP server.
"""

import os
import tempfile
from typing import Optional
import logging

import requests
import pdfplumber

# Configure logging
logger = logging.getLogger(__name__)


def extract_text_from_pdf_url(url: str, max_pages: int = 50) -> Optional[str]:
    """
    Download a PDF from a URL and extract its text content.

    Args:
        url: URL of the PDF file
        max_pages: Maximum number of pages to extract (default: 50)

    Returns:
        Extracted text as a string or None if extraction failed
    """
    try:
        # Download the PDF file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Raise exception for bad responses

        # Create a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_path = temp_pdf.name
            # Write the content to the temporary file
            for chunk in response.iter_content(chunk_size=8192):
                temp_pdf.write(chunk)

        # Extract text from the downloaded PDF
        text = extract_text_from_pdf_file(temp_path, max_pages)

        # Clean up the temporary file
        os.unlink(temp_path)

        return text

    except Exception as e:
        logger.error(f"Error extracting text from PDF URL {url}: {e}")
        return None


def extract_text_from_pdf_file(file_path: str, max_pages: int = 50) -> Optional[str]:
    """
    Extract text content from a local PDF file.

    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (default: 50)

    Returns:
        Extracted text as a string or None if extraction failed
    """
    try:
        text_content = []

        with pdfplumber.open(file_path) as pdf:
            # Limit to max_pages or the actual page count, whichever is smaller
            pages_to_extract = min(len(pdf.pages), max_pages)

            for i in range(pages_to_extract):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                if text:
                    text_content.append(text)

                # Also extract tables as text if available
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        table_text = "\n".join([" | ".join([cell or "" for cell in row]) for row in table])
                        text_content.append(f"\nTable:\n{table_text}\n")

        return "\n\n".join(text_content)

    except Exception as e:
        logger.error(f"Error extracting text from PDF file {file_path}: {e}")
        return None


def extract_text_from_pdf(source: str, max_pages: int = 50) -> Optional[str]:
    """
    Extract text from a PDF file or URL.

    Args:
        source: Path to the PDF file or URL
        max_pages: Maximum number of pages to extract (default: 50)

    Returns:
        Extracted text as a string or None if extraction failed
    """
    if source.lower().startswith(('http://', 'https://')):
        return extract_text_from_pdf_url(source, max_pages)
    else:
        return extract_text_from_pdf_file(source, max_pages)
