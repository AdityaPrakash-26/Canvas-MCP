"""
Main integration test file for Canvas MCP.

This file imports and runs all the integration tests in the correct order.
"""

import pytest

# Import all the test functions in the order they should be run
from tests.integration.test_announcements import test_get_course_announcements
from tests.integration.test_assignments import (
    test_get_assignment_details,
    test_get_course_assignments,
    test_get_upcoming_deadlines,
)
from tests.integration.test_courses import test_get_course_list
from tests.integration.test_files import (
    test_extract_text_from_course_file,
    test_get_course_files,
)
from tests.integration.test_modules import test_get_course_modules
from tests.integration.test_search import test_search_course_content
from tests.integration.test_syllabus import test_get_syllabus, test_get_syllabus_file
from tests.integration.test_sync import test_sync_canvas_data


# Define a test class that will run all the tests in order
class TestIntegration:
    """Integration tests for Canvas MCP."""

    def test_01_sync_canvas_data(self, test_client, db_connection, target_course_info):
        """Test synchronizing data from Canvas."""
        test_sync_canvas_data(test_client, db_connection, target_course_info)

    def test_02_get_course_list(self, test_client, target_course_info):
        """Test getting the list of courses."""
        test_get_course_list(test_client, target_course_info)

    def test_03_get_course_assignments(self, test_client, target_course_info):
        """Test getting assignments for a course."""
        test_get_course_assignments(test_client, target_course_info)

    def test_04_get_course_modules(self, test_client, target_course_info):
        """Test getting modules for a course."""
        test_get_course_modules(test_client, target_course_info)

    def test_05_get_syllabus(self, test_client, target_course_info):
        """Test getting the syllabus for a course."""
        test_get_syllabus(test_client, target_course_info)

    def test_06_get_course_files(self, test_client, target_course_info):
        """Test getting files for a course."""
        test_get_course_files(test_client, target_course_info)

    def test_07_extract_text_from_course_file(self, test_client, target_course_info):
        """Test extracting text from a course file."""
        test_extract_text_from_course_file(test_client, target_course_info)

    def test_08_get_assignment_details(self, test_client, target_course_info):
        """Test getting details for a specific assignment."""
        test_get_assignment_details(test_client, target_course_info)

    def test_09_search_course_content(self, test_client, target_course_info):
        """Test searching for content in a course."""
        test_search_course_content(test_client, target_course_info)

    def test_10_get_upcoming_deadlines(self, test_client, target_course_info):
        """Test getting upcoming deadlines."""
        test_get_upcoming_deadlines(test_client, target_course_info)

    def test_11_get_course_announcements(self, test_client, target_course_info):
        """Test getting course announcements."""
        test_get_course_announcements(test_client, target_course_info)

    def test_12_get_syllabus_file(self, test_client, target_course_info):
        """Test getting syllabus file for a course."""
        test_get_syllabus_file(test_client, target_course_info)
