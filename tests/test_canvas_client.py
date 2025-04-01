"""
Tests for Canvas API client and database integration using SQLAlchemy.
"""
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import necessary components from the refactored code
from canvas_mcp.canvas_client import CanvasClient, parse_canvas_datetime
from canvas_mcp.database import Base, init_db
from canvas_mcp.models import (
    Announcement,
    Assignment,
    CalendarEvent,
    Course,
    Module,
    ModuleItem,
    Syllabus,
    UserCourse,
)

# Mock canvasapi classes before they are potentially imported by CanvasClient
# This prevents errors if canvasapi is not installed during testing
mock_canvas_api = MagicMock()
sys_modules_patch = patch.dict('sys.modules', {'canvasapi': mock_canvas_api})
sys_modules_patch.start()

# Now create mock classes based on MagicMock
MockCanvas = MagicMock()
mock_canvas_api.Canvas = MockCanvas

MockCanvasCourse = MagicMock()
mock_canvas_api.course.Course = MockCanvasCourse

MockCanvasUser = MagicMock()
mock_canvas_api.user.User = MockCanvasUser

MockCanvasAssignment = MagicMock()
mock_canvas_api.assignment.Assignment = MockCanvasAssignment

MockCanvasModule = MagicMock()
mock_canvas_api.module.Module = MockCanvasModule

MockCanvasModuleItem = MagicMock()
mock_canvas_api.module.ModuleItem = MockCanvasModuleItem

MockCanvasDiscussionTopic = MagicMock() # For announcements
mock_canvas_api.discussion_topic.DiscussionTopic = MockCanvasDiscussionTopic

MockPaginatedList = MagicMock()
mock_canvas_api.paginated_list.PaginatedList = MockPaginatedList
MockPaginatedList.side_effect = lambda x: list(x) # Simple mock: behave like list()

MockResourceDoesNotExist = type('ResourceDoesNotExist', (Exception,), {})
mock_canvas_api.exceptions.ResourceDoesNotExist = MockResourceDoesNotExist


