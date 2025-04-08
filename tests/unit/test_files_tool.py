"""
Unit tests for the files tools.

These tests verify that the files tools correctly interact with the Canvas client.
"""

from types import SimpleNamespace
from unittest.mock import patch

from canvas_mcp.tools.files import register_file_tools


class TestFilesTools:
    """Test the files tools."""

    @patch("canvas_mcp.utils.file_extractor.extract_text_from_file")
    def test_extract_text_from_course_file_success(self, mock_extract, canvas_client):
        """Test the extract_text_from_course_file tool with successful extraction."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    # Store the function with its name
                    setattr(self, func.__name__, func)
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_file_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"canvas_client": canvas_client}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Mock the extract_text_from_file function
        mock_extract.return_value = {
            "success": True,
            "file_type": "pdf",
            "text": "This is the extracted text from the PDF file.",
        }

        # Call the extract_text_from_course_file tool
        result = mock_mcp.extract_text_from_course_file(
            ctx, "https://example.com/file.pdf"
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "text" in result
        assert "text_length" in result
        assert result["file_type"] == "pdf"

    @patch("canvas_mcp.utils.file_extractor.extract_text_from_file")
    def test_extract_text_from_course_file_failure(self, mock_extract, canvas_client):
        """Test the extract_text_from_course_file tool with failed extraction."""

        # Create a mock MCP server
        class MockMCP:
            def tool(self):
                def decorator(func):
                    # Store the function with its name
                    setattr(self, func.__name__, func)
                    return func

                return decorator

        # Register the tools
        mock_mcp = MockMCP()
        register_file_tools(mock_mcp)

        # Create a mock context
        lifespan_context = {"canvas_client": canvas_client}
        request_context = SimpleNamespace(lifespan_context=lifespan_context)
        ctx = SimpleNamespace(request_context=request_context)

        # Mock the extract_text_from_file function
        mock_extract.return_value = {
            "success": False,
            "file_type": "pdf",
            "error": "Failed to extract text from PDF file.",
        }

        # Call the extract_text_from_course_file tool
        result = mock_mcp.extract_text_from_course_file(
            ctx, "https://example.com/file.pdf"
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert result["file_type"] == "pdf"
