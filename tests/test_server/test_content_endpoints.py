"""
Tests for the MCP server content-related endpoints.
"""


from canvas_mcp.server import (
    get_course_announcements,
    get_upcoming_deadlines,
    search_course_content,
)


def test_get_upcoming_deadlines(server_session):
    """Test retrieving upcoming deadlines."""
    # Test default (7 days)
    deadlines_7 = get_upcoming_deadlines(days=7)
    assert len(deadlines_7) == 1
    assert deadlines_7[0]['assignment_title'] == "Programming Assignment 1"
    assert deadlines_7[0]['course_code'] == "CS101"
    assert deadlines_7[0]['due_date'] is not None

    # Test longer range (30 days)
    deadlines_30 = get_upcoming_deadlines(days=30)
    assert len(deadlines_30) == 3  # PA1, Calc PS1, Midterm

    # Verify sorted by date
    assert deadlines_30[0]['assignment_title'] == "Programming Assignment 1"
    assert deadlines_30[1]['assignment_title'] == "Calculus Problem Set 1"
    assert deadlines_30[2]['assignment_title'] == "Midterm Exam"

    # Test with course filter
    deadlines_cs101 = get_upcoming_deadlines(days=30, course_id=1)
    assert len(deadlines_cs101) == 2
    assert deadlines_cs101[0]['assignment_title'] == "Programming Assignment 1"
    assert deadlines_cs101[1]['assignment_title'] == "Midterm Exam"

    deadlines_math200 = get_upcoming_deadlines(days=30, course_id=2)
    assert len(deadlines_math200) == 1
    assert deadlines_math200[0]['assignment_title'] == "Calculus Problem Set 1"


def test_get_course_announcements(server_session):
    """Test retrieving course announcements."""
    announcements_cs101 = get_course_announcements(course_id=1)
    assert len(announcements_cs101) == 2

    # Sorted by posted_at DESC
    assert announcements_cs101[0]['title'] == "Office Hours Updated"
    assert announcements_cs101[1]['title'] == "Welcome to CS101"

    # Test limit
    announcements_limit_1 = get_course_announcements(course_id=1, limit=1)
    assert len(announcements_limit_1) == 1
    assert announcements_limit_1[0]['title'] == "Office Hours Updated"

    # Test course with no announcements
    announcements_math200 = get_course_announcements(course_id=2)
    assert len(announcements_math200) == 0


def test_search_course_content(server_session):
    """Test searching across course content."""
    # Search for "Python" (should be in assignment 1 description and module item)
    results_python = search_course_content("Python")
    assert len(results_python) == 2  # Assignment description + Module Item

    # Check result types
    result_types = {r['content_type'] for r in results_python}
    assert 'assignment' in result_types
    assert 'module_item' in result_types

    # Search for a term in an assignment title
    results_problem_set = search_course_content("Problem Set")
    assert len(results_problem_set) == 1
    assert results_problem_set[0]['content_type'] == 'assignment'
    assert results_problem_set[0]['title'] == 'Calculus Problem Set 1'

    # Search for "syllabus" (should match syllabus content)
    results_syllabus = search_course_content("syllabus")
    assert len(results_syllabus) == 2  # Matches content in both syllabi
    assert results_syllabus[0]['content_type'] == 'syllabus'

    # Search within a specific course
    results_python_cs101 = search_course_content("Python", course_id=1)
    assert len(results_python_cs101) == 2

    results_calculus_cs101 = search_course_content("Calculus", course_id=1)
    assert len(results_calculus_cs101) == 0

    # Search for non-existent term
    results_none = search_course_content("nonexistentxyz")
    assert len(results_none) == 0
