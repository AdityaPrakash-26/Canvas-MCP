"""
Canvas API client for synchronizing data with the local database using SQLAlchemy.
"""
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Add project root to sys.path to allow importing database and models
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Make Canvas available for patching in tests
try:
    from canvasapi import Canvas
    from canvasapi.assignment import Assignment as CanvasAssignment
    from canvasapi.course import Course as CanvasCourse
    from canvasapi.discussion_topic import DiscussionTopic as CanvasDiscussionTopic
    from canvasapi.exceptions import ResourceDoesNotExist
    from canvasapi.module import Module as CanvasModule
    from canvasapi.module import ModuleItem as CanvasModuleItem
    from canvasapi.paginated_list import PaginatedList
    from canvasapi.user import User as CanvasUser
except ImportError:
    # Create dummy classes for tests to patch
    print("Warning: 'canvasapi' not installed. Canvas sync functionality will be disabled.")
    Canvas = None
    CanvasAssignment = object
    CanvasCourse = object
    CanvasDiscussionTopic = object
    CanvasModule = object
    CanvasModuleItem = object
    PaginatedList = list
    ResourceDoesNotExist = Exception
    CanvasUser = object


# Local imports after path adjustment
try:
    from canvas_mcp.database import SessionLocal
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
except ImportError as e:
    print(f"Error importing local modules: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path}")
    raise


def parse_canvas_datetime(date_str: str | None) -> datetime | None:
    """Safely parse ISO 8601 datetime strings from Canvas API."""
    if not date_str:
        return None
    try:
        # Handle potential 'Z' for UTC timezone
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


