"""
Tests for the MCP server course-related endpoints.
"""
from datetime import datetime, timedelta

import pytest

from canvas_mcp.models import Course, Syllabus, UserCourse
from canvas_mcp.server import (
    get_course_list,
    get_course_assignments,
    get_course_modules,
    get_syllabus,
    opt_out_course,
)


def test_get_course_list(server_session):
    """Test retrieving the list of courses."""
    courses = get_course_list()
    
    # Verify two courses are returned
    assert len(courses) == 2
    
    # Verify course data
    course_codes = {c['course_code'] for c in courses}
    assert "CS101" in course_codes
    assert "MATH200" in course_codes
    
    # Verify structure
    assert "id" in courses[0]
    assert "canvas_course_id" in courses[0]


def test_get_course_assignments(server_session):
    """Test retrieving assignments for a specific course."""
    # Test CS101 assignments
    assignments_cs101 = get_course_assignments(course_id=1)
    assert len(assignments_cs101) == 3  # PA1, Midterm, Past Assignment
    
    # Verify all expected assignments are present (order may vary)
    titles_cs101 = [a['title'] for a in assignments_cs101]
    assert "Past Assignment 0" in titles_cs101
    assert "Programming Assignment 1" in titles_cs101
    assert "Midterm Exam" in titles_cs101
    
    # Test MATH200 assignments
    assignments_math200 = get_course_assignments(course_id=2)
    assert len(assignments_math200) == 1
    assert assignments_math200[0]['title'] == "Calculus Problem Set 1"


def test_get_course_modules(server_session):
    """Test retrieving modules for a specific course."""
    # Test without items
    modules_no_items = get_course_modules(course_id=1)
    assert len(modules_no_items) == 2
    assert modules_no_items[0]['name'] == "Week 1: Introduction"
    assert modules_no_items[1]['name'] == "Week 2: Variables"
    assert "items" not in modules_no_items[0]
    
    # Test with items
    modules_with_items = get_course_modules(course_id=1, include_items=True)
    assert len(modules_with_items) == 2
    
    # Check module 1 items
    assert len(modules_with_items[0]['items']) == 2
    assert modules_with_items[0]['items'][0]['title'] == "Intro Lecture Notes"
    assert modules_with_items[0]['items'][1]['title'] == "Setup Python Environment"
    
    # Check module 2 items
    assert len(modules_with_items[1]['items']) == 1
    assert modules_with_items[1]['items'][0]['title'] == "Programming Assignment 1"
    
    # Test for course with no modules
    modules_math200 = get_course_modules(course_id=2)
    assert len(modules_math200) == 0


def test_get_syllabus(server_session):
    """Test retrieving syllabus content."""
    # Test raw format (should return HTML)
    syllabus_raw = get_syllabus(course_id=1, format="raw")
    assert syllabus_raw['course_code'] == "CS101"
    assert syllabus_raw['content'] == "<p>This is the CS101 syllabus</p>"
    
    # Test parsed format (should return plain text)
    syllabus_parsed = get_syllabus(course_id=1, format="parsed")
    assert syllabus_parsed['course_code'] == "CS101"
    assert syllabus_parsed['content'] == "This is the CS101 syllabus in plain text format."
    
    # Test course with syllabus but no parsed content (should return raw)
    syllabus_math_raw = get_syllabus(course_id=2, format="raw")
    assert syllabus_math_raw['content'] == "<p>This is the MATH200 syllabus</p>"
    
    # Request parsed but fall back to raw when parsed not available
    syllabus_math_parsed = get_syllabus(course_id=2, format="parsed")
    assert syllabus_math_parsed['content'] == "<p>This is the MATH200 syllabus</p>"
    
    # Test non-existent course
    syllabus_none = get_syllabus(course_id=999)
    assert "error" in syllabus_none
    assert "not found" in syllabus_none["error"]


def test_opt_out_course(server_session):
    """Test opting a course in/out for a user."""
    user = "test_user1"
    course_id = 1
    
    # Opt out
    result_out = opt_out_course(course_id=course_id, user_id=user, opt_out=True)
    assert result_out["success"] is True
    assert result_out["opted_out"] is True
    
    # Need to refresh the session to see changes made by the function
    server_session.expire_all()
    
    # Verify in DB
    pref = server_session.query(UserCourse).filter_by(user_id=user, course_id=course_id).one()
    assert pref.indexing_opt_out is True
    
    # Opt back in
    result_in = opt_out_course(course_id=course_id, user_id=user, opt_out=False)
    assert result_in["success"] is True
    assert result_in["opted_out"] is False
    
    # Need to refresh the session to see changes made by the function
    server_session.expire_all()
    
    # Verify in DB
    pref = server_session.query(UserCourse).filter_by(user_id=user, course_id=course_id).one()
    assert pref.indexing_opt_out is False
    
    # Test non-existent course
    result_bad_course = opt_out_course(course_id=999, user_id=user, opt_out=True)
    assert result_bad_course["success"] is False
    assert "not found" in result_bad_course["message"]
