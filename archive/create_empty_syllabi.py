"""
Utility script to create empty syllabus entries for all courses in the database.
This ensures that the system can handle courses without syllabus content in Canvas.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# Database path
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"

print(f"Connecting to database at {DB_PATH}")

# Connect to database
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all courses that don't have a syllabus entry
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
    course_id = course["id"]
    course_name = course["course_name"]
    course_code = course["course_code"]

    print(f"Creating empty syllabus for {course_name} ({course_code})")

    cursor.execute(
        """
    INSERT INTO syllabi (
        course_id, content, content_type, parsed_content, is_parsed, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            course_id,
            "<p>No syllabus content available</p>",
            "empty",
            "No syllabus content available",
            True,
            datetime.now().isoformat(),
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

remaining = cursor.fetchone()["count"]
print(f"Courses without syllabi after update: {remaining}")

conn.close()
print("Done!")
