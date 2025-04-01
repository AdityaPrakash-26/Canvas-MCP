"""
Tests for the MCP server implementation using SQLAlchemy.
"""
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import the MCP server functions and related components
from canvas_mcp.database import Base, SessionLocal, init_db
from canvas_mcp.models import (
    Announcement,
    Assignment,
    Course,
    Module,
    ModuleItem,
    Syllabus,
    UserCourse,
    orm_to_dict, # Import helper if used directly in tests
)
# Import server functions to test
from canvas_mcp.server import (
    get_course_announcements,
    get_course_assignments,
    get_course_list,
    get_course_modules,
    get_syllabus,
    get_upcoming_deadlines,
    opt_out_course,
    search_course_content,
    sync_canvas_data, # We might test this wrapper
)


class TestMCPServerSQLAlchemy(unittest.TestCase):
    """Test suite for MCP server functionality with SQLAlchemy."""

    @classmethod
    def setUpClass(cls):
        # Use in-memory SQLite database for testing
        cls.engine = create_engine("sqlite:///:memory:")
        # Create schema based on models
        init_db(cls.engine)
        # Create a session factory bound to the test engine
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        # Populate the database with test data once for the class
        cls._populate_test_data()

    @classmethod
    def tearDownClass(cls):
        # Dispose of the engine to close connections
        cls.engine.dispose()

    @classmethod
    def _populate_test_data(cls):
        """Create a test database with sample data using SQLAlchemy."""
        session = cls.TestingSessionLocal()
        try:
            # Courses
            course1 = Course(
                id=1, # Explicitly set IDs for predictable FKs
                canvas_course_id=12345,
                course_code="CS101",
                course_name="Introduction to Computer Science",
                instructor="Professor Smith",
                description="An introduction to computer science concepts",
                start_date=datetime(2025, 1, 15),
                end_date=datetime(2025, 5, 15)
            )
            course2 = Course(
                id=2,
                canvas_course_id=67890,
                course_code="MATH200",
                course_name="Calculus II",
                instructor="Professor Johnson",
                description="Advanced calculus topics",
                start_date=datetime(2025, 1, 15),
                end_date=datetime(2025, 5, 15)
            )
            session.add_all([course1, course2])
            session.flush() # Assign IDs

            # Syllabi
            syllabus1 = Syllabus(
                id=1, course_id=course1.id, content="<p>This is the CS101 syllabus</p>",
                parsed_content="This is the CS101 syllabus in plain text format.", is_parsed=True
            )
            syllabus2 = Syllabus(
                id=2, course_id=course2.id, content="<p>This is the MATH200 syllabus</p>"
                # No parsed content for this one initially
            )
            session.add_all([syllabus1, syllabus2])

            # Assignments
            now = datetime.now()
            assignment1 = Assignment(
                id=1, course_id=course1.id, canvas_assignment_id=101, title="Programming Assignment 1",
                description="Write a simple program in Python", assignment_type="assignment",
                due_date=now + timedelta(days=5), points_possible=100
            )
            assignment2 = Assignment(
                id=2, course_id=course1.id, canvas_assignment_id=102, title="Midterm Exam",
                description="Covers material from weeks 1-7", assignment_type="exam",
                due_date=now + timedelta(days=20), points_possible=200
            )
            assignment3 = Assignment(
                id=3, course_id=course2.id, canvas_assignment_id=201, title="Calculus Problem Set 1",
                description="Problems 1-20 from Chapter 3", assignment_type="assignment",
                due_date=now + timedelta(days=8), points_possible=50
            )
            # Assignment with past due date (should not appear in upcoming)
            assignment4 = Assignment(
                id=4, course_id=course1.id, canvas_assignment_id=100, title="Past Assignment 0",
                description="Already due", assignment_type="assignment",
                due_date=now - timedelta(days=2), points_possible=10
            )
            session.add_all([assignment1, assignment2, assignment3, assignment4])

            # Modules
            module1 = Module(
                id=1, course_id=course1.id, canvas_module_id=301, name="Week 1: Introduction",
                description="Intro concepts", position=1
            )
            module2 = Module(
                id=2, course_id=course1.id, canvas_module_id=302, name="Week 2: Variables",
                description="Data types", position=2
            )
            session.add_all([module1, module2])
            session.flush() # Assign IDs

            # Module Items
            item1 = ModuleItem(
                id=1, module_id=module1.id, canvas_item_id=1001, title="Intro Lecture Notes", item_type="File", position=1, content_details="Some details about the file."
            )
            item2 = ModuleItem(
                id=2, module_id=module1.id, canvas_item_id=1002, title="Setup Python Environment", item_type="Page", position=2, page_url="setup-python"
            )
            item3 = ModuleItem( # Link to an assignment
                id=3, module_id=module2.id, canvas_item_id=1003, title=assignment1.title, item_type="Assignment", position=1, content_id=assignment1.canvas_assignment_id
            )
            session.add_all([item1, item2, item3])

            # Announcements
            announce1 = Announcement(
                id=1, course_id=course1.id, canvas_announcement_id=2001, title="Welcome to CS101",
                content="Read the syllabus.", posted_by="Professor Smith", posted_at=datetime(2025, 1, 10, 9, 0)
            )
            announce2 = Announcement(
                 id=2, course_id=course1.id, canvas_announcement_id=2002, title="Office Hours Updated",
                 content="Thursdays 2-4pm.", posted_by="Professor Smith", posted_at=datetime(2025, 1, 15, 14, 30)
            )
            session.add_all([announce1, announce2])

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error populating test data: {e}")
            raise
        finally:
            session.close()


    def setUp(self):
        """Set up test environment before each test."""
        # Patch SessionLocal used by the server functions to return a session from our test pool
        self.session_patch = patch('canvas_mcp.server.SessionLocal', self.TestingSessionLocal)
        self.mock_session_local = self.session_patch.start()

        # Patch the canvas_client instance within the server module if testing sync_canvas_data
        self.client_patch = patch('canvas_mcp.server.canvas_client')
        self.mock_canvas_client = self.client_patch.start()


    def tearDown(self):
        """Clean up test environment after each test."""
        self.session_patch.stop()
        self.client_patch.stop()
        # # Optional: Clean up data between tests if needed, though setUpClass/tearDownClass handles DB creation/deletion
        # session = self.TestingSessionLocal()
        # session.query(UserCourse).delete() # Example cleanup
        # session.commit()
        # session.close()


    def test_get_upcoming_deadlines(self):
        """Test retrieving upcoming deadlines."""
        # Test default (7 days)
        deadlines_7 = get_upcoming_deadlines(days=7)
        self.assertEqual(len(deadlines_7), 1)
        self.assertEqual(deadlines_7[0]['assignment_title'], "Programming Assignment 1")
        self.assertEqual(deadlines_7[0]['course_code'], "CS101")
        self.assertIsNotNone(deadlines_7[0]['due_date']) # Check date exists

        # Test longer range (30 days)
        deadlines_30 = get_upcoming_deadlines(days=30)
        self.assertEqual(len(deadlines_30), 3) # PA1, Calc PS1, Midterm
         # Verify sorted by date
        self.assertEqual(deadlines_30[0]['assignment_title'], "Programming Assignment 1")
        self.assertEqual(deadlines_30[1]['assignment_title'], "Calculus Problem Set 1")
        self.assertEqual(deadlines_30[2]['assignment_title'], "Midterm Exam")

        # Test with course filter
        deadlines_cs101 = get_upcoming_deadlines(days=30, course_id=1)
        self.assertEqual(len(deadlines_cs101), 2)
        self.assertEqual(deadlines_cs101[0]['assignment_title'], "Programming Assignment 1")
        self.assertEqual(deadlines_cs101[1]['assignment_title'], "Midterm Exam")

        deadlines_math200 = get_upcoming_deadlines(days=30, course_id=2)
        self.assertEqual(len(deadlines_math200), 1)
        self.assertEqual(deadlines_math200[0]['assignment_title'], "Calculus Problem Set 1")


    def test_get_course_list(self):
        """Test retrieving the list of courses."""
        courses = get_course_list()
        self.assertEqual(len(courses), 2)
        # Courses should be sorted by start_date desc, but they are same here, check codes
        course_codes = {c['course_code'] for c in courses}
        self.assertIn("CS101", course_codes)
        self.assertIn("MATH200", course_codes)
        self.assertIn("id", courses[0])
        self.assertIn("canvas_course_id", courses[0])


    def test_get_course_assignments(self):
        """Test retrieving assignments for a specific course."""
        assignments_cs101 = get_course_assignments(course_id=1)
        self.assertEqual(len(assignments_cs101), 3) # PA1, Midterm, Past Assign
        # Should be sorted by due_date asc (None might appear first or last depending on DB)
        titles_cs101 = [a['title'] for a in assignments_cs101]
        # Order depends on NULL sorting, but check presence
        self.assertIn("Past Assignment 0", titles_cs101)
        self.assertIn("Programming Assignment 1", titles_cs101)
        self.assertIn("Midterm Exam", titles_cs101)

        assignments_math200 = get_course_assignments(course_id=2)
        self.assertEqual(len(assignments_math200), 1)
        self.assertEqual(assignments_math200[0]['title'], "Calculus Problem Set 1")


    def test_get_course_modules(self):
        """Test retrieving modules for a specific course."""
        # Test without items
        modules_no_items = get_course_modules(course_id=1)
        self.assertEqual(len(modules_no_items), 2)
        self.assertEqual(modules_no_items[0]['name'], "Week 1: Introduction")
        self.assertEqual(modules_no_items[1]['name'], "Week 2: Variables")
        self.assertNotIn("items", modules_no_items[0])

        # Test with items
        modules_with_items = get_course_modules(course_id=1, include_items=True)
        self.assertEqual(len(modules_with_items), 2)
        # Check module 1 items (sorted by position)
        self.assertEqual(len(modules_with_items[0]['items']), 2)
        self.assertEqual(modules_with_items[0]['items'][0]['title'], "Intro Lecture Notes")
        self.assertEqual(modules_with_items[0]['items'][1]['title'], "Setup Python Environment")
        # Check module 2 items (sorted by position)
        self.assertEqual(len(modules_with_items[1]['items']), 1)
        self.assertEqual(modules_with_items[1]['items'][0]['title'], "Programming Assignment 1")

        # Test for course with no modules
        modules_math200 = get_course_modules(course_id=2)
        self.assertEqual(len(modules_math200), 0)


    def test_get_syllabus(self):
        """Test retrieving syllabus content."""
        # Test raw format (should return HTML)
        syllabus_raw = get_syllabus(course_id=1, format="raw")
        self.assertEqual(syllabus_raw['course_code'], "CS101")
        self.assertEqual(syllabus_raw['content'], "<p>This is the CS101 syllabus</p>")

        # Test parsed format (should return plain text)
        syllabus_parsed = get_syllabus(course_id=1, format="parsed")
        self.assertEqual(syllabus_parsed['course_code'], "CS101")
        self.assertEqual(syllabus_parsed['content'], "This is the CS101 syllabus in plain text format.")

        # Test course with syllabus but no parsed content (should return raw)
        syllabus_math_raw = get_syllabus(course_id=2, format="raw")
        self.assertEqual(syllabus_math_raw['content'], "<p>This is the MATH200 syllabus</p>")
        syllabus_math_parsed = get_syllabus(course_id=2, format="parsed") # Request parsed
        self.assertEqual(syllabus_math_parsed['content'], "<p>This is the MATH200 syllabus</p>") # Falls back to raw

        # Test non-existent course
        syllabus_none = get_syllabus(course_id=999)
        self.assertIn("error", syllabus_none)
        self.assertIn("not found", syllabus_none["error"])


    def test_get_course_announcements(self):
        """Test retrieving course announcements."""
        announcements_cs101 = get_course_announcements(course_id=1)
        self.assertEqual(len(announcements_cs101), 2)
        # Sorted by posted_at DESC
        self.assertEqual(announcements_cs101[0]['title'], "Office Hours Updated")
        self.assertEqual(announcements_cs101[1]['title'], "Welcome to CS101")

        # Test limit
        announcements_limit_1 = get_course_announcements(course_id=1, limit=1)
        self.assertEqual(len(announcements_limit_1), 1)
        self.assertEqual(announcements_limit_1[0]['title'], "Office Hours Updated")

        # Test course with no announcements
        announcements_math200 = get_course_announcements(course_id=2)
        self.assertEqual(len(announcements_math200), 0)


    def test_search_course_content(self):
        """Test searching across course content."""
        # Search for "Python" (should be in assignment 1 description)
        results_python = search_course_content("Python")
        self.assertEqual(len(results_python), 2) # Assignment description + Module Item title
        result_types = {r['content_type'] for r in results_python}
        self.assertIn('assignment', result_types)
        self.assertIn('module_item', result_types)


        # Search for "calculus" (should be in course 2 description)
        results_calculus = search_course_content("calculus")
        # Note: search currently checks limited fields. Add course description if needed.
        # Current implementation searches Assignments, Modules, ModuleItems, Syllabi.
        # Let's search for 'Problem Set' from assignment 3 title
        results_problem_set = search_course_content("Problem Set")
        self.assertEqual(len(results_problem_set), 1)
        self.assertEqual(results_problem_set[0]['content_type'], 'assignment')
        self.assertEqual(results_problem_set[0]['title'], 'Calculus Problem Set 1')


        # Search for "syllabus" (should match syllabus content)
        results_syllabus = search_course_content("syllabus")
        self.assertEqual(len(results_syllabus), 2) # Matches content in both syllabi
        self.assertEqual(results_syllabus[0]['content_type'], 'syllabus')

        # Search within a specific course
        results_python_cs101 = search_course_content("Python", course_id=1)
        self.assertEqual(len(results_python_cs101), 2)

        results_calculus_cs101 = search_course_content("Calculus", course_id=1)
        self.assertEqual(len(results_calculus_cs101), 0)

        # Search for non-existent term
        results_none = search_course_content("nonexistentxyz")
        self.assertEqual(len(results_none), 0)


    def test_opt_out_course(self):
        """Test opting a course in/out for a user."""
        user = "test_user1"
        course_id = 1

        # Opt out
        result_out = opt_out_course(course_id=course_id, user_id=user, opt_out=True)
        self.assertTrue(result_out["success"])
        self.assertTrue(result_out["opted_out"])

        # Verify in DB
        session = self.TestingSessionLocal()
        pref = session.query(UserCourse).filter_by(user_id=user, course_id=course_id).one()
        self.assertTrue(pref.indexing_opt_out)
        session.close()

        # Opt back in
        result_in = opt_out_course(course_id=course_id, user_id=user, opt_out=False)
        self.assertTrue(result_in["success"])
        self.assertFalse(result_in["opted_out"])

        # Verify in DB
        session = self.TestingSessionLocal()
        pref = session.query(UserCourse).filter_by(user_id=user, course_id=course_id).one()
        self.assertFalse(pref.indexing_opt_out)
        session.close()

        # Test non-existent course
        result_bad_course = opt_out_course(course_id=999, user_id=user, opt_out=True)
        self.assertFalse(result_bad_course["success"])
        self.assertIn("not found", result_bad_course["message"])


    def test_sync_canvas_data_tool(self):
        """Test the sync_canvas_data MCP tool wrapper."""
        # Mock the underlying client method
        expected_sync_result = {"courses": 1, "assignments": 5, "modules": 3, "announcements": 2}
        self.mock_canvas_client.sync_all.return_value = expected_sync_result

        # Call the tool function
        result = sync_canvas_data(term_id=-1) # Pass args

        # Verify the client method was called
        self.mock_canvas_client.sync_all.assert_called_once_with(term_id=-1)
        # Verify the result is passed through
        self.assertEqual(result, expected_sync_result)

    def test_sync_canvas_data_tool_no_client(self):
        """Test sync tool when canvas client is not initialized."""
        self.mock_canvas_client.canvas = None # Simulate uninitialized client

        result = sync_canvas_data()

        self.assertEqual(result, {"error": "Canvas API client not initialized. Cannot sync."})
        self.mock_canvas_client.sync_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()