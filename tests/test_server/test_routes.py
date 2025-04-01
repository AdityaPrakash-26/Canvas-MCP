"""
Tests for the FastAPI server routes.
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from canvas_mcp.server import setup_routes


def test_root_endpoint(test_client: TestClient):
    """Test the root endpoint returns correct data."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_hello_endpoint(test_client: TestClient):
    """Test the hello endpoint returns expected data."""
    response = test_client.get("/hello")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Hello from Canvas MCP Server!"


def test_get_courses(test_client: TestClient, sample_course, db_session):
    """Test the get_courses endpoint returns courses from the database."""
    # Create a test course (using the sample_course fixture)
    
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint
        response = test_client.get("/courses")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our sample course in the response
    found_course = False
    for course in data:
        if course["id"] == sample_course.id:
            found_course = True
            assert course["course_name"] == sample_course.course_name
            assert course["course_code"] == sample_course.course_code
    
    assert found_course, "Sample course not found in response"


def test_get_course_by_id(test_client: TestClient, sample_course, db_session):
    """Test the get_course_by_id endpoint returns a specific course."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint
        response = test_client.get(f"/courses/{sample_course.id}")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_course.id
    assert data["course_name"] == sample_course.course_name
    assert data["course_code"] == sample_course.course_code


def test_get_course_not_found(test_client: TestClient, db_session):
    """Test the get_course_by_id endpoint returns 404 for nonexistent course."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint with a non-existent ID
        response = test_client.get("/courses/99999")
    
    # Check the response
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_get_assignments(test_client: TestClient, sample_course, sample_assignment, db_session):
    """Test the get_assignments endpoint returns assignments for a course."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint
        response = test_client.get(f"/courses/{sample_course.id}/assignments")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our sample assignment in the response
    found_assignment = False
    for assignment in data:
        if assignment["id"] == sample_assignment.id:
            found_assignment = True
            assert assignment["title"] == sample_assignment.title
            assert assignment["course_id"] == sample_course.id
    
    assert found_assignment, "Sample assignment not found in response"


def test_get_modules(test_client: TestClient, sample_course, sample_module, db_session):
    """Test the get_modules endpoint returns modules for a course."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint
        response = test_client.get(f"/courses/{sample_course.id}/modules")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our sample module in the response
    found_module = False
    for module in data:
        if module["id"] == sample_module.id:
            found_module = True
            assert module["name"] == sample_module.name
            assert module["course_id"] == sample_course.id
    
    assert found_module, "Sample module not found in response"


def test_get_announcements(test_client: TestClient, sample_course, sample_announcement, db_session):
    """Test the get_announcements endpoint returns announcements for a course."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint
        response = test_client.get(f"/courses/{sample_course.id}/announcements")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our sample announcement in the response
    found_announcement = False
    for announcement in data:
        if announcement["id"] == sample_announcement.id:
            found_announcement = True
            assert announcement["title"] == sample_announcement.title
            assert announcement["course_id"] == sample_course.id
    
    assert found_announcement, "Sample announcement not found in response"


def test_sync_canvas_endpoint(test_client: TestClient, db_session):
    """Test the sync_canvas endpoint triggers synchronization."""
    # Mock the sync function in the app
    with patch("canvas_mcp.server.sync_canvas") as mock_sync:
        mock_sync.return_value = {
            "status": "success",
            "courses_count": 1,
            "assignments_count": 5,
            "modules_count": 2,
            "module_items_count": 10,
            "announcements_count": 3
        }
        
        # Call the endpoint
        response = test_client.post("/sync/canvas")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["courses_count"] == 1
    assert data["assignments_count"] == 5


def test_search_courses(test_client: TestClient, sample_course, db_session):
    """Test the search_courses endpoint returns courses matching the query."""
    # Mock the database session in the app
    with patch("canvas_mcp.server.get_db") as mock_get_db:
        mock_get_db.return_value = db_session
        
        # Call the endpoint with a search query
        response = test_client.get("/courses/search", params={"q": "test"})
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our sample course in the response
    found_course = False
    for course in data:
        if course["id"] == sample_course.id:
            found_course = True
            assert course["course_name"] == sample_course.course_name
    
    assert found_course, "Sample course not found in search results"
