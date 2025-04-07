"""
Canvas MCP Server

This MCP server provides tools and resources for accessing Canvas LMS data.
It integrates with the Canvas API and local SQLite database to provide
structured access to course information.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from canvas_mcp.utils.db_manager import DatabaseManager
from canvas_mcp.utils.file_extractor import extract_text_from_file

try:
    from .canvas_client import CanvasClient
except ImportError:
    from canvas_mcp.canvas_client import CanvasClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("canvas_mcp")

# Configure paths
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_DIR / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"

# Allow overriding the database path for testing
if os.environ.get("CANVAS_MCP_TEST_DB"):
    DB_PATH = Path(os.environ.get("CANVAS_MCP_TEST_DB"))
    print(f"Using test database: {DB_PATH}")

# Ensure directories exist
os.makedirs(DB_PATH.parent, exist_ok=True)

# Initialize database if it doesn't exist
if not DB_PATH.exists():
    import sys

    sys.path.append(str(PROJECT_DIR))
    from init_db import create_database

    create_database(str(DB_PATH))

print(f"Database initialized at {DB_PATH}")

# Create Canvas client (will connect to API if canvasapi is installed)
API_KEY = os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

try:
    canvas_client = CanvasClient(str(DB_PATH), API_KEY, API_URL)
    logger.info(f"Canvas client initialized successfully with database: {DB_PATH}")
except Exception as e:
    logger.error(f"Error initializing Canvas client: {e}")
    # Create a dummy client that will use database-only operations
    canvas_client = CanvasClient(str(DB_PATH), None, None)
    logger.warning("Created database-only Canvas client due to initialization error")

# Initialize database manager
db_manager = DatabaseManager(str(DB_PATH))

# Cache for course code to ID mapping (to reduce database lookups)
course_code_cache = {}

# Create an MCP server
mcp = FastMCP(
    "Canvas MCP",
    dependencies=[
        "canvasapi>=3.3.0",
        "structlog>=24.1.0",
        "python-dotenv>=1.0.1",
        "pdfplumber>=0.7.0",
        "beautifulsoup4>=4.12.0",
        "python-docx>=0.8.11",
    ],
    description="A Canvas integration for accessing course information, assignments, and resources.",
)


# Create custom DatabaseManager instance for this module
db_manager = DatabaseManager(DB_PATH)


def extract_links_from_content(content: str) -> list[dict[str, str]]:
    """
    Extract links from HTML content.

    Args:
        content: HTML content to parse

    Returns:
        List of dictionaries with 'url' and 'text' keys
    """
    if not content or not isinstance(content, str):
        return []

    links = []
    try:
        # Find <a> tags with href attributes
        a_tag_pattern = re.compile(
            r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL
        )
        for match in a_tag_pattern.finditer(content):
            url = match.group(1)
            text = re.sub(
                r"<[^>]*>", "", match.group(2)
            ).strip()  # Remove nested HTML tags
            if url:
                links.append({"url": url, "text": text or url})

        # If no <a> tags found, look for bare URLs
        if not links:
            url_pattern = re.compile(r"https?://\S+")
            for match in url_pattern.finditer(content):
                url = match.group(0)
                links.append({"url": url, "text": url})

    except Exception:
        # Fall back to simple search if regex fails
        if "href=" in content:
            # Just extract the link without parsing
            start = content.find('href="') + 6
            end = content.find('"', start)
            if start > 6 and end > start:
                url = content[start:end]
                links.append({"url": url, "text": "Link"})

    return links


# MCP Tools


@mcp.tool()
def sync_canvas_data(force: bool = False) -> dict[str, int]:
    """
    Synchronize data from Canvas LMS to the local database.

    Args:
        force: If True, sync all data even if recently updated

    Returns:
        Dictionary with counts of synced items
    """
    try:
        # Use the global canvas_client that was initialized with the correct DB_PATH
        result = canvas_client.sync_all()
        return result
    except ImportError:
        return {"error": "canvasapi module is required for this operation"}
    except Exception as e:
        logger.error(f"Error syncing Canvas data: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_upcoming_deadlines(
    days: int = 7, course_id: int | None = None
) -> list[dict[str, Any]]:
    """
    Get upcoming assignment deadlines.

    Args:
        days: Number of days to look ahead
        course_id: Optional course ID to filter by

    Returns:
        List of upcoming deadlines
    """
    # Get database connection
    conn, cursor = db_manager.connect()

    try:
        # Calculate the date range
        now = datetime.now()
        end_date = now + timedelta(days=days)

        # Format dates for SQLite comparison
        # Note: For test data in future dates (2025), this will still work
        # as we're using relative dates from the current date
        now_str = now.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Build the query with simple date string comparison for better compatibility
        query = """
        SELECT
            c.course_code,
            c.course_name,
            a.title AS assignment_title,
            a.assignment_type,
            a.due_date,
            a.points_possible
        FROM
            assignments a
        JOIN
            courses c ON a.course_id = c.id
        WHERE
            a.due_date IS NOT NULL
            AND date(a.due_date) >= date(?)
            AND date(a.due_date) <= date(?)
        """

        params: list[Any] = [now_str, end_date_str]

        # Add course filter if specified
        if course_id is not None:
            query += " AND c.id = ?"
            params.append(course_id)

        query += " ORDER BY a.due_date ASC"

        # Execute query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        return db_manager.rows_to_dicts(rows)
    finally:
        # Close the connection
        conn.close()


@mcp.tool()
def get_course_list() -> list[dict[str, Any]]:
    """
    Get list of all courses in the database.

    Returns:
        List of course information
    """
    conn, cursor = db_manager.connect()

    try:
        cursor.execute("""
        SELECT
            c.id,
            c.canvas_course_id,
            c.course_code,
            c.course_name,
            c.instructor,
            c.start_date,
            c.end_date
        FROM
            courses c
        ORDER BY
            c.start_date DESC
        """)

        rows = cursor.fetchall()
        return db_manager.rows_to_dicts(rows)
    finally:
        conn.close()


@mcp.tool()
def get_course_assignments(course_id: int) -> list[dict[str, Any]]:
    """
    Get all assignments for a specific course.

    Args:
        course_id: Course ID

    Returns:
        List of assignments
    """
    conn, cursor = db_manager.connect()

    try:
        cursor.execute(
            """
        SELECT
            a.id,
            a.canvas_assignment_id,
            a.title,
            a.description,
            a.assignment_type,
            a.due_date,
            a.available_from,
            a.available_until,
            a.points_possible,
            a.submission_types
        FROM
            assignments a
        WHERE
            a.course_id = ?
        ORDER BY
            a.due_date ASC
        """,
            (course_id,),
        )

        rows = cursor.fetchall()
        return db_manager.rows_to_dicts(rows)
    finally:
        conn.close()


@mcp.tool()
def get_course_modules(
    course_id: int, include_items: bool = False
) -> list[dict[str, Any]]:
    """
    Get all modules for a specific course.

    Args:
        course_id: Course ID
        include_items: Whether to include module items

    Returns:
        List of modules
    """
    conn, cursor = db_manager.connect()

    try:
        cursor.execute(
            """
        SELECT
            m.id,
            m.canvas_module_id,
            m.name,
            m.description,
            m.unlock_date,
            m.position
        FROM
            modules m
        WHERE
            m.course_id = ?
        ORDER BY
            m.position ASC
        """,
            (course_id,),
        )

        modules = db_manager.rows_to_dicts(cursor.fetchall())

        # Include module items if requested
        if include_items:
            for module in modules:
                cursor.execute(
                    """
                SELECT
                    mi.id,
                    mi.canvas_item_id,
                    mi.title,
                    mi.item_type,
                    mi.position,
                    mi.url,
                    mi.page_url,
                    mi.content_details
                FROM
                    module_items mi
                WHERE
                    mi.module_id = ?
                ORDER BY
                    mi.position ASC
                """,
                    (module["id"],),
                )

                module["items"] = db_manager.rows_to_dicts(cursor.fetchall())

        return modules
    finally:
        conn.close()


@mcp.tool()
def get_syllabus(course_id: int, format: str = "raw") -> dict[str, Any]:
    """
    Get the syllabus for a specific course.

    Args:
        course_id: Course ID
        format: Format to return ("raw" for HTML, "parsed" for extracted text)

    Returns:
        Dictionary with syllabus content
    """
    conn, cursor = db_manager.connect()

    try:
        # Get course information
        cursor.execute(
            """
        SELECT
            c.course_code,
            c.course_name,
            c.instructor
        FROM
            courses c
        WHERE
            c.id = ?
        """,
            (course_id,),
        )

        course_row = cursor.fetchone()
        course = (
            db_manager.row_to_dict(course_row)
            if course_row
            else {"course_code": "", "course_name": "", "instructor": ""}
        )

        # Get syllabus content
        cursor.execute(
            """
        SELECT
            s.content,
            s.content_type,
            s.parsed_content,
            s.is_parsed
        FROM
            syllabi s
        WHERE
            s.course_id = ?
        """,
            (course_id,),
        )

        syllabus_row = cursor.fetchone()
        syllabus = (
            db_manager.row_to_dict(syllabus_row)
            if syllabus_row
            else {
                "content": "",
                "content_type": "html",
                "parsed_content": "",
                "is_parsed": False,
            }
        )

        result = {**course}

        # Handle different content types
        content_type = syllabus.get("content_type", "html")

        if (
            format == "parsed"
            and syllabus.get("is_parsed")
            and syllabus.get("parsed_content")
        ):
            result["content"] = syllabus.get("parsed_content")
            result["content_type"] = "text"
        else:
            result["content"] = syllabus.get("content", "No syllabus available")
            result["content_type"] = content_type

            # Add helpful message for non-HTML content types
            if content_type == "pdf_link" and result["content"]:
                result["content_note"] = (
                    "This syllabus is available as a PDF document. The link is included in the content."
                )
            elif content_type == "external_link" and result["content"]:
                result["content_note"] = (
                    "This syllabus is available as an external link. The URL is included in the content."
                )
            elif content_type.startswith("extracted_"):
                # For extracted content types, provide a helpful note
                file_type = content_type.replace("extracted_", "")
                result["content_note"] = (
                    f"This syllabus content was extracted from a {file_type.upper()} file."
                )

                # If we're displaying raw content but have parsed content available,
                # mention that the parsed version is available
                if (
                    format == "raw"
                    and syllabus.get("is_parsed")
                    and syllabus.get("parsed_content")
                ):
                    result["format_note"] = (
                        "A plain text version of this syllabus is available by setting format='parsed'."
                    )

                # If the content is very large, add a note about that
                if len(result["content"]) > 10000:
                    result["size_note"] = (
                        "This syllabus content is quite large. Consider using the parsed format for a cleaner view."
                    )

        # Always ensure course_code is present for tests
        if "course_code" not in result:
            result["course_code"] = ""

        # If we have no content but files might be available, suggest checking for a syllabus file
        if result["content"] in [
            "",
            "No syllabus available",
            "<p>No syllabus content available</p>",
        ]:
            result["suggestion"] = (
                "No syllabus content found in the database. Try using get_syllabus_file() to find and extract a syllabus file."
            )

        return result
    finally:
        conn.close()


@mcp.tool()
def get_course_announcements(course_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get announcements for a specific course.

    Args:
        course_id: Course ID
        limit: Maximum number of announcements to return

    Returns:
        List of announcements
    """
    conn, cursor = db_manager.connect()

    try:
        cursor.execute(
            """
        SELECT
            a.id,
            a.canvas_announcement_id,
            a.title,
            a.content,
            a.posted_by,
            a.posted_at
        FROM
            announcements a
        WHERE
            a.course_id = ?
        ORDER BY
            a.posted_at DESC
        LIMIT ?
        """,
            (course_id, limit),
        )

        rows = cursor.fetchall()
        return db_manager.rows_to_dicts(rows)
    finally:
        conn.close()