class CanvasClient:
    """
    Client for interacting with the Canvas LMS API and syncing data to the local database.
    """

    def __init__(
        self,
        db_session_factory: type[SessionLocal] = SessionLocal,
        api_key: str | None = None,
        api_url: str | None = None,
    ):
        """
        Initialize the Canvas client.

        Args:
            db_session_factory: SQLAlchemy session factory (default: SessionLocal).
            api_key: Canvas API key (if None, will look for CANVAS_API_KEY in environment).
            api_url: Canvas API URL (if None, will use CANVAS_API_URL or default Canvas URL).
        """
        # Load environment variables if needed
        load_dotenv()
        self.api_key = api_key or os.environ.get("CANVAS_API_KEY")
        self.api_url = api_url or os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
        
        # Store as session factory function, not a string
        if isinstance(db_session_factory, str):
            print(f"Warning: db_session_factory is a string: {db_session_factory}")
            self.db_session_factory = SessionLocal
        else:
            self.db_session_factory = db_session_factory
            
        # For storing current user
        self.user = None

        # Initialize canvasapi if available and configured
        self.canvas: Canvas | None = None
        if Canvas is not None and self.api_key and self.api_url:
            try:
                self.canvas = Canvas(self.api_url, self.api_key)
                # Test connection by getting current user
                self.canvas.get_current_user()
                print(f"Successfully connected to Canvas API at {self.api_url}")
            except Exception as e:
                print(f"Warning: Failed to connect to Canvas API at {self.api_url}. Error: {e}")
                self.canvas = None
        elif Canvas is None:
            print("Warning: canvasapi module not installed. Sync disabled.")
        else:
            print("Warning: Canvas API Key or URL not configured. Sync disabled.")


    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.db_session_factory()

    def sync_courses(self, user_id_str: str | None = None, term_id: int | None = None) -> list[int]:
        """
        Synchronize course data from Canvas to the local database.

        Args:
            user_id_str: User ID string (obtained from Canvas). If None, uses the current authenticated user.
            term_id: Optional term ID to filter courses (-1 for latest).

        Returns:
            List of local course IDs that were synced or updated.
        """
        if not self.canvas:
            print("Canvas API client not initialized. Skipping course sync.")
            return []

        synced_course_ids = []
        session = self._get_session()
        try:
            # Get current user for authentication context
            current_user: CanvasUser = self.canvas.get_current_user()
            user_id_str = user_id_str or str(current_user.id)
            print(f"Starting course sync for user ID: {user_id_str}")

            # Get courses for the user
            canvas_courses: list[CanvasCourse] = list(current_user.get_courses(include=["term", "teachers"]))
            print(f"Found {len(canvas_courses)} potential courses in Canvas.")

            # Filter by term if requested
            if term_id is not None:
                if term_id == -1:
                    term_ids = [getattr(c, 'enrollment_term_id', 0) for c in canvas_courses]
                    if term_ids:
                        max_term_id = max(filter(lambda x: x is not None, term_ids), default=None)
                        if max_term_id is not None:
                            print(f"Filtering courses for the latest term (ID: {max_term_id})")
                            canvas_courses = [c for c in canvas_courses if getattr(c, 'enrollment_term_id', None) == max_term_id]
                else:
                    print(f"Filtering courses for specific term (ID: {term_id})")
                    canvas_courses = [c for c in canvas_courses if getattr(c, 'enrollment_term_id', None) == term_id]
            print(f"Processing {len(canvas_courses)} courses after filtering.")


            for canvas_course in canvas_courses:
                canvas_course_id = canvas_course.id
                print(f"Processing course: {canvas_course.name} (ID: {canvas_course_id})")

                # Check opt-out status
                user_course_pref = session.query(UserCourse).filter_by(
                    user_id=user_id_str,
                    course_id=canvas_course_id # Checking against canvas_course_id first
                ).first()

                # We need the local course ID to check opt-out correctly if it exists
                existing_course = session.query(Course).filter_by(canvas_course_id=canvas_course_id).first()
                local_course_id_for_opt_out = existing_course.id if existing_course else None

                if local_course_id_for_opt_out:
                    user_course_pref = session.query(UserCourse).filter_by(
                        user_id=user_id_str,
                        course_id=local_course_id_for_opt_out
                    ).first()
                    if user_course_pref and user_course_pref.indexing_opt_out:
                        print(f"Skipping opted-out course: {canvas_course.name}")
                        continue

                # Get potentially more detailed info (though get_courses often includes much of it)
                # Try/except for cases where the user might not have full permissions
                try:
                    detailed_course = self.canvas.get_course(canvas_course_id, include=["syllabus_body", "teachers"])
                except ResourceDoesNotExist:
                    print(f"Could not fetch details for course {canvas_course_id}. Skipping.")
                    continue
                except Exception as e:
                    print(f"Error fetching details for course {canvas_course_id}: {e}. Skipping.")
                    continue


                # Prepare data for DB model
                course_data = {
                    "canvas_course_id": canvas_course_id,
                    "course_code": getattr(canvas_course, "course_code", None),
                    "course_name": getattr(canvas_course, "name", "Unknown Course"),
                    "instructor": ", ".join([t.name for t in getattr(detailed_course, 'teachers', []) if hasattr(t, 'name')]) or None,
                    "description": getattr(detailed_course, "public_description", None) or getattr(canvas_course, "public_description", None),
                    "start_date": parse_canvas_datetime(getattr(detailed_course, "start_at", None) or getattr(canvas_course, "start_at", None)),
                    "end_date": parse_canvas_datetime(getattr(detailed_course, "end_at", None) or getattr(canvas_course, "end_at", None)),
                    "updated_at": datetime.now() # Mark as updated now
                }
                syllabus_content = getattr(detailed_course, "syllabus_body", None)


                # Upsert Course
                if existing_course:
                    print(f"Updating existing course: {course_data['course_name']}")
                    for key, value in course_data.items():
                        setattr(existing_course, key, value)
                    local_course = existing_course
                    session.merge(local_course)
                else:
                    print(f"Inserting new course: {course_data['course_name']}")
                    local_course = Course(**course_data)
                    session.add(local_course)
                    # We need to flush to get the local_course.id for the syllabus check
                    session.flush()


                # Upsert Syllabus
                if syllabus_content:
                    existing_syllabus = session.query(Syllabus).filter_by(course_id=local_course.id).first()
                    if existing_syllabus:
                        if existing_syllabus.content != syllabus_content:
                            print(f"Updating syllabus for course {local_course.id}")
                            existing_syllabus.content = syllabus_content
                            existing_syllabus.is_parsed = False # Reset parsed status on update
                            existing_syllabus.updated_at = datetime.now()
                            session.merge(existing_syllabus)
                    else:
                        print(f"Inserting new syllabus for course {local_course.id}")
                        new_syllabus = Syllabus(
                            course_id=local_course.id,
                            content=syllabus_content,
                            updated_at=datetime.now()
                        )
                        session.add(new_syllabus)

                session.commit() # Commit after each course to get ID and handle potential errors individually
                synced_course_ids.append(local_course.id)
                print(f"Successfully processed course {local_course.id} ({local_course.course_name})")

            print(f"Course sync complete. Synced/updated {len(synced_course_ids)} courses.")

        except Exception as e:
            print(f"Error during course sync: {e}")
            session.rollback()
        finally:
            session.close()

        return synced_course_ids

    def sync_assignments(self, local_course_ids: list[int] | None = None) -> int:
        """
        Synchronize assignment data from Canvas to the local database.

        Args:
            local_course_ids: List of local course IDs to sync. If None, syncs for all courses in DB.

        Returns:
            Number of assignments synced or updated.
        """
        if not self.canvas:
            print("Canvas API client not initialized. Skipping assignment sync.")
            return 0

        assignment_count = 0
        session = self._get_session()
        try:
            query = session.query(Course)
            if local_course_ids:
                query = query.filter(Course.id.in_(local_course_ids))
            courses_to_sync = query.all()
            print(f"Starting assignment sync for {len(courses_to_sync)} courses.")

            for local_course in courses_to_sync:
                print(f"Syncing assignments for course: {local_course.course_name} (ID: {local_course.id}, CanvasID: {local_course.canvas_course_id})")
                try:
                    canvas_course: CanvasCourse = self.canvas.get_course(local_course.canvas_course_id)
                    canvas_assignments: PaginatedList[CanvasAssignment] = canvas_course.get_assignments()

                    for canvas_assignment in canvas_assignments:
                        assignment_data = {
                            "course_id": local_course.id,
                            "canvas_assignment_id": canvas_assignment.id,
                            "title": getattr(canvas_assignment, "name", "Untitled Assignment"),
                            "description": getattr(canvas_assignment, "description", None),
                            "assignment_type": self._get_assignment_type(canvas_assignment),
                            "due_date": parse_canvas_datetime(getattr(canvas_assignment, "due_at", None)),
                            "available_from": parse_canvas_datetime(getattr(canvas_assignment, "unlock_at", None)),
                            "available_until": parse_canvas_datetime(getattr(canvas_assignment, "lock_at", None)),
                            "points_possible": getattr(canvas_assignment, "points_possible", None),
                            "submission_types": ",".join(getattr(canvas_assignment, "submission_types", [])),
                            "updated_at": datetime.now()
                        }

                        # Upsert Assignment
                        existing_assignment = session.query(Assignment).filter_by(
                            course_id=local_course.id,
                            canvas_assignment_id=canvas_assignment.id
                        ).first()

                        if existing_assignment:
                            # print(f"Updating assignment: {assignment_data['title']}")
                            for key, value in assignment_data.items():
                                setattr(existing_assignment, key, value)
                            local_assignment = existing_assignment
                            session.merge(local_assignment)
                        else:
                            # print(f"Inserting assignment: {assignment_data['title']}")
                            local_assignment = Assignment(**assignment_data)
                            session.add(local_assignment)
                        session.flush() # Ensure local_assignment has an ID for the calendar event

                        # Upsert Calendar Event for due date
                        if local_assignment.due_date:
                            event_data = {
                                "course_id": local_course.id,
                                "title": local_assignment.title,
                                "description": f"Due date for {local_assignment.assignment_type}: {local_assignment.title}",
                                "event_type": local_assignment.assignment_type or "assignment",
                                "source_type": "assignment",
                                "source_id": local_assignment.id,
                                "event_date": local_assignment.due_date,
                                "updated_at": datetime.now()
                            }
                            existing_event = session.query(CalendarEvent).filter_by(
                                course_id=local_course.id,
                                source_type="assignment",
                                source_id=local_assignment.id
                            ).first()

                            if existing_event:
                                for key, value in event_data.items():
                                    setattr(existing_event, key, value)
                                session.merge(existing_event)
                            else:
                                new_event = CalendarEvent(**event_data)
                                session.add(new_event)

                        assignment_count += 1
                    session.commit() # Commit after processing all assignments for a course
                    print(f"Finished assignments for course {local_course.course_name}.")

                except ResourceDoesNotExist:
                    print(f"Canvas course {local_course.canvas_course_id} not found or inaccessible. Skipping assignments.")
                    session.rollback() # Rollback changes for this course if the course itself fails
                except Exception as e:
                    print(f"Error syncing assignments for course {local_course.canvas_course_id} ({local_course.course_name}): {e}")
                    session.rollback() # Rollback changes for this course on error

            print(f"Assignment sync complete. Synced/updated {assignment_count} assignments.")

        except Exception as e:
            print(f"General error during assignment sync: {e}")
            session.rollback()
        finally:
            session.close()

        return assignment_count

    def sync_modules(self, local_course_ids: list[int] | None = None) -> int:
        """
        Synchronize module data and module items from Canvas to the local database.

        Args:
            local_course_ids: List of local course IDs to sync. If None, syncs for all courses.

        Returns:
            Number of modules synced or updated.
        """
        if not self.canvas:
            print("Canvas API client not initialized. Skipping module sync.")
            return 0

        module_count = 0
        session = self._get_session()
        try:
            query = session.query(Course)
            if local_course_ids:
                query = query.filter(Course.id.in_(local_course_ids))
            courses_to_sync = query.all()
            print(f"Starting module sync for {len(courses_to_sync)} courses.")

            for local_course in courses_to_sync:
                print(f"Syncing modules for course: {local_course.course_name} (ID: {local_course.id}, CanvasID: {local_course.canvas_course_id})")
                try:
                    canvas_course: CanvasCourse = self.canvas.get_course(local_course.canvas_course_id)
                    canvas_modules: PaginatedList[CanvasModule] = canvas_course.get_modules(include=["module_items"])

                    for canvas_module in canvas_modules:
                        module_data = {
                            "course_id": local_course.id,
                            "canvas_module_id": canvas_module.id,
                            "name": getattr(canvas_module, "name", "Untitled Module"),
                            "position": getattr(canvas_module, "position", None),
                            "unlock_date": parse_canvas_datetime(getattr(canvas_module, "unlock_at", None)),
                            "require_sequential_progress": getattr(canvas_module, "require_sequential_progress", False),
                            "updated_at": datetime.now()
                            # Description might be added if needed, but often not available at this level
                        }

                        # Upsert Module
                        existing_module = session.query(Module).filter_by(
                            course_id=local_course.id,
                            canvas_module_id=canvas_module.id
                        ).first()

                        if existing_module:
                            # print(f"Updating module: {module_data['name']}")
                            for key, value in module_data.items():
                                setattr(existing_module, key, value)
                            local_module = existing_module
                            session.merge(local_module)
                        else:
                            # print(f"Inserting module: {module_data['name']}")
                            local_module = Module(**module_data)
                            session.add(local_module)
                        session.flush() # Get local_module.id

                        # Sync Module Items
                        try:
                            canvas_module_items: PaginatedList[CanvasModuleItem] = canvas_module.get_module_items()
                            for canvas_item in canvas_module_items:
                                item_data = {
                                    "module_id": local_module.id,
                                    "canvas_item_id": canvas_item.id,
                                    "title": getattr(canvas_item, "title", "Untitled Item"),
                                    "position": getattr(canvas_item, "position", None),
                                    "item_type": getattr(canvas_item, "type", "Unknown"),
                                    "content_id": getattr(canvas_item, "content_id", None),
                                    "url": getattr(canvas_item, "external_url", None),
                                    "page_url": getattr(canvas_item, "page_url", None),
                                    # content_details could store item.__dict__ if needed
                                    "updated_at": datetime.now()
                                }

                                # Upsert Module Item
                                existing_item = session.query(ModuleItem).filter_by(
                                    module_id=local_module.id,
                                    canvas_item_id=canvas_item.id
                                ).first()

                                if existing_item:
                                    for key, value in item_data.items():
                                        setattr(existing_item, key, value)
                                    session.merge(existing_item)
                                else:
                                    new_item = ModuleItem(**item_data)
                                    session.add(new_item)

                        except Exception as item_exc:
                             print(f"Error syncing items for module {canvas_module.id} in course {local_course.canvas_course_id}: {item_exc}")
                             # Continue with the next module

                        module_count += 1
                    session.commit() # Commit after processing all modules for a course
                    print(f"Finished modules for course {local_course.course_name}.")

                except ResourceDoesNotExist:
                    print(f"Canvas course {local_course.canvas_course_id} not found or inaccessible. Skipping modules.")
                    session.rollback()
                except Exception as e:
                    print(f"Error syncing modules for course {local_course.canvas_course_id} ({local_course.course_name}): {e}")
                    session.rollback()

            print(f"Module sync complete. Synced/updated {module_count} modules.")

        except Exception as e:
            print(f"General error during module sync: {e}")
            session.rollback()
        finally:
            session.close()

        return module_count

    def sync_announcements(self, local_course_ids: list[int] | None = None) -> int:
        """
        Synchronize announcement data from Canvas to the local database.

        Args:
            local_course_ids: List of local course IDs to sync. If None, syncs for all courses.

        Returns:
            Number of announcements synced or updated.
        """
        if not self.canvas:
            print("Canvas API client not initialized. Skipping announcement sync.")
            return 0

        announcement_count = 0
        session = self._get_session()
        try:
            query = session.query(Course)
            if local_course_ids:
                query = query.filter(Course.id.in_(local_course_ids))
            courses_to_sync = query.all()
            print(f"Starting announcement sync for {len(courses_to_sync)} courses.")


            for local_course in courses_to_sync:
                print(f"Syncing announcements for course: {local_course.course_name} (ID: {local_course.id}, CanvasID: {local_course.canvas_course_id})")
                try:
                    # Announcements are often retrieved as discussion topics
                    # Use context_codes for efficiency
                    context_code = f"course_{local_course.canvas_course_id}"
                    canvas_announcements: PaginatedList[CanvasDiscussionTopic] = self.canvas.get_announcements(context_codes=[context_code])

                    for canvas_announcement in canvas_announcements:
                        # Ensure it's actually an announcement (though get_announcements should handle this)
                        # if not getattr(canvas_announcement, 'announcement', False): continue

                        announcement_data = {
                            "course_id": local_course.id,
                            "canvas_announcement_id": canvas_announcement.id,
                            "title": getattr(canvas_announcement, "title", "Untitled Announcement"),
                            "content": getattr(canvas_announcement, "message", None), # HTML content
                            "posted_by": getattr(canvas_announcement, "author", {}).get("display_name") if getattr(canvas_announcement, "author", None) else None,
                            "posted_at": parse_canvas_datetime(getattr(canvas_announcement, "posted_at", None)),
                            "updated_at": datetime.now()
                        }

                        # Upsert Announcement
                        existing_announcement = session.query(Announcement).filter_by(
                            # course_id=local_course.id, # canvas_announcement_id should be globally unique
                            canvas_announcement_id=canvas_announcement.id
                        ).first()

                        if existing_announcement:
                            # print(f"Updating announcement: {announcement_data['title']}")
                            # Ensure course_id is correct if found by canvas_id only
                            announcement_data["course_id"] = local_course.id
                            for key, value in announcement_data.items():
                                setattr(existing_announcement, key, value)
                            session.merge(existing_announcement)
                        else:
                            # print(f"Inserting announcement: {announcement_data['title']}")
                            new_announcement = Announcement(**announcement_data)
                            session.add(new_announcement)

                        announcement_count += 1
                    session.commit() # Commit after processing announcements for a course
                    print(f"Finished announcements for course {local_course.course_name}.")

                except ResourceDoesNotExist:
                     print(f"Canvas course {local_course.canvas_course_id} not found or inaccessible for announcements. Skipping.")
                     session.rollback()
                except Exception as e:
                    print(f"Error syncing announcements for course {local_course.canvas_course_id} ({local_course.course_name}): {e}")
                    session.rollback()

            print(f"Announcement sync complete. Synced/updated {announcement_count} announcements.")

        except Exception as e:
            print(f"General error during announcement sync: {e}")
            session.rollback()
        finally:
            session.close()

        return announcement_count


    def sync_all(self, user_id_str: str | None = None, term_id: int | None = -1) -> dict[str, int]:
        """
        Synchronize all relevant data from Canvas to the local database.

        Args:
            user_id_str: Optional user ID string to identify the user context.
            term_id: Optional term ID to filter courses (-1 for latest term, None for all terms).

        Returns:
            Dictionary with counts of synced items.
        """
        print(f"Starting full sync process. User: {user_id_str or 'current'}, Term: {term_id}")

        # 1. Sync Courses (returns local IDs of synced/updated courses)
        local_course_ids = self.sync_courses(user_id_str=user_id_str, term_id=term_id)

        if not local_course_ids:
            print("No courses were synced. Aborting further synchronization.")
            return {"courses": 0, "assignments": 0, "modules": 0, "announcements": 0}

        print(f"Proceeding to sync details for {len(local_course_ids)} courses...")

        # 2. Sync other data types using the obtained local course IDs
        assignment_count = self.sync_assignments(local_course_ids)
        module_count = self.sync_modules(local_course_ids)
        announcement_count = self.sync_announcements(local_course_ids)
        # Add calls to sync other data types (discussions, files, grades) here if implemented

        print("Full sync process completed.")
        return {
            "courses": len(local_course_ids),
            "assignments": assignment_count,
            "modules": module_count,
            "announcements": announcement_count,
            # Add counts for other synced types
        }

    def _get_assignment_type(self, assignment: CanvasAssignment) -> str:
        """
        Determine the type of an assignment based on Canvas data.

        Args:
            assignment: Canvas assignment object.

        Returns:
            Assignment type string (e.g., 'quiz', 'discussion', 'exam', 'assignment').
        """
        submission_types = getattr(assignment, "submission_types", [])
        name_lower = getattr(assignment, "name", "").lower()

        if "online_quiz" in submission_types:
            return "quiz"
        elif "discussion_topic" in submission_types:
            return "discussion"
        elif any(term in name_lower for term in ["exam", "midterm", "final"]):
            return "exam"
        else:
            return "assignment"

# Example usage (optional)
if __name__ == "__main__":
    print("Running CanvasClient example...")
    client = CanvasClient()
    if client.canvas:
        sync_results = client.sync_all(term_id=-1) # Sync only the latest term
        print("Sync results:", sync_results)
    else:
        print("Canvas client could not be initialized (check API key/URL and canvasapi installation).")
