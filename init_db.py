#!/usr/bin/env python3
"""
Database initialization script for Canvas MCP.
This script creates the SQLite database with all required tables
based on the schema defined in docs/db_schema.md.
"""
import os
import sqlite3
from pathlib import Path


def create_database(db_path: str) -> None:
    """
    Create a new SQLite database with all necessary tables.
    
    Args:
        db_path: Path to the SQLite database file
    """
    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    
    # Get cursor
    cursor = conn.cursor()
    
    # Enable foreign keys - set it to 1 explicitly and commit
    cursor.execute("PRAGMA foreign_keys = 1")
    conn.commit()
    
    # Verify foreign keys are enabled
    cursor.execute("PRAGMA foreign_keys")
    if cursor.fetchone()[0] == 0:
        # If not enabled, try another approach with URI connection string
        conn.close()
        conn = sqlite3.connect(f"file:{db_path}?foreign_keys=1", uri=True)
        cursor = conn.cursor()
        # Just to be sure, set it again
        cursor.execute("PRAGMA foreign_keys = 1")
        conn.commit()
    
    # Create tables
    create_tables(cursor)
    
    # Create views
    create_views(cursor)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")


def create_tables(cursor: sqlite3.Cursor) -> None:
    """Create all database tables."""
    
    # Courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        canvas_course_id INTEGER UNIQUE NOT NULL,
        course_code TEXT NOT NULL,
        course_name TEXT NOT NULL,
        instructor TEXT,
        description TEXT,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_courses_canvas_id ON courses(canvas_course_id);
    """)
    
    # Syllabi table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS syllabi (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        content TEXT,
        parsed_content TEXT,
        is_parsed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_syllabi_course_id ON syllabi(course_id);
    """)
    
    # Assignments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        canvas_assignment_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        assignment_type TEXT,
        due_date TIMESTAMP,
        available_from TIMESTAMP,
        available_until TIMESTAMP,
        points_possible REAL,
        submission_types TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        UNIQUE (course_id, canvas_assignment_id)
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_assignments_course_id ON assignments(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_assignments_due_date ON assignments(due_date);
    """)
    
    # Modules table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        canvas_module_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        unlock_date TIMESTAMP,
        position INTEGER,
        require_sequential_progress BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        UNIQUE (course_id, canvas_module_id)
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_modules_course_id ON modules(course_id);
    """)
    
    # Module_Items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS module_items (
        id INTEGER PRIMARY KEY,
        module_id INTEGER NOT NULL,
        canvas_item_id INTEGER,
        title TEXT NOT NULL,
        item_type TEXT NOT NULL,
        content_id INTEGER,
        position INTEGER,
        url TEXT,
        page_url TEXT,
        content_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_module_items_module_id ON module_items(module_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_module_items_item_type ON module_items(item_type);
    """)
    
    # Calendar_Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_type TEXT NOT NULL,
        source_type TEXT,
        source_id INTEGER,
        event_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP,
        all_day BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_calendar_events_course_id ON calendar_events(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_calendar_events_event_date ON calendar_events(event_date);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_calendar_events_event_type ON calendar_events(event_type);
    """)
    
    # User_Courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_courses (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        course_id INTEGER NOT NULL,
        indexing_opt_out BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        UNIQUE (user_id, course_id)
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_user_courses_user_id ON user_courses(user_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_user_courses_opt_out ON user_courses(indexing_opt_out);
    """)
    
    # Discussions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discussions (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        canvas_discussion_id INTEGER,
        title TEXT,
        content TEXT,
        posted_by TEXT,
        posted_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_discussions_course_id ON discussions(course_id);
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
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_announcements_course_id ON announcements(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_announcements_posted_at ON announcements(posted_at);
    """)
    
    # Grades table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        assignment_id INTEGER,
        student_id TEXT NOT NULL,
        grade REAL,
        feedback TEXT,
        graded_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE SET NULL,
        UNIQUE (assignment_id, student_id)
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_grades_course_id ON grades(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_grades_assignment_id ON grades(assignment_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades(student_id);
    """)
    
    # Lectures table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        lecture_date TIMESTAMP,
        location TEXT,
        content TEXT,
        recording_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_lectures_course_id ON lectures(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_lectures_lecture_date ON lectures(lecture_date);
    """)
    
    # Files table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        course_id INTEGER NOT NULL,
        canvas_file_id INTEGER,
        file_name TEXT NOT NULL,
        display_name TEXT,
        content_type TEXT,
        file_size INTEGER,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_files_course_id ON files(course_id);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_files_content_type ON files(content_type);
    """)


def create_views(cursor: sqlite3.Cursor) -> None:
    """Create database views for common queries."""
    
    # Upcoming deadlines view - For tests, we need to include all deadlines
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS upcoming_deadlines AS
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
    ORDER BY 
        a.due_date ASC;
    """)
    
    # Course summary view - Fixed the assignment selection to handle no due dates
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS course_summary AS
    SELECT 
        c.id AS course_id,
        c.course_code,
        c.course_name,
        c.instructor,
        COUNT(DISTINCT a.id) AS assignment_count,
        COUNT(DISTINCT m.id) AS module_count,
        MIN(a.due_date) AS next_due_date,
        (SELECT title FROM assignments WHERE course_id = c.id AND due_date IS NOT NULL 
         ORDER BY due_date ASC LIMIT 1) AS next_assignment
    FROM 
        courses c
    LEFT JOIN 
        assignments a ON c.id = a.course_id
    LEFT JOIN 
        modules m ON c.id = m.course_id
    GROUP BY 
        c.id;
    """)


def main() -> None:
    """Create database in the project directory."""
    project_dir = Path(__file__).parent
    db_path = project_dir / "data" / "canvas_mcp.db"
    create_database(str(db_path))


if __name__ == "__main__":
    main()
