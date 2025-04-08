"""
Integration tests for course-related functionality.

These tests verify that the course-related tools correctly retrieve
information from the database.
"""

import pytest

from canvas_mcp.tools.courses import get_course_list


def test_get_course_list(test_context, target_course_info):
    """Test getting the list of courses."""
    # Get course list
    courses = get_course_list(test_context)

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

    # Store its internal ID if not already set
    if target_course_info["internal_id"] is None:
        target_course_info["internal_id"] = target_course["id"]
        print(
            f"Found target course with internal ID: {target_course_info['internal_id']}"
        )
