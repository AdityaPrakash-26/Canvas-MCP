"""
Canvas API client for synchronizing data with the local database.
"""
import os
import sqlite3
import re
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv

from canvas_mcp.utils.pdf_extractor import extract_text_from_pdf

# Make Canvas available for patching in tests
try:
    from canvasapi import Canvas
except ImportError:
    # Create a dummy Canvas class for tests to patch
    class Canvas:
        def __init__(self, api_url, api_key):
            self.api_url = api_url
            self.api_key = api_key


class CanvasClient:
    """
    Client for interacting with the Canvas LMS API and syncing data to the local database.
    """
    
    def extract_pdf_links(self, content: str | None) -> list[str]:
        """
        Extract PDF links from content.
        
        Args:
            content: HTML content to parse
            
        Returns:
            List of PDF URLs
        """
        if not content or not isinstance(content, str):
            return []
            
        pdf_links = []
        try:
            # Find <a> tags with href attributes pointing to PDFs
            a_tag_pattern = re.compile(r'<a\s+[^>]*href="([^"]*\.pdf[^"]*)"[^>]*>', re.IGNORECASE)
            for match in a_tag_pattern.finditer(content):
                url = match.group(1)
                if url:
                    pdf_links.append(url)
                    
            # Also look for embedded PDFs
            embed_pattern = re.compile(r'<embed\s+[^>]*src="([^"]*\.pdf[^"]*)"[^>]*>', re.IGNORECASE)
            for match in embed_pattern.finditer(content):
                url = match.group(1)
                if url:
                    pdf_links.append(url)
                    
            # Look for iframes with PDF sources
            iframe_pattern = re.compile(r'<iframe\s+[^>]*src="([^"]*\.pdf[^"]*)"[^>]*>', re.IGNORECASE)
            for match in iframe_pattern.finditer(content):
                url = match.group(1)
                if url:
                    pdf_links.append(url)
            
            # Look for links that look like Canvas file downloads
            canvas_file_pattern = re.compile(r'<a\s+[^>]*href="([^"]*\/files\/\d+\/download[^"]*)"[^>]*>', re.IGNORECASE)
            for match in canvas_file_pattern.finditer(content):
                url = match.group(1)
                if url and ('.pdf' in url.lower() or 'pdf' in url.lower()):
                    pdf_links.append(url)
                    
            # Direct PDF URLs in the text
            if not pdf_links:
                url_pattern = re.compile(r'https?://[^\s"\'<>]+\.pdf', re.IGNORECASE)
                for match in url_pattern.finditer(content):
                    url = match.group(0)
                    pdf_links.append(url)
                
            # Look for Canvas file download URLs
            if not pdf_links:
                canvas_url_pattern = re.compile(r'https?://[^\s"\'<>]+/files/\d+/download', re.IGNORECASE)
                for match in canvas_url_pattern.finditer(content):
                    url = match.group(0)
                    if 'pdf' in url.lower():
                        pdf_links.append(url)
                    
        except Exception as e:
            print(f"Error extracting PDF links: {e}")
            # Fall back to simple string search
            if ".pdf" in content.lower():
                # Just extract the link without parsing
                lower_content = content.lower()
                pdf_index = lower_content.find('.pdf')
                if pdf_index > 0:
                    # Look backwards for http
                    start = lower_content.rfind('http', 0, pdf_index)
                    if start >= 0:
                        # Look forward for the end of URL (space, quote, etc.)
                        end = pdf_index + 4  # Include .pdf
                        for i in range(end, min(end + 100, len(content))):
                            if i < len(content) and content[i] in [' ', '"', "'", '>', '<']:
                                end = i
                                break
                        url = content[start:end]
                        pdf_links.append(url)
        
        # Also check for Canvas files URLs
        if '/files/' in content and 'download' in content:
            try:
                canvas_file_pattern = re.compile(r'(/files/\d+/download)')
                for match in canvas_file_pattern.finditer(content):
                    file_path = match.group(1)
                    # Build a complete URL if API URL is available
                    base_url = self.api_url if hasattr(self, 'api_url') and self.api_url else "https://canvas.instructure.com"
                    url = f"{base_url}{file_path}"
                    pdf_links.append(url)
            except Exception as e:
                print(f"Error processing Canvas files URL: {e}")
                
        return pdf_links

    @staticmethod
    def extract_links(content: str | None) -> list[dict[str, str]]:
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
            # Simple regex pattern for links
            import re
            
            # Find <a> tags with href attributes
            a_tag_pattern = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
            for match in a_tag_pattern.finditer(content):
                url = match.group(1)
                text = re.sub(r'<[^>]*>', '', match.group(2)).strip()  # Remove nested HTML tags
                if url:
                    links.append({"url": url, "text": text or url})
                    
            # If no <a> tags found, look for bare URLs
            if not links:
                url_pattern = re.compile(r'https?://\S+')
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

    @staticmethod
    def detect_content_type(content: str | None) -> str:
        """
        Detect the content type from the given content string.
        
        Args:
            content: The content string to analyze
            
        Returns:
            String indicating the content type ('html', 'pdf_link', 'external_link', 'json', etc.)
        """
        if not content or not isinstance(content, str):
            return "html"  # Default for empty content
            
        content_lower = content.lower()
        
        # Check for PDF links
        if ".pdf" in content_lower and ("<a href=" in content_lower or "src=" in content_lower):
            return "pdf_link"
            
        # Check for external links (simple URLs with minimal formatting)
        if ("http://" in content or "https://" in content) and len(content.strip()) < 1000 and content.count(" ") < 10:
            return "external_link"
            
        # Check for JSON content
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                import json
                json.loads(content)
                return "json"
            except (json.JSONDecodeError, ValueError):
                pass  # Not valid JSON
                
        # Check for empty HTML
        if content.strip() in ['<p></p>', '<div></div>', '']:
            return "empty"
            
        # Default to HTML
        return "html"

    def __init__(self, db_path: str, api_key: str | None = None, api_url: str | None = None):
        """
        Initialize the Canvas client.

        Args:
            db_path: Path to the SQLite database
            api_key: Canvas API key (if None, will look for CANVAS_API_KEY in environment)
            api_url: Canvas API URL (if None, will use default Canvas URL)
        """
        # Load environment variables if api_key not provided
        if api_key is None:
            load_dotenv()
            api_key = os.environ.get("CANVAS_API_KEY")

        self.api_key = api_key
        self.api_url = api_url or "https://canvas.instructure.com"
        self.db_path = db_path

        # Import canvasapi here to avoid making it a hard dependency
        try:
            from canvasapi import Canvas
            self.canvas = Canvas(self.api_url, self.api_key)
        except ImportError:
            self.canvas = None
            print("Warning: canvasapi module not found. Some features will be limited.")

    def connect_db(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        Connect to the SQLite database.

        Returns:
            Tuple of (connection, cursor)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    def sync_courses(self, user_id: str | None = None, term_id: int | None = None) -> list[int]:
        """
        Synchronize course data from Canvas to the local database.

        Args:
            user_id: Optional user ID to filter courses
            term_id: Optional term ID to filter courses
                     (use -1 to select only the most recent term)

        Returns:
            List of local course IDs that were synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Get current user if not specified
        if user_id is None:
            user = self.canvas.get_current_user()
            user_id = str(user.id)
        else:
            user = self.canvas.get_current_user()  # Always use current user for authentication

        # Get courses from Canvas directly using the user object
        # This fixes the authentication issue reported in integration testing
        courses = list(user.get_courses())

        # Apply term filtering if requested
        if term_id is not None:
            if term_id == -1:
                # Get the most recent term (maximum term_id)
                term_ids = [getattr(course, 'enrollment_term_id', 0) for course in courses]
                if term_ids:
                    max_term_id = max(filter(lambda x: x is not None, term_ids), default=None)
                    if max_term_id is not None:
                        print(f"Filtering to only include the most recent term (ID: {max_term_id})")
                        courses = [
                            course for course in courses
                            if getattr(course, 'enrollment_term_id', None) == max_term_id
                        ]
            else:
                # Filter for the specific term requested
                courses = [
                    course for course in courses
                    if getattr(course, 'enrollment_term_id', None) == term_id
                ]

        # Connect to database
        conn, cursor = self.connect_db()

        course_ids = []
        for course in courses:
            # Check if user has opted out of this course
            cursor.execute(
                "SELECT indexing_opt_out FROM user_courses WHERE user_id = ? AND course_id = ?",
                (user_id, course.id)
            )
            row = cursor.fetchone()
            if row and row["indexing_opt_out"]:
                print(f"Skipping opted-out course: {course.name}")
                continue

            # Get detailed course information
            detailed_course = self.canvas.get_course(course.id)

            # Properly convert all MagicMock attributes to appropriate types for SQLite
            course_id = int(course.id) if hasattr(course, "id") else None
            course_code = str(getattr(course, "course_code", "")) if getattr(course, "course_code", None) is not None else ""
            course_name = str(course.name) if hasattr(course, "name") else ""
            instructor = str(getattr(detailed_course, "teacher", "")) if getattr(detailed_course, "teacher", None) is not None else None
            description = str(getattr(detailed_course, "description", "")) if getattr(detailed_course, "description", None) is not None else None
            start_date = str(getattr(detailed_course, "start_at", "")) if getattr(detailed_course, "start_at", None) is not None else None
            end_date = str(getattr(detailed_course, "end_at", "")) if getattr(detailed_course, "end_at", None) is not None else None

            # Check if course exists
            cursor.execute(
                "SELECT id FROM courses WHERE canvas_course_id = ?",
                (course_id,)
            )
            existing_course = cursor.fetchone()

            if existing_course:
                # Update existing course
                cursor.execute(
                    """
                    UPDATE courses SET
                        course_code = ?,
                        course_name = ?,
                        instructor = ?,
                        description = ?,
                        start_date = ?,
                        end_date = ?,
                        updated_at = ?
                    WHERE canvas_course_id = ?
                    """,
                    (
                        course_code,
                        course_name,
                        instructor,
                        description,
                        start_date,
                        end_date,
                        datetime.now().isoformat(),
                        course_id
                    )
                )
                local_course_id = existing_course["id"]
            else:
                # Insert new course
                cursor.execute(
                    """
                    INSERT INTO courses (
                        canvas_course_id, course_code, course_name,
                        instructor, description, start_date, end_date, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        course_code,
                        course_name,
                        instructor,
                        description,
                        start_date,
                        end_date,
                        datetime.now().isoformat()
                    )
                )
                local_course_id = cursor.lastrowid
            course_ids.append(local_course_id)

        # Store or update syllabus
            # Check if syllabus body is available
            syllabus_body = getattr(detailed_course, "syllabus_body", None)
            
            # Always create a syllabus entry, even if empty
            content = syllabus_body if syllabus_body else "<p>No syllabus content available</p>"
            content_type = self.detect_content_type(content) if syllabus_body else "empty"
            parsed_content = None
            is_parsed = False

            # If it's a PDF link, try to extract the content from the PDF
            if content_type == "pdf_link":
                pdf_links = self.extract_pdf_links(content)

                if pdf_links:
                    # Try to extract text from the first PDF link
                    pdf_url = pdf_links[0]

                    # Try to extract the PDF content
                    try:
                        pdf_text = extract_text_from_pdf(pdf_url)
                        if pdf_text:
                            parsed_content = pdf_text
                            is_parsed = True
                            print(f"Successfully extracted PDF content for course: {course_name}")
                        else:
                            print(f"Failed to extract content from PDF for course: {course_name}")
                    except Exception as e:
                        print(f"Error extracting PDF content for course {course_name}: {e}")
                
            # Check if syllabus exists
            cursor.execute(
                "SELECT id FROM syllabi WHERE course_id = ?",
                (local_course_id,)
            )
            existing_syllabus = cursor.fetchone()

            if existing_syllabus:
                # Update existing syllabus
                if is_parsed and parsed_content:
                    cursor.execute(
                        """
                        UPDATE syllabi SET
                            content = ?,
                            content_type = ?,
                            parsed_content = ?,
                            is_parsed = ?,
                            updated_at = ?
                        WHERE course_id = ?
                        """,
                        (content, content_type, parsed_content, is_parsed,
                         datetime.now().isoformat(), local_course_id)
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE syllabi SET
                            content = ?,
                            content_type = ?,
                            updated_at = ?
                        WHERE course_id = ?
                        """,
                        (content, content_type, datetime.now().isoformat(), local_course_id)
                    )
            else:
                # Insert new syllabus
                if is_parsed and parsed_content:
                    cursor.execute(
                        """
                        INSERT INTO syllabi
                        (course_id, content, content_type, parsed_content, is_parsed, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (local_course_id, content, content_type, parsed_content, is_parsed,
                         datetime.now().isoformat())
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO syllabi (course_id, content, content_type, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (local_course_id, content, content_type, datetime.now().isoformat())
                    )

        conn.commit()
        conn.close()

        return course_ids

    def sync_assignments(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize assignment data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of assignments synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        assignment_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get assignments for the course
                assignments = canvas_course.get_assignments()

                for assignment in assignments:
                    # Convert submission_types to string
                    submission_types = ",".join(getattr(assignment, "submission_types", []))

                    # Check if assignment exists
                    cursor.execute(
                        "SELECT id FROM assignments WHERE course_id = ? AND canvas_assignment_id = ?",
                        (local_course_id, assignment.id)
                    )
                    existing_assignment = cursor.fetchone()

                    if existing_assignment:
                        # Update existing assignment
                        cursor.execute(
                            """
                            UPDATE assignments SET
                                title = ?,
                                description = ?,
                                assignment_type = ?,
                                due_date = ?,
                                available_from = ?,
                                available_until = ?,
                                points_possible = ?,
                                submission_types = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                assignment.name,
                                getattr(assignment, "description", None),
                                self._get_assignment_type(assignment),
                                getattr(assignment, "due_at", None),
                                getattr(assignment, "unlock_at", None),
                                getattr(assignment, "lock_at", None),
                                getattr(assignment, "points_possible", None),
                                submission_types,
                                datetime.now().isoformat(),
                                existing_assignment["id"]
                            )
                        )
                        assignment_id = existing_assignment["id"]
                    else:
                        # Insert new assignment
                        cursor.execute(
                            """
                            INSERT INTO assignments (
                                course_id, canvas_assignment_id, title, description,
                                assignment_type, due_date, available_from, available_until,
                                points_possible, submission_types, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                assignment.id,
                                assignment.name,
                                getattr(assignment, "description", None),
                                self._get_assignment_type(assignment),
                                getattr(assignment, "due_at", None),
                                getattr(assignment, "unlock_at", None),
                                getattr(assignment, "lock_at", None),
                                getattr(assignment, "points_possible", None),
                                submission_types,
                                datetime.now().isoformat()
                            )
                        )
                        assignment_id = cursor.lastrowid
                    assignment_count += 1

                    # Add to calendar events
                    if hasattr(assignment, "due_at") and assignment.due_at:
                        # Check if calendar event exists
                        cursor.execute(
                            """
                            SELECT id FROM calendar_events
                            WHERE course_id = ? AND source_type = ? AND source_id = ?
                            """,
                            (local_course_id, "assignment", assignment_id)
                        )
                        existing_event = cursor.fetchone()

                        if existing_event:
                            # Update existing event
                            cursor.execute(
                                """
                                UPDATE calendar_events SET
                                    title = ?,
                                    description = ?,
                                    event_date = ?,
                                    updated_at = ?
                                WHERE id = ?
                                """,
                                (
                                    assignment.name,
                                    f"Due date for assignment: {assignment.name}",
                                    assignment.due_at,
                                    datetime.now().isoformat(),
                                    existing_event["id"]
                                )
                            )
                        else:
                            # Insert new event
                            cursor.execute(
                                """
                                INSERT INTO calendar_events (
                                    course_id, title, description, event_type,
                                    source_type, source_id, event_date, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    local_course_id,
                                    assignment.name,
                                    f"Due date for assignment: {assignment.name}",
                                    self._get_assignment_type(assignment),
                                    "assignment",
                                    assignment_id,
                                    assignment.due_at,
                                    datetime.now().isoformat()
                                )
                            )
            except Exception as e:
                print(f"Error syncing assignments for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return assignment_count

    def sync_modules(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize module data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of modules synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        module_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get modules for the course
                modules = canvas_course.get_modules()

                for module in modules:
                    # Convert boolean attribute to integer for SQLite
                    require_sequential_progress = 1 if getattr(module, "require_sequential_progress", False) else 0

                    # Properly convert all MagicMock attributes to appropriate types for SQLite
                    module_id = int(module.id) if hasattr(module, "id") else None
                    module_name = str(module.name) if hasattr(module, "name") else ""
                    module_description = str(getattr(module, "description", "")) if getattr(module, "description", None) is not None else None
                    module_unlock_at = str(getattr(module, "unlock_at", "")) if getattr(module, "unlock_at", None) is not None else None
                    module_position = int(getattr(module, "position", 0)) if getattr(module, "position", None) is not None else None

                    # Check if module exists
                    cursor.execute(
                        "SELECT id FROM modules WHERE course_id = ? AND canvas_module_id = ?",
                        (local_course_id, module_id)
                    )
                    existing_module = cursor.fetchone()

                    if existing_module:
                        # Update existing module
                        cursor.execute(
                            """
                            UPDATE modules SET
                                name = ?,
                                description = ?,
                                unlock_date = ?,
                                position = ?,
                                require_sequential_progress = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                module_name,
                                module_description,
                                module_unlock_at,
                                module_position,
                                require_sequential_progress,
                                datetime.now().isoformat(),
                                existing_module["id"]
                            )
                        )
                        local_module_id = existing_module["id"]
                    else:
                        # Insert new module
                        cursor.execute(
                            """
                            INSERT INTO modules (
                                course_id, canvas_module_id, name, description,
                                unlock_date, position, require_sequential_progress, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                module_id,
                                module_name,
                                module_description,
                                module_unlock_at,
                                module_position,
                                require_sequential_progress,
                                datetime.now().isoformat()
                            )
                        )
                        local_module_id = cursor.lastrowid
                    module_count += 1

                    # Get module items
                    try:
                        items = module.get_module_items()
                        for item in items:
                            # Properly convert all MagicMock attributes to appropriate types for SQLite
                            item_id = int(item.id) if hasattr(item, "id") else None
                            item_title = str(getattr(item, "title", "")) if getattr(item, "title", None) is not None else None
                            item_type = str(getattr(item, "type", "")) if getattr(item, "type", None) is not None else None
                            item_position = int(getattr(item, "position", 0)) if getattr(item, "position", None) is not None else None
                            item_url = str(getattr(item, "external_url", "")) if getattr(item, "external_url", None) is not None else None
                            item_page_url = str(getattr(item, "page_url", "")) if getattr(item, "page_url", None) is not None else None

                            # Convert the content_details to a string representation
                            content_details = str(item) if hasattr(item, "__dict__") else None

                            # Check if module item exists
                            cursor.execute(
                                "SELECT id FROM module_items WHERE module_id = ? AND canvas_item_id = ?",
                                (local_module_id, item_id)
                            )
                            existing_item = cursor.fetchone()

                            if existing_item:
                                # Update existing item
                                cursor.execute(
                                    """
                                    UPDATE module_items SET
                                        title = ?,
                                        item_type = ?,
                                        position = ?,
                                        url = ?,
                                        page_url = ?,
                                        content_details = ?,
                                        updated_at = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        item_title,
                                        item_type,
                                        item_position,
                                        item_url,
                                        item_page_url,
                                        content_details,
                                        datetime.now().isoformat(),
                                        existing_item["id"]
                                    )
                                )
                            else:
                                # Insert new item
                                cursor.execute(
                                    """
                                    INSERT INTO module_items (
                                        module_id, canvas_item_id, title, item_type,
                                        position, url, page_url, content_details, updated_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        local_module_id,
                                        item_id,
                                        item_title,
                                        item_type,
                                        item_position,
                                        item_url,
                                        item_page_url,
                                        content_details,
                                        datetime.now().isoformat()
                                    )
                                )
                    except Exception as e:
                        print(f"Error syncing module items for module {module.id}: {e}")
            except Exception as e:
                print(f"Error syncing modules for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return module_count

    def extract_pdf_files_from_course(self, local_course_id: int) -> list[dict[str, Any]]:
        """
        Extract PDF files from a Canvas course.
        
        Args:
            local_course_id: The local database ID for the course
            
        Returns:
            List of dictionaries with PDF file information, including URLs
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")
            
        # Get Canvas course ID from local course ID
        conn, cursor = self.connect_db()
        cursor.execute(
            "SELECT canvas_course_id FROM courses WHERE id = ?",
            (local_course_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print(f"Course with ID {local_course_id} not found in database")
            return []
            
        canvas_course_id = row["canvas_course_id"]
        
        # Get course from Canvas
        canvas_course = self.canvas.get_course(canvas_course_id)
        pdf_files = []
        
        # Get files from the course
        try:
            files = canvas_course.get_files()
            for file in files:
                # Check if file is a PDF by various attributes or filename extension
                is_pdf = False
                
                # Check content-type or content_type attribute
                if hasattr(file, "content-type") and "pdf" in getattr(file, "content-type").lower():
                    is_pdf = True
                elif hasattr(file, "content_type") and "pdf" in getattr(file, "content_type", "").lower():
                    is_pdf = True
                
                # Check by filename extension as a fallback
                elif hasattr(file, "filename") and str(file.filename).lower().endswith(".pdf"):
                    is_pdf = True
                elif hasattr(file, "display_name") and str(file.display_name).lower().endswith(".pdf"):
                    is_pdf = True
                
                # If it's a PDF, add it to the list
                if is_pdf:
                    file_name = (
                        file.display_name if hasattr(file, "display_name") else 
                        (file.filename if hasattr(file, "filename") else "Unnamed PDF")
                    )
                    pdf_files.append({
                        "name": file_name,
                        "url": file.url if hasattr(file, "url") else None,
                        "id": file.id if hasattr(file, "id") else None,
                        "source": "files"
                    })
        except Exception as e:
            print(f"Error getting files for course {canvas_course_id}: {e}")
            
        # Get files from assignments
        try:
            assignments = canvas_course.get_assignments()
            for assignment in assignments:
                # Check assignment description for PDF links
                if hasattr(assignment, "description") and assignment.description:
                    # First, check for PDF links in the description
                    pdf_links = self.extract_pdf_links(assignment.description)
                    
                    # Also check for Canvas file URLs in the description
                    if '/files/' in assignment.description:
                        # Extract file IDs from the description
                        try:
                            import re
                            file_id_pattern = re.compile(r'/files/(\d+)')
                            file_ids = file_id_pattern.findall(assignment.description)
                            
                            # Check each file to see if it's a PDF
                            for file_id in file_ids:
                                try:
                                    file = canvas_course.get_file(file_id)
                                    # Check if it's a PDF by name
                                    if (hasattr(file, "filename") and str(file.filename).lower().endswith(".pdf")) or \
                                       (hasattr(file, "display_name") and str(file.display_name).lower().endswith(".pdf")):
                                        file_name = (
                                            file.display_name if hasattr(file, "display_name") else 
                                            (file.filename if hasattr(file, "filename") else f"File from {assignment.name}")
                                        )
                                        pdf_files.append({
                                            "name": file_name,
                                            "url": file.url if hasattr(file, "url") else None,
                                            "id": file.id,
                                            "source": "assignment_file_reference",
                                            "assignment_id": assignment.id,
                                            "assignment_name": assignment.name
                                        })
                                except Exception as e:
                                    print(f"Error getting file {file_id} referenced in assignment {assignment.id}: {e}")
                        except Exception as e:
                            print(f"Error parsing file IDs from assignment {assignment.id}: {e}")
                    
                    # Add any direct PDF links found
                    for link in pdf_links:
                        pdf_files.append({
                            "name": f"PDF link from assignment: {assignment.name}",
                            "url": link,
                            "id": None,
                            "source": "assignment_link",
                            "assignment_id": assignment.id,
                            "assignment_name": assignment.name
                        })
                        
                # Check for attachments
                if hasattr(assignment, "attachments"):
                    for attachment in assignment.attachments:
                        # Check if attachment is a PDF
                        is_pdf = False
                        
                        # Check content_type attribute
                        if hasattr(attachment, "content_type") and "pdf" in getattr(attachment, "content_type", "").lower():
                            is_pdf = True
                        
                        # Check by filename extension as a fallback
                        elif hasattr(attachment, "filename") and str(attachment.filename).lower().endswith(".pdf"):
                            is_pdf = True
                        elif hasattr(attachment, "display_name") and str(attachment.display_name).lower().endswith(".pdf"):
                            is_pdf = True
                        
                        # If it's a PDF, add it to the list
                        if is_pdf:
                            att_name = (
                                attachment.display_name if hasattr(attachment, "display_name") else 
                                (attachment.filename if hasattr(attachment, "filename") else f"Attachment from {assignment.name}")
                            )
                            pdf_files.append({
                                "name": att_name,
                                "url": attachment.url if hasattr(attachment, "url") else None,
                                "id": attachment.id if hasattr(attachment, "id") else None,
                                "source": "assignment_attachment",
                                "assignment_id": assignment.id
                            })
        except Exception as e:
            print(f"Error getting assignments for course {canvas_course_id}: {e}")
            
        # Get files from modules
        try:
            modules = canvas_course.get_modules()
            for module in modules:
                try:
                    items = module.get_module_items()
                    for item in items:
                        # Check if item is a file
                        if hasattr(item, "type") and item.type == "File":
                            # Get the file
                            file_id = getattr(item, "content_id", None)
                            if file_id:
                                try:
                                    file = canvas_course.get_file(file_id)
                                    # Check if file is a PDF
                                    is_pdf = False
                                    
                                    # Check content-type or content_type attribute
                                    if hasattr(file, "content_type") and "pdf" in getattr(file, "content_type", "").lower():
                                        is_pdf = True
                                    elif hasattr(file, "content-type") and "pdf" in getattr(file, "content-type", "").lower():
                                        is_pdf = True
                                    
                                    # Check by filename extension as a fallback
                                    elif hasattr(file, "filename") and str(file.filename).lower().endswith(".pdf"):
                                        is_pdf = True
                                    elif hasattr(file, "display_name") and str(file.display_name).lower().endswith(".pdf"):
                                        is_pdf = True
                                    
                                    # If it's a PDF, add it to the list
                                    if is_pdf:
                                        file_name = (
                                            file.display_name if hasattr(file, "display_name") else 
                                            (file.filename if hasattr(file, "filename") else f"File from {module.name}")
                                        )
                                        pdf_files.append({
                                            "name": file_name,
                                            "url": file.url if hasattr(file, "url") else None,
                                            "id": file.id if hasattr(file, "id") else None,
                                            "source": "module_file",
                                            "module_id": module.id,
                                            "module_name": module.name
                                        })
                                except Exception as e:
                                    print(f"Error getting file {file_id} for module {module.id}: {e}")
                except Exception as e:
                    print(f"Error getting items for module {module.id}: {e}")
        except Exception as e:
            print(f"Error getting modules for course {canvas_course_id}: {e}")
            
        return pdf_files

    def sync_announcements(self, course_ids: list[int] | None = None) -> int:
        """
        Synchronize announcement data from Canvas to the local database.

        Args:
            course_ids: Optional list of local course IDs to sync

        Returns:
            Number of announcements synced
        """
        if self.canvas is None:
            raise ImportError("canvasapi module is required for this operation")

        # Connect to database
        conn, cursor = self.connect_db()

        # Get all courses if not specified
        if course_ids is None:
            cursor.execute("SELECT id, canvas_course_id FROM courses")
            courses = cursor.fetchall()
        else:
            courses = []
            for course_id in course_ids:
                cursor.execute(
                    "SELECT id, canvas_course_id FROM courses WHERE id = ?",
                    (course_id,)
                )
                course = cursor.fetchone()
                if course:
                    courses.append(course)

        announcement_count = 0
        for course in courses:
            try:
                local_course_id = course["id"]
                canvas_course_id = course["canvas_course_id"]

                # Get course from Canvas
                canvas_course = self.canvas.get_course(canvas_course_id)

                # Get announcements for the course
                announcements = canvas_course.get_discussion_topics(only_announcements=True)

                for announcement in announcements:
                    # Check if announcement exists
                    cursor.execute(
                        "SELECT id FROM announcements WHERE course_id = ? AND canvas_announcement_id = ?",
                        (local_course_id, announcement.id)
                    )
                    existing_announcement = cursor.fetchone()

                    if existing_announcement:
                        # Update existing announcement
                        cursor.execute(
                            """
                            UPDATE announcements SET
                                title = ?,
                                content = ?,
                                posted_by = ?,
                                posted_at = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                announcement.title,
                                getattr(announcement, "message", None),
                                getattr(announcement, "author_name", None),
                                getattr(announcement, "posted_at", None),
                                datetime.now().isoformat(),
                                existing_announcement["id"]
                            )
                        )
                    else:
                        # Insert new announcement
                        cursor.execute(
                            """
                            INSERT INTO announcements (
                                course_id, canvas_announcement_id, title, content,
                                posted_by, posted_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                local_course_id,
                                announcement.id,
                                announcement.title,
                                getattr(announcement, "message", None),
                                getattr(announcement, "author_name", None),
                                getattr(announcement, "posted_at", None),
                                datetime.now().isoformat()
                            )
                        )

                    announcement_count += 1
            except Exception as e:
                print(f"Error syncing announcements for course {canvas_course_id}: {e}")

        conn.commit()
        conn.close()

        return announcement_count

    def parse_existing_pdf_syllabi(self) -> int:
        """
        Parse existing PDF syllabi that haven't been parsed yet.
        
        Returns:
            Number of successfully parsed syllabi
        """
        if not extract_text_from_pdf:
            print("PDF extraction not available. Install pdfplumber and requests packages.")
            return 0
            
        conn, cursor = self.connect_db()
        
        # Find syllabi of type pdf_link that haven't been parsed
        cursor.execute("""
            SELECT s.id, s.course_id, s.content, c.course_name
            FROM syllabi s
            JOIN courses c ON s.course_id = c.id
            WHERE s.content_type = 'pdf_link' AND (s.is_parsed = 0 OR s.is_parsed IS NULL)
        """)
        
        pdf_syllabi = cursor.fetchall()
        parsed_count = 0
        
        for syllabus in pdf_syllabi:
            syllabus_id = syllabus[0]
            content = syllabus[2]
            course_name = syllabus[3]
            
            # Extract PDF links from the content
            pdf_links = self.extract_pdf_links(content)
            
            if not pdf_links:
                continue
                
            # Try to extract text from the first PDF link
            try:
                pdf_text = extract_text_from_pdf(pdf_links[0])
                
                if pdf_text:
                    # Update the syllabus with the parsed content
                    cursor.execute("""
                        UPDATE syllabi SET
                            parsed_content = ?,
                            is_parsed = 1,
                            updated_at = ?
                        WHERE id = ?
                    """, (pdf_text, datetime.now().isoformat(), syllabus_id))
                    
                    parsed_count += 1
                    print(f"Successfully parsed PDF syllabus for course: {course_name}")
            except Exception as e:
                print(f"Error parsing PDF syllabus for course {course_name}: {e}")
                
        conn.commit()
        conn.close()
        
        return parsed_count

    def sync_all(self, user_id: str | None = None, term_id: int | None = -1) -> dict[str, int]:
        """
        Synchronize all data from Canvas to the local database.

        Args:
            user_id: Optional user ID to filter courses
            term_id: Optional term ID to filter courses
                     (default is -1, which only selects the most recent term)

        Returns:
            Dictionary with counts of synced items
        """
        # First sync courses
        course_ids = self.sync_courses(user_id, term_id)

        # Then sync other data
        assignment_count = self.sync_assignments(course_ids)
        module_count = self.sync_modules(course_ids)
        announcement_count = self.sync_announcements(course_ids)

        # Parse any remaining PDF syllabi
        pdf_count = 0
        try:
            pdf_count = self.parse_existing_pdf_syllabi()
        except Exception as e:
            print(f"Error parsing PDF syllabi: {e}")
            
        return {
            "courses": len(course_ids),
            "assignments": assignment_count,
            "modules": module_count,
            "announcements": announcement_count,
            "pdf_syllabi_parsed": pdf_count
        }

    def _get_assignment_type(self, assignment: Any) -> str:
        """
        Determine the type of an assignment.

        Args:
            assignment: Canvas assignment object

        Returns:
            Assignment type string
        """
        if not hasattr(assignment, "submission_types"):
            return "assignment"

        if "online_quiz" in assignment.submission_types:
            return "quiz"
        elif "discussion_topic" in assignment.submission_types:
            return "discussion"
        elif any(t in assignment.name.lower() for t in ["exam", "midterm", "final"]):
            return "exam"
        else:
            return "assignment"
