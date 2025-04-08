"""
Integration tests for Canvas data synchronization.

These tests verify that the sync_canvas_data tool correctly synchronizes
data from Canvas to the local database.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from tests.conftest import CACHE_METADATA_PATH, CACHED_DB_PATH, TEST_DB_PATH

# No need to import sync_canvas_data, we'll use the test_client


def cache_database(source_path: Path, cache_path: Path, metadata_path: Path) -> None:
    """Cache the database for future test runs."""
    # Ensure the parent directory exists
    os.makedirs(cache_path.parent, exist_ok=True)

    # Copy the database to the cache location
    print(f"Caching database to: {cache_path}")
    shutil.copy2(source_path, cache_path)

    # Write the cache timestamp
    timestamp = datetime.now().isoformat()
    with open(metadata_path, "w") as f:
        f.write(timestamp)

    print(f"Database cached successfully at: {timestamp}")


def test_sync_canvas_data(test_client, db_connection, target_course_info):
    """Test synchronizing data from Canvas."""
    # Ensure Canvas API key is available
    assert os.environ.get("CANVAS_API_KEY"), (
        "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests"
    )

    # Run the sync with Canvas API
    print("Running sync_canvas_data...")
    result = test_client.sync_canvas_data()
    print(f"Sync result: {result}")

    # Check that we got some data
    assert isinstance(result, dict)
    # Check for potential error key first
    assert "error" not in result, f"Sync failed with error: {result.get('error')}"
    assert "courses" in result
    # Allow for 0 if the API key only has access to opted-out courses
    assert result["courses"] >= 0
    if result["courses"] == 0:
        print("Warning: 0 courses synced. Check API key permissions and term filters.")
    else:
        print(f"Synced {result['courses']} courses.")

    # Verify our target course exists after sync
    _, cursor = db_connection
    print(f"Verifying target course with Canvas ID: {target_course_info['canvas_id']}")
    cursor.execute(
        "SELECT id, course_code FROM courses WHERE canvas_course_id = ?",
        (target_course_info["canvas_id"],),
    )
    course_data = cursor.fetchone()

    # The target course must exist
    assert course_data is not None, (
        f"Target course with Canvas ID {target_course_info['canvas_id']} not found after sync"
    )

    # Update target_course_info with the internal ID
    target_course_info["internal_id"] = course_data["id"]
    # Update the code in case it changed during sync
    target_course_info["code"] = course_data["course_code"]
    print(
        f"Confirmed target course exists. Internal ID: {target_course_info['internal_id']}, "
        f"Code: {target_course_info['code']}"
    )

    # Cache the database for future test runs
    cache_database(TEST_DB_PATH, CACHED_DB_PATH, CACHE_METADATA_PATH)


def test_sync_filters_dropped_courses(test_client, db_connection, api_adapter):
    """Test that sync filters out dropped courses."""
    # Ensure Canvas API key is available
    assert os.environ.get("CANVAS_API_KEY"), (
        "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests"
    )

    # Get all courses directly from Canvas API
    user = api_adapter.get_current_user_raw()
    all_courses = api_adapter.get_courses_raw(user)

    # Get active courses directly from Canvas API
    active_courses = api_adapter.get_courses_raw(user, enrollment_state="active")

    # Skip test if all courses are active (no dropped courses to test with)
    if len(all_courses) == len(active_courses):
        pytest.skip("No dropped courses found to test with")

    # Run the sync with Canvas API
    print("Running sync_canvas_data...")
    result = test_client.sync_canvas_data()
    print(f"Sync result: {result}")

    # Verify that the number of synced courses matches the number of active courses
    # in the current term
    _, cursor = db_connection
    cursor.execute("SELECT COUNT(*) FROM courses")
    db_course_count = cursor.fetchone()[0]

    # Get term IDs from active courses
    term_ids = set()
    for course in active_courses:
        term_id = getattr(course, "enrollment_term_id", None)
        if term_id:
            term_ids.add(term_id)

    # Find the most recent term
    if term_ids:
        max_term_id = max(term_ids)

        # Count courses in the most recent term
        current_term_courses = [
            course
            for course in active_courses
            if getattr(course, "enrollment_term_id", None) == max_term_id
        ]

        # Verify that the number of courses in the database matches the number of
        # active courses in the current term
        assert db_course_count == len(current_term_courses), (
            f"Expected {len(current_term_courses)} courses in database, but found {db_course_count}"
        )
    else:
        # If no term IDs found, just check that we have the right number of active courses
        assert db_course_count == len(active_courses), (
            f"Expected {len(active_courses)} courses in database, but found {db_course_count}"
        )
