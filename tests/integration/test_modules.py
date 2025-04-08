"""
Integration tests for module-related functionality.

These tests verify that the module-related tools correctly retrieve
information from the database.
"""

# No need to import module functions, we'll use the test_client


def test_get_course_modules(test_client, target_course_info):
    """Test getting modules for a course."""
    # Ensure we have the target course ID
    assert target_course_info["internal_id"] is not None, "Target course ID is required"

    # Get modules without items
    modules = test_client.get_course_modules(
        target_course_info["internal_id"], include_items=False
    )

    # Check that we got a list of modules
    assert isinstance(modules, list)
    print(
        f"Found {len(modules)} modules for course {target_course_info['internal_id']}"
    )

    # If there are no modules, that's okay for this course
    if len(modules) == 0:
        print("No modules found for this course, which is expected for some courses.")
        return

    # Get modules with items (only if we have modules)
    modules_with_items = test_client.get_course_modules(
        target_course_info["internal_id"], include_items=True
    )

    # Check that we got a list of modules with items
    assert isinstance(modules_with_items, list)
    assert len(modules_with_items) == len(
        modules
    ), "Module count mismatch between calls with and without items"

    # Check if any modules have items
    has_items = any(
        "items" in module and module["items"] for module in modules_with_items
    )
    print(f"Modules with items: {has_items}")
