"""
Integration tests for syllabus-related functionality.

These tests verify that the syllabus-related tools correctly retrieve
information from the database.
"""

# No need to import syllabus functions, we'll use the test_client


def test_get_syllabus(test_client, target_course_info):
    """Test getting the syllabus for a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get syllabus in raw format
    syllabus_raw = test_client.get_syllabus(
        target_course_info["internal_id"], format="raw"
    )

    # Check that we got a syllabus
    assert isinstance(syllabus_raw, dict)
    assert "content" in syllabus_raw
    assert "content_type" in syllabus_raw
    assert syllabus_raw["content"] != "", "Syllabus content is empty"

    # Get syllabus in parsed format
    syllabus_parsed = test_client.get_syllabus(
        target_course_info["internal_id"], format="parsed"
    )

    # Check that we got a syllabus
    assert isinstance(syllabus_parsed, dict)
    assert "content" in syllabus_parsed
    assert syllabus_parsed["content"] != "", "Parsed syllabus content is empty"


def test_get_syllabus_file(test_client, target_course_info):
    """Test getting syllabus file for a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get syllabus file for the target course
    result = test_client.get_syllabus_file(
        target_course_info["internal_id"], extract_content=False
    )

    # Check that we got a result
    assert isinstance(result, dict)
    print(f"Syllabus file search result: {result.get('success', False)}")

    # It's okay if no syllabus file is found, but we should still get a valid result
    if result.get("success", False):
        # Check the structure of the result
        assert "syllabus_file" in result
        assert "all_syllabus_files" in result

        # Check the structure of the syllabus file
        syllabus_file = result["syllabus_file"]
        assert "name" in syllabus_file
        assert "url" in syllabus_file
        print(f"Found syllabus file: {syllabus_file.get('name')}")
    else:
        # If no syllabus file was found, check that we got an error message
        assert "error" in result
        print(f"No syllabus file found: {result.get('error')}")
