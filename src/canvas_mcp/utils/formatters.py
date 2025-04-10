"""
Canvas MCP Formatters

This module contains utility functions for formatting data for display.
"""

import logging
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import markitdown
from markitdown import DocumentConverterResult, StreamInfo

# Instantiate MarkItDown once for efficiency
_MARKITDOWN_INSTANCE = markitdown.MarkItDown()


logger = logging.getLogger(__name__)


def format_date(date_str: str | None) -> str:
    """
    Format a date string for display.

    Args:
        date_str: ISO format date string

    Returns:
        Formatted date string
    """
    if not date_str:
        return "No date"

    try:
        # Parse the ISO format date string
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Get current date for comparison
        now = datetime.now(UTC)

        # Format based on how far in the future/past the date is
        if date.date() == now.date():
            return f"Today at {date.strftime('%I:%M %p')}"
        elif date.date() == (now + timedelta(days=1)).date():
            return f"Tomorrow at {date.strftime('%I:%M %p')}"
        elif date.date() == (now - timedelta(days=1)).date():
            return f"Yesterday at {date.strftime('%I:%M %p')}"
        elif abs((date.date() - now.date()).days) < 7:
            return date.strftime("%A, %B %d at %I:%M %p")
        else:
            return date.strftime("%B %d, %Y at %I:%M %p")
    except Exception as e:
        logger.error(f"Error formatting date {date_str}: {e}")
        return date_str


def format_deadlines(deadlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Format deadlines for display.

    Args:
        deadlines: List of deadline dictionaries

    Returns:
        List of formatted deadline dictionaries
    """
    formatted_deadlines = []

    for deadline in deadlines:
        formatted_deadline = deadline.copy()

        # Format the due date
        if "due_date" in formatted_deadline and formatted_deadline["due_date"]:
            formatted_deadline["formatted_due_date"] = format_date(
                formatted_deadline["due_date"]
            )

        formatted_deadlines.append(formatted_deadline)

    return formatted_deadlines


def format_communications(communications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Format communications for display.

    Args:
        communications: List of communication dictionaries

    Returns:
        List of formatted communication dictionaries
    """
    formatted_communications = []

    for comm in communications:
        formatted_comm = comm.copy()

        # Format the posted date
        if "posted_at" in formatted_comm and formatted_comm["posted_at"]:
            formatted_comm["formatted_posted_at"] = format_date(
                formatted_comm["posted_at"]
            )

        # Ensure content is never empty
        if "content" in formatted_comm and (
            not formatted_comm["content"] or formatted_comm["content"].strip() == ""
        ):
            formatted_comm["content"] = "[No content available]"

        formatted_communications.append(formatted_comm)

    return formatted_communications


def convert_html_to_markdown(html_string: str) -> str | None:
    """Converts an HTML string to Markdown using a shared MarkItDown instance.

    Args:
        html_string: The HTML content as a string.

    Returns:
        The converted Markdown content as a string, or None if conversion fails.
    """
    if not html_string:
        return ""

    try:
        # Convert the string to bytes and wrap it in BytesIO
        html_bytes: bytes = html_string.encode("utf-8")
        html_stream = BytesIO(html_bytes)

        # Provide StreamInfo to ensure correct handling
        stream_info = StreamInfo(mimetype="text/html", charset="utf-8")

        result: DocumentConverterResult = _MARKITDOWN_INSTANCE.convert(
            html_stream, stream_info=stream_info
        )
        return result.text_content
    except Exception as e:
        # Consider logging the error here
        print(f"Error converting HTML to Markdown: {e}")
        return None  # Or raise the exception, depending on desired behavior