class TestCanvasClientSQLAlchemy(unittest.TestCase):
    """Test suite for the Canvas client functionality with SQLAlchemy."""

    @classmethod
    def setUpClass(cls):
        """Patch sys.modules once for the class."""
        # Ensure the patch is active if it wasn't started earlier
        if not sys_modules_patch.is_started:
             sys_modules_patch.start()

    @classmethod
    def tearDownClass(cls):
        """Stop the sys.modules patch."""
        sys_modules_patch.stop()

    def setUp(self):
        """Set up test environment before each test."""
        # Use in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        # Create schema based on models
        init_db(self.engine)
        # Create a session factory bound to the test engine
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Mock the Canvas class from canvasapi *within* canvas_client module specifically
        # This ensures our client uses the mock, not a potentially real one
        self.canvas_patch = patch('canvas_mcp.canvas_client.Canvas', new=MockCanvas)
        self.mock_canvas_class = self.canvas_patch.start()
        # Reset the mock before each test
        self.mock_canvas = self.mock_canvas_class.return_value
        self.mock_canvas.reset_mock() # Clear previous calls/instances

        # Initialize the client with the testing session factory and mock API details
        self.api_key = "test_api_key"
        self.api_url = "https://test.instructure.com"
        # Pass the testing session factory
        self.client = CanvasClient(db_session_factory=self.TestingSessionLocal, api_key=self.api_key, api_url=self.api_url)
        # Ensure the client's internal canvas instance is our mock
        self.client.canvas = self.mock_canvas

        # Verify mock setup
        self.assertIsNotNone(self.client.canvas, "Client canvas should be mocked")


    def tearDown(self):
        """Clean up test environment after each test."""
        self.canvas_patch.stop()
        # Dispose of the engine to close connections
        self.engine.dispose()

    def _get_test_session(self):
        """Helper to get a session for test assertions."""
        return self.TestingSessionLocal()

    def test_parse_canvas_datetime(self):
        """Test the datetime parsing helper."""
        self.assertIsNone(parse_canvas_datetime(None))
        self.assertIsNone(parse_canvas_datetime(""))
        self.assertIsNone(parse_canvas_datetime("invalid date"))
        dt_zulu = parse_canvas_datetime("2025-02-15T23:59:00Z")
        self.assertEqual(dt_zulu, datetime(2025, 2, 15, 23, 59, 0))
        dt_offset = parse_canvas_datetime("2025-02-15T18:59:00-05:00")
        # Note: fromisoformat preserves offset, test against expected UTC or naive representation if needed
        self.assertEqual(dt_offset.hour, 18)
        self.assertEqual(dt_offset.minute, 59)


    def test_sync_courses(self):
        """Test syncing courses from Canvas to the database."""
        # Mock user and courses
        mock_user = MagicMock(spec=CanvasUser) # Use spec for better mocking
        mock_user.id = 999
        self.mock_canvas.get_current_user.return_value = mock_user

        mock_course1_api = MagicMock(spec=CanvasCourse)
        mock_course1_api.id = 12345
        mock_course1_api.name = "Test Course 1"
        mock_course1_api.course_code = "TST101"
        mock_course1_api.enrollment_term_id = 1
        mock_course1_api.start_at = "2025-01-10T00:00:00Z"
        mock_course1_api.end_at = "2025-05-10T00:00:00Z"

        mock_course2_api = MagicMock(spec=CanvasCourse)
        mock_course2_api.id = 67890
        mock_course2_api.name = "Test Course 2"
        mock_course2_api.course_code = "TST102"
        mock_course2_api.enrollment_term_id = 1
        mock_course2_api.start_at = "2025-01-15T00:00:00Z"
        mock_course2_api.end_at = "2025-05-15T00:00:00Z"

        # Mock the user's get_courses method
        mock_user.get_courses.return_value = [mock_course1_api, mock_course2_api]

        # Mock detailed course info (get_course call)
        mock_teacher1 = MagicMock()
        mock_teacher1.name = "Prof One"
        mock_detailed_course1 = MagicMock(spec=CanvasCourse)
        mock_detailed_course1.id = 12345 # Ensure ID matches
        mock_detailed_course1.teachers = [mock_teacher1]
        mock_detailed_course1.public_description = "Course 1 description"
        mock_detailed_course1.syllabus_body = "<p>Syllabus 1</p>"
        mock_detailed_course1.start_at = mock_course1_api.start_at
        mock_detailed_course1.end_at = mock_course1_api.end_at

        mock_teacher2 = MagicMock()
        mock_teacher2.name = "Prof Two"
        mock_detailed_course2 = MagicMock(spec=CanvasCourse)
        mock_detailed_course2.id = 67890 # Ensure ID matches
        mock_detailed_course2.teachers = [mock_teacher2]
        mock_detailed_course2.public_description = "Course 2 description"
        mock_detailed_course2.syllabus_body = "<p>Syllabus 2</p>"
        mock_detailed_course2.start_at = mock_course2_api.start_at
        mock_detailed_course2.end_at = mock_course2_api.end_at

        # Configure get_course mock to return detailed info based on ID
        def get_course_side_effect(course_id, **kwargs):
            if course_id == 12345:
                return mock_detailed_course1
            elif course_id == 67890:
                return mock_detailed_course2
            else:
                raise MockResourceDoesNotExist(f"Course {course_id} not found")
        self.mock_canvas.get_course.side_effect = get_course_side_effect

        # Run the sync
        synced_ids = self.client.sync_courses()

        # Verify API calls
        self.mock_canvas.get_current_user.assert_called_once()
        mock_user.get_courses.assert_called_once_with(include=["term", "teachers"])
        self.assertEqual(self.mock_canvas.get_course.call_count, 2)
        # Check that include flags were passed to get_course
        self.mock_canvas.get_course.assert_any_call(12345, include=["syllabus_body", "teachers"])
        self.mock_canvas.get_course.assert_any_call(67890, include=["syllabus_body", "teachers"])


        # Verify database state
        session = self._get_test_session()
        courses = session.query(Course).order_by(Course.canvas_course_id).all()
        syllabi = session.query(Syllabus).join(Course).order_by(Course.canvas_course_id).all()
        session.close()

        self.assertEqual(len(synced_ids), 2)
        self.assertEqual(len(courses), 2)
        self.assertEqual(len(syllabi), 2)

        # Check Course 1 data
        self.assertEqual(courses[0].canvas_course_id, 12345)
        self.assertEqual(courses[0].course_code, "TST101")
        self.assertEqual(courses[0].instructor, "Prof One")
        self.assertEqual(courses[0].description, "Course 1 description")
        self.assertEqual(courses[0].start_date, datetime(2025, 1, 10))
        self.assertEqual(syllabi[0].content, "<p>Syllabus 1</p>")
        self.assertEqual(syllabi[0].course_id, courses[0].id)
        self.assertIn(courses[0].id, synced_ids)

        # Check Course 2 data
        self.assertEqual(courses[1].canvas_course_id, 67890)
        self.assertEqual(courses[1].course_code, "TST102")
        self.assertEqual(courses[1].instructor, "Prof Two")
        self.assertEqual(courses[1].description, "Course 2 description")
        self.assertEqual(courses[1].start_date, datetime(2025, 1, 15))
        self.assertEqual(syllabi[1].content, "<p>Syllabus 2</p>")
        self.assertEqual(syllabi[1].course_id, courses[1].id)
        self.assertIn(courses[1].id, synced_ids)


    def test_sync_courses_with_term_filter(self):
        """Test syncing courses with term filtering."""
        mock_user = MagicMock(spec=CanvasUser)
        mock_user.id = 999
        self.mock_canvas.get_current_user.return_value = mock_user

        mock_course1 = MagicMock(spec=CanvasCourse, id=1, name="Term 1 Course", enrollment_term_id=10)
        mock_course2 = MagicMock(spec=CanvasCourse, id=2, name="Term 2 Course", enrollment_term_id=20)
        mock_course3 = MagicMock(spec=CanvasCourse, id=3, name="Term 3 Course", enrollment_term_id=30) # Latest

        mock_user.get_courses.return_value = [mock_course1, mock_course2, mock_course3]

        # Mock get_course to return minimal info, focusing on filtering logic
        def get_course_side_effect(course_id, **kwargs):
            if course_id == 1: return MagicMock(spec=CanvasCourse, id=1, name="Term 1 Course", teachers=[], syllabus_body="")
            if course_id == 2: return MagicMock(spec=CanvasCourse, id=2, name="Term 2 Course", teachers=[], syllabus_body="")
            if course_id == 3: return MagicMock(spec=CanvasCourse, id=3, name="Term 3 Course", teachers=[], syllabus_body="")
            raise MockResourceDoesNotExist()
        self.mock_canvas.get_course.side_effect = get_course_side_effect

        # Test case 1: Filter for specific term (term_id=20)
        synced_ids_term20 = self.client.sync_courses(term_id=20)

        session = self._get_test_session()
        courses_term20 = session.query(Course).all()
        session.close()
        self.assertEqual(len(synced_ids_term20), 1)
        self.assertEqual(len(courses_term20), 1)
        self.assertEqual(courses_term20[0].canvas_course_id, 2) # Course with term_id 20

        # Clear DB for next test
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.mock_canvas.get_course.reset_mock() # Reset call count

        # Test case 2: Filter for latest term (term_id=-1)
        synced_ids_latest = self.client.sync_courses(term_id=-1)

        session = self._get_test_session()
        courses_latest = session.query(Course).all()
        session.close()
        self.assertEqual(len(synced_ids_latest), 1)
        self.assertEqual(len(courses_latest), 1)
        self.assertEqual(courses_latest[0].canvas_course_id, 3) # Course with max term_id 30


    def test_sync_assignments(self):
        """Test syncing assignments from Canvas to the database."""
        # Setup: Create a course in the DB first
        session = self._get_test_session()
        local_course = Course(canvas_course_id=123, course_code="PRE101", course_name="Prereq Course")
        session.add(local_course)
        session.commit()
        local_course_id = local_course.id
        session.close()

        # Mock Canvas API course and assignments
        mock_canvas_course = MagicMock(spec=CanvasCourse)
        self.mock_canvas.get_course.return_value = mock_canvas_course

        mock_assignment1_api = MagicMock(spec=CanvasAssignment)
        mock_assignment1_api.id = 9876
        mock_assignment1_api.name = "Assignment 1"
        mock_assignment1_api.description = "Desc 1"
        mock_assignment1_api.due_at = "2025-02-15T23:59:00Z"
        mock_assignment1_api.unlock_at = "2025-02-01T00:00:00Z"
        mock_assignment1_api.lock_at = "2025-02-16T23:59:00Z"
        mock_assignment1_api.points_possible = 100.0
        mock_assignment1_api.submission_types = ["online_text_entry", "online_upload"]

        mock_assignment2_api = MagicMock(spec=CanvasAssignment)
        mock_assignment2_api.id = 5432
        mock_assignment2_api.name = "Quiz 1"
        mock_assignment2_api.description = "Desc 2"
        mock_assignment2_api.due_at = "2025-03-01T23:59:00Z"
        mock_assignment2_api.unlock_at = None # Test None date
        mock_assignment2_api.lock_at = None
        mock_assignment2_api.points_possible = 50.5
        mock_assignment2_api.submission_types = ["online_quiz"]

        # Use MockPaginatedList for get_assignments
        mock_canvas_course.get_assignments.return_value = MockPaginatedList([mock_assignment1_api, mock_assignment2_api])

        # Run the sync for the specific course
        assignment_count = self.client.sync_assignments([local_course_id])

        # Verify API calls
        self.mock_canvas.get_course.assert_called_once_with(123)
        mock_canvas_course.get_assignments.assert_called_once()

        # Verify database state
        session = self._get_test_session()
        assignments = session.query(Assignment).filter_by(course_id=local_course_id).order_by(Assignment.canvas_assignment_id).all()
        calendar_events = session.query(CalendarEvent).filter_by(course_id=local_course_id).order_by(CalendarEvent.event_date).all()
        session.close()

        self.assertEqual(assignment_count, 2)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(len(calendar_events), 2) # One for each due date

        # Check Assignment 1 data
        self.assertEqual(assignments[1].canvas_assignment_id, 9876) # Order by canvas_id
        self.assertEqual(assignments[1].title, "Assignment 1")
        self.assertEqual(assignments[1].assignment_type, "assignment")
        self.assertEqual(assignments[1].due_date, datetime(2025, 2, 15, 23, 59))
        self.assertEqual(assignments[1].points_possible, 100.0)
        self.assertEqual(assignments[1].submission_types, "online_text_entry,online_upload")

        # Check Assignment 2 data
        self.assertEqual(assignments[0].canvas_assignment_id, 5432) # Order by canvas_id
        self.assertEqual(assignments[0].title, "Quiz 1")
        self.assertEqual(assignments[0].assignment_type, "quiz")
        self.assertEqual(assignments[0].due_date, datetime(2025, 3, 1, 23, 59))
        self.assertEqual(assignments[0].points_possible, 50.5)
        self.assertIsNone(assignments[0].available_from) # Check None date

        # Check Calendar Events
        self.assertEqual(calendar_events[0].source_type, "assignment")
        self.assertEqual(calendar_events[0].source_id, assignments[1].id) # Event for assignment 1
        self.assertEqual(calendar_events[0].event_date, assignments[1].due_date)
        self.assertEqual(calendar_events[1].source_type, "assignment")
        self.assertEqual(calendar_events[1].source_id, assignments[0].id) # Event for assignment 2
        self.assertEqual(calendar_events[1].event_date, assignments[0].due_date)


    def test_sync_modules(self):
        """Test syncing modules and items from Canvas to the database."""
        # Setup: Create a course in the DB first
        session = self._get_test_session()
        local_course = Course(canvas_course_id=123, course_code="PRE101", course_name="Prereq Course")
        session.add(local_course)
        session.commit()
        local_course_id = local_course.id
        session.close()

        # Mock Canvas API course and modules
        mock_canvas_course = MagicMock(spec=CanvasCourse)
        self.mock_canvas.get_course.return_value = mock_canvas_course

        mock_module1_api = MagicMock(spec=CanvasModule)
        mock_module1_api.id = 111
        mock_module1_api.name = "Module 1"
        mock_module1_api.position = 1
        mock_module1_api.unlock_at = "2025-01-20T00:00:00Z"
        mock_module1_api.require_sequential_progress = False

        mock_module2_api = MagicMock(spec=CanvasModule)
        mock_module2_api.id = 222
        mock_module2_api.name = "Module 2"
        mock_module2_api.position = 2
        mock_module2_api.unlock_at = None
        mock_module2_api.require_sequential_progress = True

        mock_canvas_course.get_modules.return_value = MockPaginatedList([mock_module1_api, mock_module2_api])

        # Mock Module Items
        mock_item1_api = MagicMock(spec=CanvasModuleItem)
        mock_item1_api.id = 101
        mock_item1_api.title = "Item 1 Page"
        mock_item1_api.type = "Page"
        mock_item1_api.position = 1
        mock_item1_api.content_id = 501
        mock_item1_api.page_url = "item-1-page"
        mock_item1_api.external_url = None

        mock_item2_api = MagicMock(spec=CanvasModuleItem)
        mock_item2_api.id = 102
        mock_item2_api.title = "Item 2 Assignment"
        mock_item2_api.type = "Assignment"
        mock_item2_api.position = 2
        mock_item2_api.content_id = 9876 # Matches assignment ID from previous test if needed
        mock_item2_api.page_url = None
        mock_item2_api.external_url = None

        # Mock get_module_items for each module
        mock_module1_api.get_module_items.return_value = MockPaginatedList([mock_item1_api, mock_item2_api])
        mock_module2_api.get_module_items.return_value = MockPaginatedList([]) # Module 2 has no items

        # Run the sync
        module_count = self.client.sync_modules([local_course_id])

        # Verify API calls
        self.mock_canvas.get_course.assert_called_once_with(123)
        mock_canvas_course.get_modules.assert_called_once_with(include=["module_items"])
        mock_module1_api.get_module_items.assert_called_once()
        mock_module2_api.get_module_items.assert_called_once()


        # Verify database state
        session = self._get_test_session()
        modules = session.query(Module).filter_by(course_id=local_course_id).order_by(Module.position).all()
        # Eager load items for verification
        items = session.query(ModuleItem).join(Module).filter(Module.course_id==local_course_id).order_by(Module.position, ModuleItem.position).all()
        session.close()

        self.assertEqual(module_count, 2)
        self.assertEqual(len(modules), 2)
        self.assertEqual(len(items), 2) # Only module 1 has items

        # Check Module 1 data
        self.assertEqual(modules[0].canvas_module_id, 111)
        self.assertEqual(modules[0].name, "Module 1")
        self.assertEqual(modules[0].unlock_date, datetime(2025, 1, 20))
        self.assertFalse(modules[0].require_sequential_progress)

        # Check Module 2 data
        self.assertEqual(modules[1].canvas_module_id, 222)
        self.assertEqual(modules[1].name, "Module 2")
        self.assertIsNone(modules[1].unlock_date)
        self.assertTrue(modules[1].require_sequential_progress)

        # Check Module 1 Items
        self.assertEqual(items[0].canvas_item_id, 101)
        self.assertEqual(items[0].title, "Item 1 Page")
        self.assertEqual(items[0].item_type, "Page")
        self.assertEqual(items[0].module_id, modules[0].id)
        self.assertEqual(items[0].page_url, "item-1-page")

        self.assertEqual(items[1].canvas_item_id, 102)
        self.assertEqual(items[1].title, "Item 2 Assignment")
        self.assertEqual(items[1].item_type, "Assignment")
        self.assertEqual(items[1].content_id, 9876)
        self.assertEqual(items[1].module_id, modules[0].id)


    def test_sync_announcements(self):
        """Test syncing announcements from Canvas to the database."""
        # Setup: Create a course
        session = self._get_test_session()
        local_course = Course(canvas_course_id=123, course_code="PRE101", course_name="Prereq Course")
        session.add(local_course)
        session.commit()
        local_course_id = local_course.id
        session.close()

        # Mock Canvas API announcements (retrieved via get_announcements)
        mock_announcement1_api = MagicMock(spec=CanvasDiscussionTopic)
        mock_announcement1_api.id = 333
        mock_announcement1_api.title = "Announce 1"
        mock_announcement1_api.message = "<p>Message 1</p>"
        mock_announcement1_api.posted_at = "2025-01-15T10:00:00Z"
        mock_announcement1_api.author = {"display_name": "Prof Smith"}
        mock_announcement1_api.announcement = True # Mark as announcement

        mock_announcement2_api = MagicMock(spec=CanvasDiscussionTopic)
        mock_announcement2_api.id = 444
        mock_announcement2_api.title = "Announce 2"
        mock_announcement2_api.message = "<p>Message 2</p>"
        mock_announcement2_api.posted_at = "2025-01-20T14:30:00Z"
        mock_announcement2_api.author = {"display_name": "TA Jane"}
        mock_announcement2_api.announcement = True

        context_code = f"course_{local_course.canvas_course_id}"
        self.mock_canvas.get_announcements.return_value = MockPaginatedList([mock_announcement1_api, mock_announcement2_api])

        # Run the sync
        announcement_count = self.client.sync_announcements([local_course_id])

        # Verify API calls
        self.mock_canvas.get_announcements.assert_called_once_with(context_codes=[context_code])

        # Verify database state
        session = self._get_test_session()
        announcements = session.query(Announcement).filter_by(course_id=local_course_id).order_by(Announcement.canvas_announcement_id).all()
        session.close()

        self.assertEqual(announcement_count, 2)
        self.assertEqual(len(announcements), 2)

        # Check Announcement 1
        self.assertEqual(announcements[0].canvas_announcement_id, 333)
        self.assertEqual(announcements[0].title, "Announce 1")
        self.assertEqual(announcements[0].content, "<p>Message 1</p>")
        self.assertEqual(announcements[0].posted_by, "Prof Smith")
        self.assertEqual(announcements[0].posted_at, datetime(2025, 1, 15, 10, 0))

        # Check Announcement 2
        self.assertEqual(announcements[1].canvas_announcement_id, 444)
        self.assertEqual(announcements[1].title, "Announce 2")
        self.assertEqual(announcements[1].content, "<p>Message 2</p>")
        self.assertEqual(announcements[1].posted_by, "TA Jane")
        self.assertEqual(announcements[1].posted_at, datetime(2025, 1, 20, 14, 30))


    def test_sync_all(self):
        """Test syncing all data using sync_all method."""
        # Mock sync methods to verify they are called with correct IDs
        with patch.object(self.client, 'sync_courses', return_value=[1, 2]) as mock_sync_courses, \
             patch.object(self.client, 'sync_assignments', return_value=5) as mock_sync_assignments, \
             patch.object(self.client, 'sync_modules', return_value=10) as mock_sync_modules, \
             patch.object(self.client, 'sync_announcements', return_value=3) as mock_sync_announcements:

            # Run sync_all with specific term
            result = self.client.sync_all(user_id_str="user123", term_id=99)

            # Verify sync_courses was called correctly
            mock_sync_courses.assert_called_once_with(user_id_str="user123", term_id=99)

            # Verify subsequent sync methods were called with the IDs from sync_courses
            mock_sync_assignments.assert_called_once_with([1, 2])
            mock_sync_modules.assert_called_once_with([1, 2])
            mock_sync_announcements.assert_called_once_with([1, 2])

            # Verify the result dictionary
            expected_result = {
                "courses": 2,
                "assignments": 5,
                "modules": 10,
                "announcements": 3
            }
            self.assertEqual(result, expected_result)

    def test_sync_all_no_courses_synced(self):
        """Test sync_all when sync_courses returns no IDs."""
        with patch.object(self.client, 'sync_courses', return_value=[]) as mock_sync_courses, \
             patch.object(self.client, 'sync_assignments') as mock_sync_assignments, \
             patch.object(self.client, 'sync_modules') as mock_sync_modules, \
             patch.object(self.client, 'sync_announcements') as mock_sync_announcements:

            result = self.client.sync_all(term_id=-1)

            mock_sync_courses.assert_called_once_with(user_id_str=None, term_id=-1)
            # Ensure other syncs were NOT called
            mock_sync_assignments.assert_not_called()
            mock_sync_modules.assert_not_called()
            mock_sync_announcements.assert_not_called()

            expected_result = {"courses": 0, "assignments": 0, "modules": 0, "announcements": 0}
            self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()