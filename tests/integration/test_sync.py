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

from tests.conftest import CACHED_DB_PATH, CACHE_METADATA_PATH, TEST_DB_PATH

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
    assert os.environ.get(
        "CANVAS_API_KEY"
    ), "Canvas API key environment variable (CANVAS_API_KEY) is required for integration tests"

    # Run the sync with Canvas API
    print("Running sync_canvas_data...")
    result = test_client.sync_canvas_data(_force=True)
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
    assert (
        course_data is not None
    ), f"Target course with Canvas ID {target_course_info['canvas_id']} not found after sync"

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
