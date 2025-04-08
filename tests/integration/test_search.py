"""
Integration tests for search functionality.

These tests verify that the search-related tools correctly retrieve
information from the database.
"""

# No need to import search functions, we'll use the test_client


def test_search_course_content(test_client, target_course_info):
    """Test searching for content in a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Check if we have an assignment name from the previous test
    # If not, use a default search term that's likely to find something
    if (
        "test_assignment_name" in target_course_info
        and target_course_info["test_assignment_name"]
    ):
        # Use part of the assignment name as search term
        search_term = target_course_info["test_assignment_name"].split()[0]
    else:
        # Use a generic term that's likely to find something
        search_term = "First"  # Most courses have something with "First" in the title

    # Search for content
    results = test_client.search_course_content(
        search_term, target_course_info["internal_id"]
    )

    # Check that we got a list of results
    assert isinstance(results, list)
    assert len(results) > 0, f"No results found for search term '{search_term}'"
    print(f"Found {len(results)} results for search term '{search_term}'")
