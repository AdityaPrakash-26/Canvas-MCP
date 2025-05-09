"""
Database initialization for Canvas MCP.

This module provides functions to initialize the SQLite database for Canvas MCP.
"""

import logging
import sqlite3
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


def create_database(db_path: str | Path) -> None:
    """
    Create and initialize the SQLite database for Canvas MCP.

    Args:
        db_path: Path to the database file
    """
    # Ensure the directory exists
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    cursor = conn.cursor()

    try:
        # Create tables

        # Terms table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY,
            canvas_term_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Courses table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            canvas_course_id INTEGER UNIQUE,
            course_code TEXT,
            course_name TEXT NOT NULL,
            instructor TEXT,
            description TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            term_id INTEGER,
            syllabus_body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE SET NULL
        );
        """)

        # Create index on course_name
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_courses_course_name ON courses(course_name);
        """)

        # Syllabi table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS syllabi (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            content TEXT,
            content_type TEXT DEFAULT 'html',
            parsed_content TEXT,
            is_parsed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id for syllabi
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_syllabi_course_id ON syllabi(course_id);
        """)

        # Assignments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_assignment_id INTEGER,
            name TEXT,
            title TEXT, -- Alias for name
            description TEXT,
            due_at TIMESTAMP,
            due_date TIMESTAMP, -- Alias for due_at
            points_possible REAL,
            assignment_type TEXT,
            submission_types TEXT,
            source_type TEXT,
            available_from TIMESTAMP,
            available_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assignments_course_id ON assignments(course_id);
        """)

        # Create index on due_at
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_assignments_due_at ON assignments(due_at);
        """)

        # Add unique constraint on canvas_assignment_id and course_id
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_assignments_canvas_course ON assignments (canvas_assignment_id, course_id);
        """)

        # Modules table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_module_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            position INTEGER,
            unlock_date TIMESTAMP,
            require_sequential_progress BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_modules_course_id ON modules(course_id);
        """)

        # Add unique constraint on canvas_module_id and course_id
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_canvas_course ON modules (canvas_module_id, course_id);
        """)

        # Module items table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_items (
            id INTEGER PRIMARY KEY,
            module_id INTEGER NOT NULL,
            canvas_module_item_id INTEGER,
            canvas_item_id INTEGER,
            title TEXT NOT NULL,
            position INTEGER,
            content_type TEXT,
            type TEXT,
            item_type TEXT,
            content_id INTEGER,
            url TEXT,
            page_url TEXT,
            content_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
        );
        """)

        # Create index on module_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_module_items_module_id ON module_items(module_id);
        """)

        # Add unique constraint on canvas_item_id and module_id
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_module_items_canvas_module ON module_items (canvas_item_id, module_id);
        """)

        # Announcements table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_announcement_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            posted_by TEXT,
            posted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_announcements_course_id ON announcements(course_id);
        """)

        # Create index on posted_at
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_announcements_posted_at ON announcements(posted_at);
        """)

        # Add unique constraint on canvas_announcement_id and course_id
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_announcements_canvas_course ON announcements (canvas_announcement_id, course_id);
        """)

        # Conversations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_conversation_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            posted_by TEXT,
            posted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_course_id ON conversations(course_id);
        """)

        # Create index on posted_at
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_posted_at ON conversations(posted_at);
        """)

        # Add unique constraint on canvas_conversation_id (assuming it's globally unique)
        # If not globally unique, might need combination with course_id or other fields.
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_canvas_id ON conversations (canvas_conversation_id);
        """)

        # Calendar events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            canvas_event_id INTEGER,
            title TEXT,
            description TEXT,
            start_at TIMESTAMP,
            end_at TIMESTAMP,
            event_date TIMESTAMP,
            event_type TEXT,
            source_type TEXT,
            source_id INTEGER,
            location_name TEXT,
            location_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)

        # Create index on course_id
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_course_id ON calendar_events(course_id);
        """)

        # Add unique constraint based on source_type and source_id
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_events_source ON calendar_events (source_type, source_id);
        """)

        # Commit the changes
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
        print(f"Database initialized at {db_path}")

    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        # Close the connection
        conn.close()


if __name__ == "__main__":
    # Default database path
    default_db_path = Path(__file__).parent.parent.parent / "data" / "canvas_mcp.db"
    create_database(default_db_path)
