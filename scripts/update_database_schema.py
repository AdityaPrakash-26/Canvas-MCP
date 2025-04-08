"""
Script to update the database schema to include the content_type field.
"""

import sqlite3
from pathlib import Path

# Database path
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"

print(f"Updating database schema at {DB_PATH}")

# Connect to database
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Check if content_type column exists
try:
    cursor.execute("SELECT content_type FROM syllabi LIMIT 1")
    print("content_type column already exists in syllabi table")
except sqlite3.OperationalError:
    print("Adding content_type column to syllabi table")
    cursor.execute("ALTER TABLE syllabi ADD COLUMN content_type TEXT DEFAULT 'html'")
    conn.commit()
    print("Added content_type column")

# Verify all tables and columns
tables = [
    "courses",
    "syllabi",
    "assignments",
    "modules",
    "module_items",
    "calendar_events",
    "user_courses",
    "announcements",
]

print("\nVerifying database tables:")
for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"  {table}: {len(columns)} columns - {', '.join(columns[:5])}...")
    except sqlite3.OperationalError:
        print(f"  {table}: Table not found")

# Now run the empty syllabi creation script
print("\nAdding empty syllabi for courses:")
cursor.execute("""
SELECT c.id, c.course_name, c.course_code
FROM courses c
LEFT JOIN syllabi s ON c.id = s.course_id
WHERE s.id IS NULL
""")

courses_without_syllabi = cursor.fetchall()
print(f"Found {len(courses_without_syllabi)} courses without syllabus entries")

# Create empty syllabus entries for each course
for course in courses_without_syllabi:
    course_id = course[0]
    course_name = course[1]
    course_code = course[2]

    print(f"Creating empty syllabus for {course_name} ({course_code})")

    cursor.execute(
        """
    INSERT INTO syllabi (
        course_id, content, content_type, parsed_content, is_parsed, updated_at
    ) VALUES (?, ?, ?, ?, ?, datetime('now'))
    """,
        (
            course_id,
            "<p>No syllabus content available</p>",
            "empty",
            "No syllabus content available",
            True,
        ),
    )

# Commit changes
conn.commit()
print(f"Created {len(courses_without_syllabi)} empty syllabus entries")

# Verify all courses now have syllabi
cursor.execute("""
SELECT COUNT(*) as count FROM courses c
LEFT JOIN syllabi s ON c.id = s.course_id
WHERE s.id IS NULL
""")

remaining = cursor.fetchone()[0]
print(f"Courses without syllabi after update: {remaining}")

conn.close()
print("\nDatabase update completed successfully!")
