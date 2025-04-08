"""
Integration tests for file-related functionality.

These tests verify that the file-related tools correctly retrieve
information from the database and extract text from files.
"""

import pytest

from canvas_mcp.tools.files import get_course_files, extract_text_from_course_file


def test_get_course_files(test_context, target_course_info):
    """Test getting files for a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get all files
    files = get_course_files(test_context, target_course_info["internal_id"])

    # Check that we got a list of files
    assert isinstance(files, list)
    print(f"Found {len(files)} files for course {target_course_info['internal_id']}")

    # If there are no files, we can't continue with the test
    if len(files) == 0:
        print("No files found for this course, skipping file tests.")
        # Set a dummy URL for later tests to skip
        target_course_info["test_pdf_url"] = None
        return

    # Get PDF files
    pdf_files = get_course_files(test_context, target_course_info["internal_id"], file_type="pdf")

    # Check that we got a list of PDF files
    assert isinstance(pdf_files, list)
    print(
        f"Found {len(pdf_files)} PDF files for course {target_course_info['internal_id']}"
    )

    # If there are no PDF files, we can't continue with the test
    if len(pdf_files) == 0:
        print("No PDF files found for this course, skipping PDF tests.")
        # Set a dummy URL for later tests to skip
        target_course_info["test_pdf_url"] = None
        return

    # Store a PDF file URL for later tests
    target_course_info["test_pdf_url"] = pdf_files[0].get("url")
    assert target_course_info["test_pdf_url"] is not None, "PDF file URL is required for later tests"
    print(f"Found PDF file: {pdf_files[0].get('name')}")


def test_extract_text_from_course_file(test_context, target_course_info):
    """Test extracting text from a course file."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Check if we have a PDF file URL from the previous test
    if "test_pdf_url" not in target_course_info or target_course_info["test_pdf_url"] is None:
        pytest.skip("No PDF file URL available, skipping text extraction test.")

    # Extract text from the file
    result = extract_text_from_course_file(
        test_context,
        target_course_info["test_pdf_url"],
        file_type="pdf",
    )

    # Check that we got a successful result
    assert isinstance(result, dict)
    assert result.get("success"), f"Failed to extract text: {result.get('error')}"

    # Check the text content
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0, "Extracted text is empty"
    print(f"Extracted {result.get('text_length', 0)} characters of text")
