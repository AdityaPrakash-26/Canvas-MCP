"""
Test file extraction functionality.
"""

from unittest.mock import MagicMock, patch

from canvas_mcp.utils.file_extractor import (
    extract_text_from_file,
    extract_text_from_url,
)


def test_extract_text_from_file_auto_detection():
    """Test auto-detection of file types in extract_text_from_file."""
    with patch("canvas_mcp.utils.file_extractor.extract_text_from_pdf_url") as mock_pdf:
        mock_pdf.return_value = "PDF content"

        # Test PDF detection from URL
        result = extract_text_from_file("https://example.com/syllabus.pdf")
        assert result["success"] is True
        assert result["file_type"] == "pdf"
        assert result["text"] == "PDF content"

    with patch(
        "canvas_mcp.utils.file_extractor.extract_text_from_docx_url"
    ) as mock_docx:
        mock_docx.return_value = "DOCX content"

        # Test DOCX detection from URL
        result = extract_text_from_file("https://example.com/syllabus.docx")
        assert result["success"] is True
        assert result["file_type"] == "docx"
        assert result["text"] == "DOCX content"

    with patch("canvas_mcp.utils.file_extractor.extract_text_from_url") as mock_url:
        mock_url.return_value = "URL content"

        # Test URL detection
        result = extract_text_from_file("https://example.com/syllabus")
        assert result["success"] is True
        assert result["file_type"] == "url"
        assert result["text"] == "URL content"


def test_extract_text_from_file_explicit_type():
    """Test extract_text_from_file with explicit file type."""
    with patch("canvas_mcp.utils.file_extractor.extract_text_from_pdf_url") as mock_pdf:
        mock_pdf.return_value = "PDF content"

        # Test explicit PDF type
        result = extract_text_from_file("https://example.com/file", "pdf")
        assert result["success"] is True
        assert result["file_type"] == "pdf"
        assert result["text"] == "PDF content"

    with patch(
        "canvas_mcp.utils.file_extractor.extract_text_from_docx_url"
    ) as mock_docx:
        mock_docx.return_value = "DOCX content"

        # Test explicit DOCX type
        result = extract_text_from_file("https://example.com/file", "docx")
        assert result["success"] is True
        assert result["file_type"] == "docx"
        assert result["text"] == "DOCX content"


def test_extract_text_from_file_error_handling():
    """Test error handling in extract_text_from_file."""
    with patch("canvas_mcp.utils.file_extractor.extract_text_from_pdf_url") as mock_pdf:
        mock_pdf.side_effect = Exception("PDF extraction error")

        # Test error handling
        result = extract_text_from_file("https://example.com/syllabus.pdf")
        assert result["success"] is False
        assert result["error"] == "Error extracting text: PDF extraction error"

    # Test unsupported file type
    result = extract_text_from_file("https://example.com/file", "unsupported")
    assert result["success"] is False
    assert "Unsupported file type" in result["error"]


def test_url_content_extraction():
    """Test extraction from URLs with different content types."""
    # Mock response for HTML
    html_response = MagicMock()
    html_response.text = "<html><body><p>Test content</p></body></html>"
    html_response.headers = {"Content-Type": "text/html"}

    # Mock response for PDF
    pdf_response = MagicMock()
    pdf_response.headers = {"Content-Type": "application/pdf"}
    pdf_response.iter_content.return_value = [b"PDF content"]

    with (
        patch("canvas_mcp.utils.file_extractor.requests.get") as mock_get,
        patch(
            "canvas_mcp.utils.file_extractor.extract_text_from_pdf_file"
        ) as mock_pdf_extract,
        patch("tempfile.NamedTemporaryFile") as mock_tempfile,
        patch("os.unlink"),
    ):
        # Setup mock for HTML
        mock_get.return_value = html_response

        # Test HTML extraction
        result = extract_text_from_url("https://example.com/page.html")
        assert "Test content" in result

        # Setup mock for PDF
        mock_get.return_value = pdf_response
        mock_pdf_extract.return_value = "Extracted PDF content"
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test.pdf"

        # Test PDF extraction
        result = extract_text_from_url("https://example.com/file.pdf")
        assert result == "Extracted PDF content"
