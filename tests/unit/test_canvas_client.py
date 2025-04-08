"""
Unit tests for the CanvasClient class using the fake Canvas API.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.utils.db_manager import DatabaseManager
from tests.fakes.fake_canvasapi import FakeCanvas, patch_canvasapi

# Apply the patch before importing any code that uses canvasapi
patch_canvasapi()


class TestCanvasClient(unittest.TestCase):
    """Test the CanvasClient class with the fake Canvas API."""

    def setUp(self):
        """Set up the test environment."""
        # Create a test database
        self.db_path = Path("tests/test_data/test_unit.db")
        os.makedirs(self.db_path.parent, exist_ok=True)
        
        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            from init_db import create_database
            create_database(str(self.db_path))
        
        # Create a database manager
        self.db_manager = DatabaseManager(self.db_path)
        
        # Create a Canvas client with the fake Canvas API
        self.canvas_client = CanvasClient(self.db_manager, "fake_api_key")
    
    def test_sync_courses(self):
        """Test syncing courses from Canvas."""
        # Sync courses
        course_ids = self.canvas_client.sync_courses()
        
        # Verify that courses were synced
        self.assertIsInstance(course_ids, list)
        self.assertGreater(len(course_ids), 0)
        
        # Verify that courses are in the database
        conn, cursor = self.db_manager.connect()
        cursor.execute("SELECT COUNT(*) FROM courses")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreater(count, 0)
    
    def test_sync_assignments(self):
        """Test syncing assignments from Canvas."""
        # First sync courses to get course IDs
        course_ids = self.canvas_client.sync_courses()
        
        # Sync assignments
        assignment_count = self.canvas_client.sync_assignments(course_ids)
        
        # Verify that assignments were synced
        self.assertIsInstance(assignment_count, int)
        
        # Verify that assignments are in the database
        conn, cursor = self.db_manager.connect()
        cursor.execute("SELECT COUNT(*) FROM assignments")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreaterEqual(count, assignment_count)
    
    def test_extract_pdf_links(self):
        """Test extracting PDF links from content."""
        # Test with HTML content containing PDF links
        content = """
        <p>Here are some PDF links:</p>
        <ul>
            <li><a href="https://example.com/file.pdf">PDF File</a></li>
            <li><a href="https://canvas.instructure.com/files/12345/download">Canvas File</a></li>
        </ul>
        """
        
        pdf_links = self.canvas_client.extract_pdf_links(content)
        
        # Verify that PDF links were extracted
        self.assertIsInstance(pdf_links, list)
        self.assertGreaterEqual(len(pdf_links), 1)
        
        # Verify that at least one link contains .pdf
        pdf_found = any(".pdf" in link.lower() for link in pdf_links)
        self.assertTrue(pdf_found)


if __name__ == "__main__":
    unittest.main()