@mcp.tool()
def get_course_files(course_id: int, file_type: str = None) -> list[dict[str, Any]]:
    """
    Get all files available in a specific course, with optional filtering by file type.

    Args:
        course_id: Course ID
        file_type: Optional file extension to filter by (e.g., 'pdf', 'docx')

    Returns:
        List of files with URLs
    """
    try:
        files = canvas_client.extract_files_from_course(course_id, file_type)

        # Add extraction URLs if needed
        result = []
        for file in files:
            # Add a property to identify if this might be a syllabus
            is_syllabus = "syllabus" in file.get("name", "").lower()

            result.append(
                {
                    "name": file.get("name", "Unnamed File"),
                    "url": file.get("url", ""),
                    "content_type": file.get("content_type", ""),
                    "size": file.get("size", ""),
                    "created_at": file.get("created_at", ""),
                    "updated_at": file.get("updated_at", ""),
                    "source": file.get("source", "unknown"),
                    "is_syllabus": is_syllabus,
                }
            )

        return result
    except Exception as e:
        return [{"error": f"Error getting files: {e}"}]


@mcp.tool()
def get_syllabus_file(course_id: int, extract_content: bool = True) -> dict[str, Any]:
    """
    Attempt to find a syllabus file for a specific course.

    Args:
        course_id: Course ID
        extract_content: Whether to extract and store content from the syllabus file

    Returns:
        Dictionary with syllabus file information or error
    """
    try:
        # Use the global canvas_client instance directly
        if canvas_client.canvas is None:
            logger.warning("Canvas API not available in get_syllabus_file")
            return {
                "success": False,
                "course_id": course_id,
                "error": "Canvas API connection not available",
            }

        # Get all files in the course using the global client
        files = canvas_client.extract_files_from_course(course_id)

        # Look for files with "syllabus" in the name
        syllabus_files = []
        for file in files:
            if "syllabus" in file["name"].lower():
                syllabus_files.append(file)

        if not syllabus_files:
            return {
                "success": False,
                "course_id": course_id,
                "error": "No syllabus file found",
            }

        # Get the first syllabus file found
        syllabus_file = syllabus_files[0]
        result = {
            "success": True,
            "course_id": course_id,
            "syllabus_file": syllabus_file,
            "all_syllabus_files": syllabus_files,
        }

        # Extract content if requested
        if extract_content and "url" in syllabus_file:
            file_url = syllabus_file["url"]
            file_name = syllabus_file["name"]

            # Determine file type
            file_type = None
            if file_name.lower().endswith(".pdf"):
                file_type = "pdf"
            elif file_name.lower().endswith((".docx", ".doc")):
                file_type = "docx"

            # Extract content
            extraction = extract_text_from_file(file_url, file_type)

            if extraction["success"]:
                # Store the extracted content in the database
                conn, cursor = db_manager.connect()

                try:
                    # Check if there's already a syllabus entry
                    cursor.execute(
                        "SELECT id, content_type FROM syllabi WHERE course_id = ?",
                        (course_id,),
                    )
                    syllabus_row = cursor.fetchone()

                    # Get the original syllabus content
                    original_content = ""
                    content_type = "html"

                    if syllabus_row:
                        # Get current content
                        cursor.execute(
                            "SELECT content FROM syllabi WHERE id = ?",
                            (syllabus_row["id"],),
                        )
                        content_row = cursor.fetchone()
                        if content_row:
                            original_content = content_row["content"]
                            content_type = syllabus_row["content_type"]

                    # Format the content to include the original syllabus
                    # along with the extracted file content
                    extracted_content = extraction["text"]

                    # Add metadata about the file source
                    full_content = f"""
                    <div class="syllabus-extracted-file">
                        <p><strong>Extracted from: </strong>{file_name}</p>
                        <hr/>
                        <pre>{extracted_content}</pre>
                    </div>
                    """

                    # Combine with original content if we're not replacing it completely
                    if (
                        original_content
                        and content_type in ["html", "empty"]
                        and "No syllabus content available" not in original_content
                    ):
                        full_content = f"{original_content}\n<hr/>\n{full_content}"

                    # Determine what content type to set
                    new_content_type = f"extracted_{extraction['file_type']}"

                    if syllabus_row:
                        # Update the syllabus entry
                        cursor.execute(
                            """
                            UPDATE syllabi SET
                                content = ?,
                                content_type = ?,
                                parsed_content = ?,
                                is_parsed = 1,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                full_content,
                                new_content_type,
                                extracted_content,
                                datetime.now().isoformat(),
                                syllabus_row["id"],
                            ),
                        )
                    else:
                        # Insert a new syllabus entry
                        cursor.execute(
                            """
                            INSERT INTO syllabi
                            (course_id, content, content_type, parsed_content, is_parsed, updated_at)
                            VALUES (?, ?, ?, ?, 1, ?)
                            """,
                            (
                                course_id,
                                full_content,
                                new_content_type,
                                extracted_content,
                                datetime.now().isoformat(),
                            ),
                        )

                    conn.commit()

                    # Add the extracted content to the result
                    result["extracted_content"] = {
                        "success": True,
                        "file_type": extraction["file_type"],
                        "text_preview": (extracted_content[:500] + "...")
                        if len(extracted_content) > 500
                        else extracted_content,
                    }

                except Exception as db_error:
                    conn.rollback()
                    logger.error(
                        f"Database error while storing extracted content: {str(db_error)}"
                    )
                    result["extraction_db_error"] = str(db_error)
                finally:
                    conn.close()
            else:
                # Content extraction failed
                result["extracted_content"] = {
                    "success": False,
                    "error": extraction["error"],
                }

        return result
    except Exception as e:
        logger.error(f"Error in get_syllabus_file: {str(e)}")
        return {
            "success": False,
            "course_id": course_id,
            "error": f"Error searching for syllabus file: {e}",
        }


@mcp.tool()
def get_assignment_details(
    course_id: int, assignment_name: str, include_canvas_data: bool = True
) -> dict[str, Any]:
    """
    Get comprehensive information about a specific assignment by name.
    This function consolidates the functionality of get_course_assignment and get_assignment_by_name.

    Args:
        course_id: Course ID
        assignment_name: Name or partial name of the assignment
        include_canvas_data: Whether to include data from Canvas API if available

    Returns:
        Dictionary with assignment details and related resources
    """
    try:
        if not assignment_name or not course_id:
            return {
                "error": "Missing required parameters: course_id and assignment_name must be provided"
            }

        conn, cursor = db_manager.connect()

        try:
            # Get course information
            cursor.execute(
                """
            SELECT
                c.course_code,
                c.course_name,
                c.canvas_course_id
            FROM
                courses c
            WHERE
                c.id = ?
            """,
                (course_id,),
            )
            course_row = cursor.fetchone()
            if not course_row:
                return {
                    "error": f"Course with ID {course_id} not found",
                    "course_id": course_id,
                }

            course = db_manager.row_to_dict(course_row)

            # Search for the assignment with fuzzy matching
            search_term = f"%{assignment_name}%"
            cursor.execute(
                """
            SELECT
                a.id,
                a.canvas_assignment_id,
                a.title,
                a.description,
                a.assignment_type,
                a.due_date,
                a.available_from,
                a.available_until,
                a.points_possible,
                a.submission_types
            FROM
                assignments a
            WHERE
                a.course_id = ? AND (a.title LIKE ? OR a.description LIKE ?)
            ORDER BY
                CASE WHEN a.title LIKE ? THEN 0 ELSE 1 END,
                a.due_date ASC
            LIMIT 1
            """,
                (course_id, search_term, search_term, search_term),
            )

            assignment_row = cursor.fetchone()
            if not assignment_row:
                return {
                    "error": f"No assignment matching '{assignment_name}' found in course {course_id}",
                    "course_id": course_id,
                    "course_name": course.get("course_name"),
                    "course_code": course.get("course_code"),
                    "assignment_name": assignment_name,
                }

            assignment = db_manager.row_to_dict(assignment_row)

            # Add course information to the result
            result = {
                "course_code": course.get("course_code"),
                "course_name": course.get("course_name"),
                "assignment": assignment,
            }

            # Get related PDF files
            pdf_files = []
            try:
                # Use the global canvas_client instance
                all_pdfs = canvas_client.extract_pdf_files_from_course(course_id)

                # Filter PDFs that might be related to this assignment
                for pdf in all_pdfs:
                    if (
                        "assignment_id" in pdf
                        and str(pdf["assignment_id"])
                        == str(assignment.get("canvas_assignment_id"))
                        or assignment.get("title") in pdf.get("name", "")
                        or assignment_name.lower() in pdf.get("name", "").lower()
                    ):
                        pdf_files.append(
                            {
                                "name": pdf.get("name", ""),
                                "url": pdf.get("url", ""),
                                "source": pdf.get("source", ""),
                            }
                        )
            except Exception as e:
                logger.error(f"Error retrieving PDF files: {str(e)}")
                pdf_files = [{"error": f"Error retrieving PDF files: {str(e)}"}]

            result["pdf_files"] = pdf_files

            # Extract links from assignment description
            if assignment.get("description"):
                try:
                    result["links"] = extract_links_from_content(
                        assignment.get("description", "")
                    )
                except Exception as e:
                    logger.error(f"Error extracting links: {str(e)}")
                    result["links"] = []
                    result["links_error"] = f"Error extracting links: {str(e)}"

            # Get module information where this assignment might be referenced
            try:
                cursor.execute(
                    """
                SELECT
                    m.id,
                    m.name,
                    mi.title,
                    mi.item_type
                FROM
                    modules m
                JOIN
                    module_items mi ON m.id = mi.module_id
                WHERE
                    m.course_id = ? AND mi.content_details LIKE ?
                """,
                    (course_id, f"%{assignment.get('canvas_assignment_id')}%"),
                )

                modules = [db_manager.row_to_dict(row) for row in cursor.fetchall()]
                if modules:
                    result["modules"] = modules
            except Exception as e:
                logger.error(f"Error retrieving module information: {str(e)}")
                result["modules_error"] = (
                    f"Error retrieving module information: {str(e)}"
                )

        except Exception as e:
            logger.error(
                f"Database error while retrieving assignment details: {str(e)}"
            )
            return {
                "error": f"Database error: {str(e)}",
                "course_id": course_id,
                "assignment_name": assignment_name,
            }
        finally:
            conn.close()

        # If requested and the assignment was found, try to get additional info from Canvas API
        if include_canvas_data and "error" not in result:
            try:
                canvas_info = canvas_client.get_assignment_details(
                    course_id, assignment_name
                )
                if canvas_info and canvas_info.get("success", False):
                    # Merge the Canvas data with our database data
                    result["canvas_details"] = canvas_info.get("data", {})
            except ImportError:
                # Canvas API not available, continue with database info
                logger.warning(
                    "Canvas API not available - proceeding with database info only"
                )
                result["canvas_api_status"] = "unavailable"
            except Exception as e:
                logger.error(f"Canvas API error: {str(e)}")
                result["canvas_api_error"] = str(e)

        return result

    except Exception as e:
        logger.error(f"Unexpected error in get_assignment_details: {str(e)}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "course_id": course_id,
            "assignment_name": assignment_name,
        }


@mcp.tool()
def extract_text_from_course_file(
    file_url: str, file_type: str = None
) -> dict[str, Any]:
    """
    Extract text from a file.

    Args:
        file_url: URL of the file
        file_type: Optional file type to override auto-detection ('pdf', 'docx', 'url')

    Returns:
        Dictionary with extracted text and metadata
    """
    try:
        result = extract_text_from_file(file_url, file_type)

        if result["success"]:
            return {
                "success": True,
                "file_url": file_url,
                "file_type": result["file_type"],
                "text_length": len(result["text"]),
                "text": result["text"],
            }
        else:
            return {
                "success": False,
                "file_url": file_url,
                "file_type": result.get("file_type"),
                "error": result.get("error", "Failed to extract text from file"),
            }
    except Exception as e:
        logger.error(f"Error in extract_text_from_course_file: {str(e)}")
        return {
            "success": False,
            "file_url": file_url,
            "error": f"Error extracting text: {str(e)}",
        }


# This function was removed as it duplicates extract_text_from_course_file


# These functions were removed as they duplicate get_assignment_details


@mcp.tool()
def search_course_content(
    query: str, course_id: int | None = None
) -> list[dict[str, Any]]:
    """
    Search for content across courses.

    Args:
        query: Search query
        course_id: Optional course ID to limit search

    Returns:
        List of matching items
    """
    conn, cursor = db_manager.connect()

    # Prepare search parameters
    search_term = f"%{query}%"
    params: list[Any] = []
    course_filter = ""

    if course_id is not None:
        course_filter = "AND c.id = ?"
        params.append(course_id)

    # Search in assignments
    cursor.execute(
        f"""
    SELECT
        c.course_code,
        c.course_name,
        a.title,
        a.description,
        'assignment' AS content_type,
        a.id AS content_id
    FROM
        assignments a
    JOIN
        courses c ON a.course_id = c.id
    WHERE
        (a.title LIKE ? OR a.description LIKE ?)
        {course_filter}
    """,
        [search_term, search_term] + params,
    )

    assignments = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

    # Search in modules
    cursor.execute(
        f"""
    SELECT
        c.course_code,
        c.course_name,
        m.name AS title,
        m.description,
        'module' AS content_type,
        m.id AS content_id
    FROM
        modules m
    JOIN
        courses c ON m.course_id = c.id
    WHERE
        (m.name LIKE ? OR m.description LIKE ?)
        {course_filter}
    """,
        [search_term, search_term] + params,
    )

    modules = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

    # Search in module items
    cursor.execute(
        f"""
    SELECT
        c.course_code,
        c.course_name,
        mi.title,
        mi.content_details AS description,
        'module_item' AS content_type,
        mi.id AS content_id
    FROM
        module_items mi
    JOIN
        modules m ON mi.module_id = m.id
    JOIN
        courses c ON m.course_id = c.id
    WHERE
        (mi.title LIKE ? OR mi.content_details LIKE ?)
        {course_filter}
    """,
        [search_term, search_term] + params,
    )

    module_items = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

    # Search in syllabi
    cursor.execute(
        f"""
    SELECT
        c.course_code,
        c.course_name,
        'Syllabus' AS title,
        s.content AS description,
        'syllabus' AS content_type,
        s.id AS content_id
    FROM
        syllabi s
    JOIN
        courses c ON s.course_id = c.id
    WHERE
        s.content LIKE ?
        {course_filter}
    """,
        [search_term] + params,
    )

    syllabi = [db_manager.row_to_dict(row) for row in cursor.fetchall()]

    # Combine results
    results = assignments + modules + module_items + syllabi

    conn.close()
    return results


if __name__ == "__main__":
    mcp.run()
