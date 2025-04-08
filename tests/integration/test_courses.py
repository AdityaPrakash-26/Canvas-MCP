"""
Integration tests for course-related functionality.

These tests verify that the course-related tools correctly retrieve
information from the database.
"""

# No need to import get_course_list, we'll use the test_client

import pytest


def test_get_course_list(test_client, target_course_info):
    """Test getting the list of courses."""
    # Get course list
    courses = test_client.get_course_list()

    # Check that we got a list of courses
    assert isinstance(courses, list)
    assert len(courses) > 0, "No courses found in the database"

    # Look for our target course
    target_course = None
    for course in courses:
        if (
            course.get("course_code") == target_course_info["code"]
            or course.get("canvas_course_id") == target_course_info["canvas_id"]
        ):
            target_course = course
            break

    # Ensure we found the target course
    assert target_course is not None, (
        f"Target course {target_course_info['code']} not found in course list"
    )


def test_course_list_filtering(test_client, canvas_client, db_connection):
    """Test that the course list only contains active courses from the current term."""
    # Get course list from the database
    courses = test_client.get_course_list()

    # Get active courses directly from Canvas API
    user = canvas_client.canvas.get_current_user()
    active_courses = list(user.get_courses(enrollment_state="active"))

    # Get term IDs from active courses
    term_ids = set()
    for course in active_courses:
        term_id = getattr(course, "enrollment_term_id", None)
        if term_id:
            term_ids.add(term_id)

    # Skip test if there's only one term in the test data
    if len(term_ids) <= 1:
        pytest.skip("Test data doesn't have multiple terms")

    # Find the most recent term
    max_term_id = max(term_ids)

    # Count courses in the most recent term
    current_term_courses = [
        course
        for course in active_courses
        if getattr(course, "enrollment_term_id", None) == max_term_id
    ]

    # Verify that the number of courses in the database matches the number of
    # active courses in the current term
    assert len(courses) == len(current_term_courses), (
        f"Expected {len(current_term_courses)} courses in database, but found {len(courses)}"
    )

    # Verify that all courses in the database are from the current term
    # by checking if any course from a different term exists in the database
    _, cursor = db_connection
    for course in active_courses:
        if getattr(course, "enrollment_term_id", None) != max_term_id:
            # This course is from a different term, it should not be in the database
            canvas_id = getattr(course, "id", None)
            if canvas_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM courses WHERE canvas_course_id = ?",
                    (canvas_id,),
                )
                count = cursor.fetchone()[0]
                assert count == 0, (
                    f"Course from different term (ID: {canvas_id}) found in database"
                )
