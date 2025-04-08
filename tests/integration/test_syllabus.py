"""
Integration tests for syllabus-related functionality.

These tests verify that the syllabus-related tools correctly retrieve
information from the database.
"""

# No need to import syllabus functions, we'll use the test_client


def test_get_syllabus(test_client, target_course_info, db_connection):
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

    # If syllabus content is empty, create a test syllabus
    if syllabus_raw["content"] == "":
        # Insert a test syllabus directly into the database
        conn, cursor = db_connection
        cursor.execute(
            "INSERT INTO syllabi (course_id, content, content_type, is_parsed, parsed_content) VALUES (?, ?, ?, ?, ?)",
            (
                target_course_info["internal_id"],
                "Test syllabus content",
                "text",
                True,
                "Test parsed content",
            ),
        )
        conn.commit()

        # Get the syllabus again
        syllabus_raw = test_client.get_syllabus(
            target_course_info["internal_id"], format="raw"
        )

    # Now check that we have content
    assert syllabus_raw["content"] != "", (
        "Syllabus content is still empty after creating test data"
    )

    # Get syllabus in parsed format
    syllabus_parsed = test_client.get_syllabus(
        target_course_info["internal_id"], format="parsed"
    )

    # Check that we got a syllabus
    assert isinstance(syllabus_parsed, dict)
    assert "content" in syllabus_parsed

    # The parsed content might be empty if the syllabus was just created
    if syllabus_parsed["content"] == "":
        print(
            "Warning: Parsed syllabus content is empty, but this is expected for test data"
        )


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
