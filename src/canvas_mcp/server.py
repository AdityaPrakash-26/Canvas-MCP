"""
Canvas MCP Server

This MCP server provides tools and resources for accessing Canvas LMS data,
using SQLAlchemy for database interaction.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from sqlalchemy import desc, func, or_, String as SQLString
from sqlalchemy.orm import Session, joinedload

# Add project root to sys.path to allow importing database and models
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local imports after path adjustment
try:
    from canvas_mcp.canvas_client import CanvasClient
    from canvas_mcp.database import SessionLocal, engine, init_db
    from canvas_mcp.models import (
        Announcement,
        Assignment,
        Course,
        Module,
        ModuleItem,
        Syllabus,
        UserCourse,
        orm_to_dict, # Import the helper
    )
except ImportError as e:
    print(f"Error importing local modules in server.py: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path}")
    raise


# Load environment variables
load_dotenv()

# Configure paths (using database.py's path logic)
DB_PATH = Path(str(engine.url).replace("sqlite:///", ""))

# Ensure database is initialized (database.py handles this on import)
print(f"Database path check in server: {DB_PATH}")
if not DB_PATH.exists() or os.path.getsize(DB_PATH) == 0:
     print("Database not found or empty, initializing...")
     init_db(engine)


# Create Canvas client
API_KEY = os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
# Pass the session factory to the client
canvas_client = CanvasClient(db_session_factory=SessionLocal, api_key=API_KEY, api_url=API_URL)

# Create an MCP server
mcp = FastMCP(
    "Canvas MCP",
    dependencies=["canvasapi>=3.3.0", "structlog>=24.1.0", "python-dotenv>=1.0.1", "sqlalchemy>=2.0.0"],
)


# --- Database Session Dependency ---
# Although FastMCP doesn't directly support Depends like FastAPI,
# we manage sessions manually within each tool/resource.

def get_db_session() -> Session:
    """Provides a SQLAlchemy session."""
    return SessionLocal()


# --- MCP Tools ---

@mcp.tool()
def sync_canvas_data(force: bool = False, term_id: Optional[int] = -1) -> Dict[str, int]:
    """
    Synchronize data from Canvas LMS to the local database using SQLAlchemy.

    Args:
        force: If True, might trigger a more thorough sync in the future (currently unused).
        term_id: Optional term ID to filter courses (-1 for latest, None for all).

    Returns:
        Dictionary with counts of synced items or an error message.
    """
    if not canvas_client.canvas:
        return {"error": "Canvas API client not initialized. Cannot sync."}
    try:
        # Assuming user_id comes from authentication context if needed, otherwise syncs for the API key's user
        result = canvas_client.sync_all(term_id=term_id)
        return result
    except ImportError:
        # This case should be handled by the initial check, but kept for safety
        return {"error": "canvasapi module is required for this operation"}
    except Exception as e:
        print(f"Error during sync_canvas_data: {e}")
        return {"error": f"An unexpected error occurred during sync: {e}"}


@mcp.tool()
def get_upcoming_deadlines(days: int = 7, course_id: Optional[int] = None) -> List[Dict[str, object]]:
    """
    Get upcoming assignment deadlines using SQLAlchemy.

    Args:
        days: Number of days to look ahead.
        course_id: Optional local course ID to filter by.

    Returns:
        List of upcoming deadlines (dictionaries).
    """
    session = get_db_session()
    try:
        now = datetime.now()
        end_date = now + timedelta(days=days)

        query = session.query(
            Course.course_code,
            Course.course_name,
            Assignment.title.label("assignment_title"),
            Assignment.assignment_type,
            Assignment.due_date,
            Assignment.points_possible
        ).join(Assignment, Course.id == Assignment.course_id).filter(
            Assignment.due_date != None, # Ensure due date exists
            Assignment.due_date >= now,
            Assignment.due_date <= end_date
        )

        if course_id is not None:
            query = query.filter(Course.id == course_id)

        query = query.order_by(Assignment.due_date.asc())

        results = query.all()

        # Convert results (which are KeyedTuples) to dictionaries
        deadlines = [
            {
                "course_code": r.course_code,
                "course_name": r.course_name,
                "assignment_title": r.assignment_title,
                "assignment_type": r.assignment_type,
                # Format datetime for JSON compatibility
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "points_possible": r.points_possible,
            } for r in results
        ]
        return deadlines
    finally:
        session.close()


@mcp.tool()
def get_course_list() -> List[Dict[str, object]]:
    """
    Get list of all courses from the database using SQLAlchemy.

    Returns:
        List of course information (dictionaries).
    """
    session = get_db_session()
    try:
        courses = session.query(
            Course.id,
            Course.canvas_course_id,
            Course.course_code,
            Course.course_name,
            Course.instructor,
            Course.start_date,
            Course.end_date
        ).order_by(desc(Course.start_date)).all()

        # Convert results to dictionaries
        return [
            {
                "id": c.id,
                "canvas_course_id": c.canvas_course_id,
                "course_code": c.course_code,
                "course_name": c.course_name,
                "instructor": c.instructor,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
            } for c in courses
        ]
    finally:
        session.close()


@mcp.tool()
def get_course_assignments(course_id: int) -> List[Dict[str, object]]:
    """
    Get all assignments for a specific course using SQLAlchemy.

    Args:
        course_id: Local Course ID.

    Returns:
        List of assignments (dictionaries).
    """
    session = get_db_session()
    try:
        assignments = session.query(Assignment).filter(
            Assignment.course_id == course_id
        ).order_by(Assignment.due_date.asc()).all()

        # Convert ORM objects to dictionaries
        return [orm_to_dict(a) for a in assignments]
    finally:
        session.close()


@mcp.tool()
def get_course_modules(course_id: int, include_items: bool = False) -> List[Dict[str, object]]:
    """
    Get all modules for a specific course using SQLAlchemy.

    Args:
        course_id: Local Course ID.
        include_items: Whether to include module items.

    Returns:
        List of modules (dictionaries).
    """
    session = get_db_session()
    try:
        query = session.query(Module).filter(Module.course_id == course_id)

        if include_items:
            # Eager load items relationship, ordered by position
            query = query.options(joinedload(Module.items).raiseload('*')) # Use raiseload for nested items if any

        modules = query.order_by(Module.position.asc()).all()

        # Convert to list of dictionaries, including items if requested
        results = []
        for mod in modules:
            module_dict = orm_to_dict(mod)
            if include_items:
                module_dict["items"] = [orm_to_dict(item) for item in mod.items]
            results.append(module_dict)
        return results
    finally:
        session.close()


@mcp.tool()
def get_syllabus(course_id: int, format: str = "raw") -> Dict[str, object]:
    """
    Get the syllabus for a specific course using SQLAlchemy.

    Args:
        course_id: Local Course ID.
        format: Format to return ("raw" for HTML, "parsed" for extracted text).

    Returns:
        Dictionary with syllabus content and course info.
    """
    session = get_db_session()
    try:
        course = session.query(
            Course.course_code,
            Course.course_name,
            Course.instructor
        ).filter(Course.id == course_id).first()

        if not course:
            return {"error": f"Course with ID {course_id} not found"}

        syllabus = session.query(
            Syllabus.content,
            Syllabus.parsed_content,
            Syllabus.is_parsed
        ).filter(Syllabus.course_id == course_id).first()

        result = {
            "course_code": course.course_code,
            "course_name": course.course_name,
            "instructor": course.instructor,
            "content": "No syllabus available" # Default content
        }

        if syllabus:
            if format == "parsed" and syllabus.is_parsed and syllabus.parsed_content:
                result["content"] = syllabus.parsed_content
            else:
                result["content"] = syllabus.content or "No syllabus content found" # Use raw content if parsed fails or not requested

        return result
    finally:
        session.close()


@mcp.tool()
def get_course_announcements(course_id: int, limit: int = 10) -> List[Dict[str, object]]:
    """
    Get announcements for a specific course using SQLAlchemy.

    Args:
        course_id: Local Course ID.
        limit: Maximum number of announcements to return.

    Returns:
        List of announcements (dictionaries).
    """
    session = get_db_session()
    try:
        announcements = session.query(Announcement).filter(
            Announcement.course_id == course_id
        ).order_by(desc(Announcement.posted_at)).limit(limit).all()

        return [orm_to_dict(a) for a in announcements]
    finally:
        session.close()


@mcp.tool()
def search_course_content(query_term: str, course_id: Optional[int] = None) -> List[Dict[str, object]]:
    """
    Search for content across courses using SQLAlchemy.

    Args:
        query_term: Search query.
        course_id: Optional local course ID to limit search.

    Returns:
        List of matching items (dictionaries).
    """
    session = get_db_session()
    try:
        search_pattern = f"%{query_term}%"
        results = []

        # Base query part for joining with Course
        base_query = session.query(
            Course.course_code,
            Course.course_name,
        )
        if course_id:
            base_query = base_query.filter(Course.id == course_id)

        # Search Assignments
        assignment_query = base_query.join(Assignment).filter(
            or_(Assignment.title.ilike(search_pattern), Assignment.description.ilike(search_pattern))
        ).add_columns(
            Assignment.title,
            Assignment.description,
            func.cast("assignment", SQLString).label("content_type"),
            Assignment.id.label("content_id")
        )
        assignments = assignment_query.all()
        results.extend([{**row._asdict()} for row in assignments]) # Convert KeyedTuple to dict

        # Search Modules
        module_query = base_query.join(Module).filter(
             or_(Module.name.ilike(search_pattern), Module.description.ilike(search_pattern))
        ).add_columns(
            Module.name.label("title"),
            Module.description,
            func.cast("module", SQLString).label("content_type"),
            Module.id.label("content_id")
        )
        modules = module_query.all()
        results.extend([{**row._asdict()} for row in modules])

        # Search Module Items
        module_item_query = base_query.join(Module, Course.id == Module.course_id).join(ModuleItem).filter(
             or_(ModuleItem.title.ilike(search_pattern), ModuleItem.content_details.ilike(search_pattern)) # Assuming content_details is stored as TEXT/JSON searchable string
        ).add_columns(
            ModuleItem.title,
            ModuleItem.content_details.label("description"), # Adjust if content_details is JSON
            func.cast("module_item", SQLString).label("content_type"),
            ModuleItem.id.label("content_id")
        )
        module_items = module_item_query.all()
        results.extend([{**row._asdict()} for row in module_items])

        # Search Syllabi
        syllabus_query = base_query.join(Syllabus).filter(
            Syllabus.content.ilike(search_pattern) # Search raw content
        ).add_columns(
            func.cast("Syllabus", SQLString).label("title"),
            Syllabus.content.label("description"),
            func.cast("syllabus", SQLString).label("content_type"),
            Syllabus.id.label("content_id")
        )
        syllabi = syllabus_query.all()
        results.extend([{**row._asdict()} for row in syllabi])

        return results
    finally:
        session.close()


@mcp.tool()
def opt_out_course(course_id: int, user_id: str, opt_out: bool = True) -> Dict[str, object]:
    """
    Opt out of indexing a specific course using SQLAlchemy.

    Args:
        course_id: Local Course ID.
        user_id: User ID string.
        opt_out: Whether to opt out (True) or opt in (False).

    Returns:
        Status of the operation.
    """
    session = get_db_session()
    try:
        # Check if course exists by local ID
        course = session.query(Course.id).filter(Course.id == course_id).first()
        if not course:
            return {"success": False, "message": f"Course with local ID {course_id} not found"}

        # Find existing preference or create a new one
        user_pref = session.query(UserCourse).filter_by(user_id=user_id, course_id=course_id).first()

        if user_pref:
            user_pref.indexing_opt_out = opt_out
            user_pref.updated_at = datetime.now()
            session.merge(user_pref)
            message = f"Course {course_id} {'opted out' if opt_out else 'opted in'} successfully for user {user_id}"
        else:
            new_pref = UserCourse(
                user_id=user_id,
                course_id=course_id,
                indexing_opt_out=opt_out,
                updated_at=datetime.now()
            )
            session.add(new_pref)
            message = f"Created preference for course {course_id}: {'opted out' if opt_out else 'opted in'} for user {user_id}"

        session.commit()
        return {
            "success": True,
            "message": message,
            "course_id": course_id,
            "user_id": user_id,
            "opted_out": opt_out,
        }
    except Exception as e:
        session.rollback()
        print(f"Error in opt_out_course: {e}")
        return {"success": False, "message": f"An error occurred: {e}"}
    finally:
        session.close()


# --- MCP Resources ---

# Helper to format resource content
def format_resource(title: str, sections: Dict[str, str]) -> str:
    content = f"# {title}\n\n"
    for heading, text in sections.items():
        content += f"## {heading}\n{text}\n\n"
    return content.strip()

@mcp.resource("course://{course_id}")
def get_course_resource(course_id: int) -> str:
    """
    Get resource with course information using SQLAlchemy.

    Args:
        course_id: Local Course ID.

    Returns:
        Course information as formatted text.
    """
    session = get_db_session()
    try:
        course = session.query(Course).options(
            joinedload(Course.assignments) # Eager load assignments for count/next due
        ).filter(Course.id == course_id).first()

        if not course:
            return f"Course with ID {course_id} not found"

        # Get module count separately
        module_count = session.query(func.count(Module.id)).filter(Module.course_id == course_id).scalar() or 0
        assignment_count = len(course.assignments)

        # Find next due assignment
        now = datetime.now()
        next_assignment = None
        min_due_date = None
        for assign in course.assignments:
            if assign.due_date and assign.due_date > now:
                if min_due_date is None or assign.due_date < min_due_date:
                    min_due_date = assign.due_date
                    next_assignment = assign

        # Format the information
        title = f"{course.course_name} ({course.course_code})"
        sections = {
            "Details": f"**Instructor:** {course.instructor or 'Not specified'}\n"
                       f"**Canvas ID:** {course.canvas_course_id}\n"
                       f"**Start Date:** {course.start_date.strftime('%Y-%m-%d') if course.start_date else 'N/A'}\n"
                       f"**End Date:** {course.end_date.strftime('%Y-%m-%d') if course.end_date else 'N/A'}",
            "Description": course.description or "No description available",
            "Summary": f"- **Assignments:** {assignment_count}\n- **Modules:** {module_count}",
            "Next Due Assignment": f"- **{next_assignment.title}** - Due: {next_assignment.due_date.strftime('%Y-%m-%d %H:%M')}" if next_assignment else "- No upcoming assignments"
        }
        return format_resource(title, sections)

    finally:
        session.close()


@mcp.resource("deadlines://{days}")
def get_deadlines_resource(days: int = 7) -> str:
    """
    Get resource with upcoming deadlines using SQLAlchemy tool function.

    Args:
        days: Number of days to look ahead.

    Returns:
        Upcoming deadlines as formatted text.
    """
    deadlines = get_upcoming_deadlines(days) # Reuse the tool function

    if not deadlines:
        return f"No deadlines found in the next {days} days."

    content = f"# Upcoming Deadlines (Next {days} Days)\n\n"
    deadlines.sort(key=lambda x: (x.get('course_code', ''), x.get('due_date', ''))) # Sort by course then date

    current_course_code = None
    for item in deadlines:
        course_code = item.get('course_code')
        if course_code != current_course_code:
            current_course_code = course_code
            content += f"## {item.get('course_name')} ({course_code})\n\n"

        due_date_str = item.get("due_date")
        formatted_date = "No due date"
        if due_date_str:
            try:
                due_dt = datetime.fromisoformat(due_date_str)
                formatted_date = due_dt.strftime("%A, %B %d, %Y %I:%M %p")
            except (ValueError, TypeError):
                formatted_date = due_date_str # Fallback

        points = item.get("points_possible")
        points_str = f" ({points} points)" if points else ""
        content += f"- **{item.get('assignment_title')}**{points_str} - Due: {formatted_date}\n"

    return content.strip()


@mcp.resource("syllabus://{course_id}")
def get_syllabus_resource(course_id: int) -> str:
    """
    Get resource with course syllabus using SQLAlchemy tool function.

    Args:
        course_id: Local Course ID.

    Returns:
        Syllabus as formatted text.
    """
    syllabus_data = get_syllabus(course_id, format="parsed") # Reuse tool, prefer parsed

    if syllabus_data.get("error"):
        return syllabus_data["error"]
    if not syllabus_data.get("content"):
         return f"Syllabus for course ID {course_id} not found or empty."

    title = f"Syllabus: {syllabus_data.get('course_name')} ({syllabus_data.get('course_code')})"
    sections = {}
    if syllabus_data.get("instructor"):
        sections["Instructor"] = syllabus_data.get("instructor")
    sections["Content"] = syllabus_data.get("content")

    return format_resource(title, sections)


@mcp.resource("assignments://{course_id}")
def get_assignments_resource(course_id: int) -> str:
    """
    Get resource with course assignments using SQLAlchemy tool function.

    Args:
        course_id: Local Course ID.

    Returns:
        Assignments as formatted text.
    """
    session = get_db_session()
    try:
        course = session.query(Course.course_code, Course.course_name).filter(Course.id == course_id).first()
        if not course:
            return f"Course with ID {course_id} not found"

        assignments = get_course_assignments(course_id) # Reuse tool function

        if not assignments:
            return f"No assignments found for {course.course_name} ({course.course_code})"

        title = f"Assignments: {course.course_name} ({course.course_code})"
        content = f"# {title}\n\n"

        # Group by type
        assignments_by_type: Dict[str, List[Dict[str, object]]] = {}
        for a in assignments:
            a_type = a.get("assignment_type", "Other") or "Other"
            assignments_by_type.setdefault(a_type, []).append(a)

        for a_type, items in sorted(assignments_by_type.items()):
            content += f"## {a_type.capitalize()}s\n\n"
            items.sort(key=lambda x: x.get('due_date') or '') # Sort by due date within type
            for item in items:
                due_date_str = item.get("due_date")
                formatted_date = "No due date"
                if due_date_str:
                     try:
                         due_dt = datetime.fromisoformat(due_date_str)
                         formatted_date = due_dt.strftime("%A, %B %d, %Y %I:%M %p")
                     except (ValueError, TypeError):
                         formatted_date = due_date_str

                points = item.get("points_possible")
                points_str = f" ({points} points)" if points else ""

                content += f"### {item.get('title')}{points_str}\n"
                content += f"**Due Date:** {formatted_date}\n"
                desc = item.get('description')
                content += f"{desc}\n\n" if desc else "No description available.\n\n"

        return content.strip()
    finally:
        session.close()


if __name__ == "__main__":
    print("Starting Canvas MCP server...")
    mcp.run()