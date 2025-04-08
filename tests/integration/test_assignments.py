"""
Integration tests for assignment-related functionality.

These tests verify that the assignment-related tools correctly retrieve
information from the database.
"""

# No need to import assignment functions, we'll use the test_client


def test_get_course_assignments(test_client, target_course_info):
    """Test getting assignments for a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get assignments
    assignments = test_client.get_course_assignments(target_course_info["internal_id"])

    # Check that we got a list of assignments
    assert isinstance(assignments, list)
    assert len(assignments) > 0, (
        f"No assignments found for course {target_course_info['internal_id']}"
    )
    print(
        f"Found {len(assignments)} assignments for course {target_course_info['internal_id']}"
    )

    # Print some assignment details for debugging
    print(f"First assignment: {assignments[0].get('title')}")

    # Store the first assignment name for later tests
    target_course_info["test_assignment_name"] = assignments[0]["title"]


def test_get_upcoming_deadlines(test_client, target_course_info):
    """Test getting upcoming deadlines."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get upcoming deadlines for all courses
    all_deadlines = test_client.get_upcoming_deadlines(days=30)

    # Check that we got a list of deadlines
    assert isinstance(all_deadlines, list)
    assert len(all_deadlines) > 0, "No upcoming deadlines found across all courses"
    print(f"Found {len(all_deadlines)} upcoming deadlines across all courses")

    # Get upcoming deadlines for the target course
    course_deadlines = test_client.get_upcoming_deadlines(
        days=30, course_id=target_course_info["internal_id"]
    )

    # Check that we got a list of deadlines
    assert isinstance(course_deadlines, list)
    # It's possible there are no upcoming deadlines for this specific course
    # So we'll just print the result instead of asserting
    if len(course_deadlines) > 0:
        print(
            f"Found {len(course_deadlines)} upcoming deadlines for course {target_course_info['internal_id']}"
        )
    else:
        print(
            f"No upcoming deadlines found for course {target_course_info['internal_id']}"
        )


def test_get_assignment_details(test_client, target_course_info):
    """Test getting details for a specific assignment."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Ensure we have an assignment name
    assert "test_assignment_name" in target_course_info, (
        "No assignment name available for testing"
    )

    assignment_name = target_course_info["test_assignment_name"]

    # Get details for the assignment
    result = test_client.get_assignment_details(
        target_course_info["internal_id"], assignment_name
    )

    # Check that we got a result
    assert isinstance(result, dict)
    assert "error" not in result, (
        f"Error getting assignment details: {result.get('error')}"
    )
    assert "assignment" in result
    assert "course_code" in result
    assert "course_name" in result

    print(f"Tested assignment details for: {assignment_name}")
