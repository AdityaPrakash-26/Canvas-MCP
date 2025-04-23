"""
Unit tests for the formatters module.

These tests verify that the formatter functions work correctly.
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock

from canvas_mcp.utils.formatters import convert_html_to_markdown, format_date


def test_convert_html_to_markdown_simple():
    """Test the convert_html_to_markdown function with a simple HTML string."""
    # Test with a simple HTML string
    html = "<p>Hello <strong>World</strong></p>"
    expected_markdown = "Hello **World**"

    # Call the function
    result = convert_html_to_markdown(html)

    # Verify the result
    assert result is not None
    assert result.strip() == expected_markdown


def test_convert_html_to_markdown_complex():
    """Test the convert_html_to_markdown function with a more complex HTML string."""
    # Test with a more complex HTML string
    html = """
    <div>
        <h1>Title</h1>
        <p>This is a <em>paragraph</em> with <strong>bold</strong> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
    """

    # Call the function
    result = convert_html_to_markdown(html)

    # Verify the result
    assert result is not None
    assert "Title" in result
    assert "paragraph" in result
    assert (
        "*paragraph*" in result or "_paragraph_" in result
    )  # Different markdown libs might use different syntax
    assert "**bold**" in result
    assert "Item 1" in result
    assert "Item 2" in result


def test_convert_html_to_markdown_empty():
    """Test the convert_html_to_markdown function with an empty string."""
    # Test with an empty string
    result = convert_html_to_markdown("")

    # Verify the result
    assert result == ""


def test_convert_html_to_markdown_none():
    """Test the convert_html_to_markdown function with None."""
    # Test with None
    result = convert_html_to_markdown(None)

    # Verify the result
    assert result == ""


@patch("markitdown.MarkItDown.convert")
def test_convert_html_to_markdown_exception(mock_convert):
    """Test the convert_html_to_markdown function when an exception occurs."""
    # Configure the mock to raise an exception
    mock_convert.side_effect = Exception("Test exception")

    # Call the function
    result = convert_html_to_markdown("<p>Test</p>")

    # Verify the result
    assert result is None


def test_format_date(mock_datetime):  # mock_datetime ensures consistent date formatting
    """Test the format_date function."""
    # Test today
    today = "2025-04-05T14:30:00"
    formatted = format_date(today)
    assert formatted == "Today at 02:30 PM"

    # Test yesterday
    yesterday = "2025-04-04T09:15:00"
    formatted = format_date(yesterday)
    assert formatted == "Yesterday at 09:15 AM"

    # Test this week
    this_week = "2025-04-02T18:45:00"
    formatted = format_date(this_week)
    assert formatted == "Wednesday, April 02 at 06:45 PM"

    # Test older date
    older_date = "2025-03-15T12:00:00"
    formatted = format_date(older_date)
    assert formatted == "March 15, 2025 at 12:00 PM"
