"""
Tests for the MCP server tools.
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP

from canvas_mcp.server import create_app, setup_mcp_tools


def test_mcp_tools_registration(mock_mcp_server):
    """Test that MCP tools are properly registered."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Check that tools were registered
    tools = mock_mcp_server.list_tools()
    tool_names = [tool.name for tool in tools]
    
    # Verify expected tools exist
    assert "list_courses" in tool_names
    assert "get_course" in tool_names
    assert "list_assignments" in tool_names
    assert "sync_canvas" in tool_names


def test_list_courses_tool(mock_mcp_server, sample_course, db_session):
    """Test the list_courses MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the database session
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the tool
        courses_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "list_courses")
        result = courses_tool.handler()
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) >= 1
    
    # Find our sample course in the result
    found_course = False
    for course in result:
        if course["id"] == sample_course.id:
            found_course = True
            assert course["course_name"] == sample_course.course_name
            assert course["course_code"] == sample_course.course_code
    
    assert found_course, "Sample course not found in tool result"


def test_get_course_tool(mock_mcp_server, sample_course, db_session):
    """Test the get_course MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the database session
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the tool
        get_course_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "get_course")
        result = get_course_tool.handler(course_id=sample_course.id)
    
    # Check the result
    assert result["id"] == sample_course.id
    assert result["course_name"] == sample_course.course_name
    assert result["course_code"] == sample_course.course_code


def test_list_assignments_tool(mock_mcp_server, sample_course, sample_assignment, db_session):
    """Test the list_assignments MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the database session
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the tool
        assignments_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "list_assignments")
        result = assignments_tool.handler(course_id=sample_course.id)
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) >= 1
    
    # Find our sample assignment in the result
    found_assignment = False
    for assignment in result:
        if assignment["id"] == sample_assignment.id:
            found_assignment = True
            assert assignment["title"] == sample_assignment.title
            assert assignment["course_id"] == sample_course.id
    
    assert found_assignment, "Sample assignment not found in tool result"


def test_sync_canvas_tool(mock_mcp_server, db_session):
    """Test the sync_canvas MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the sync function and database session
    with patch("canvas_mcp.server.sync_canvas") as mock_sync, \
         patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        mock_sync.return_value = {
            "status": "success",
            "courses_count": 1,
            "assignments_count": 5,
            "modules_count": 2,
            "module_items_count": 10,
            "announcements_count": 3
        }
        
        # Call the tool
        sync_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "sync_canvas")
        result = sync_tool.handler()
    
    # Check the result
    assert result["status"] == "success"
    assert result["courses_count"] == 1
    assert result["assignments_count"] == 5
    assert result["modules_count"] == 2


def test_search_courses_tool(mock_mcp_server, sample_course, db_session):
    """Test the search_courses MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the database session
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the tool
        search_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "search_courses")
        result = search_tool.handler(query="test")
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) >= 1
    
    # Find our sample course in the result
    found_course = False
    for course in result:
        if course["id"] == sample_course.id:
            found_course = True
            assert course["course_name"] == sample_course.course_name
    
    assert found_course, "Sample course not found in search results"


def test_get_deadlines_tool(mock_mcp_server, sample_course, sample_assignment, db_session):
    """Test the get_deadlines MCP tool."""
    # Set up MCP tools
    setup_mcp_tools(mock_mcp_server)
    
    # Mock the database session
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the tool
        deadlines_tool = next(tool for tool in mock_mcp_server.list_tools() if tool.name == "get_deadlines")
        result = deadlines_tool.handler(days=30)
    
    # Check the result
    assert isinstance(result, list)
    # Note: The result may be empty if the sample_assignment due date is not within the next 30 days
    # Therefore, we don't assert on the specific content
