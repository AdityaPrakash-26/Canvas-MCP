"""
Tests for the MCP server sync-related endpoints.
"""
import pytest
from unittest.mock import MagicMock

from canvas_mcp.server import sync_canvas_data


def test_sync_canvas_data_tool(mock_canvas_client):
    """Test the sync_canvas_data MCP tool wrapper."""
    # Mock the underlying client method
    expected_sync_result = {"courses": 1, "assignments": 5, "modules": 3, "announcements": 2}
    mock_canvas_client.sync_all.return_value = expected_sync_result
    
    # Call the tool function
    result = sync_canvas_data(term_id=-1)
    
    # Verify the client method was called with correct parameters
    mock_canvas_client.sync_all.assert_called_once_with(term_id=-1)
    
    # Verify the result is passed through
    assert result == expected_sync_result


def test_sync_canvas_data_with_specified_term(mock_canvas_client):
    """Test the sync_canvas_data tool with a specified term."""
    # Reset any previous calls
    mock_canvas_client.sync_all.reset_mock()
    
    # Mock the underlying client method
    expected_sync_result = {"courses": 2, "assignments": 10, "modules": 6, "announcements": 4}
    mock_canvas_client.sync_all.return_value = expected_sync_result
    
    # Call the tool function with a specific term ID
    specific_term_id = 123
    result = sync_canvas_data(term_id=specific_term_id)
    
    # Verify the client method was called with the correct term_id
    mock_canvas_client.sync_all.assert_called_once_with(term_id=specific_term_id)
    
    # Verify the result is passed through
    assert result == expected_sync_result


def test_sync_canvas_data_tool_no_client(mock_canvas_client):
    """Test sync tool when canvas client is not initialized."""
    # Simulate uninitialized client
    mock_canvas_client.canvas = None
    
    # Call the tool function
    result = sync_canvas_data()
    
    # Verify error response
    assert "error" in result
    assert "Canvas API client not initialized" in result["error"]
    
    # Verify sync_all was not called
    mock_canvas_client.sync_all.assert_not_called()
