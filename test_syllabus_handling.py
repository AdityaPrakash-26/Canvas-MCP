"""
Test script to verify syllabus handling in the Canvas MCP project.
"""
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# Test database path
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "syllabus_test.db"
os.makedirs(DB_DIR, exist_ok=True)

# Remove existing test database
if DB_PATH.exists():
    os.remove(DB_PATH)

print(f"Creating test database at {DB_PATH}")

# Create test database with schema
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Create necessary tables
cursor.execute("""
CREATE TABLE courses (
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
CREATE TABLE syllabi (
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

# Insert test courses
cursor.execute("""
INSERT INTO courses (
    id, canvas_course_id, course_code, course_name, instructor
) VALUES (?, ?, ?, ?, ?)
""", (1, 101, "CS101", "Introduction to Computer Science", "Dr. Smith"))

cursor.execute("""
INSERT INTO courses (
    id, canvas_course_id, course_code, course_name, instructor
) VALUES (?, ?, ?, ?, ?)
""", (2, 102, "CS102", "Data Structures", "Dr. Johnson"))

# Insert test syllabi with different content types
# 1. HTML syllabus
html_syllabus = """
<h1>CS101: Introduction to Computer Science</h1>
<p>This course provides an introduction to computer science and programming.</p>
<h2>Course Objectives</h2>
<ul>
  <li>Understand basic programming concepts</li>
  <li>Learn problem-solving techniques</li>
  <li>Develop algorithmic thinking</li>
</ul>
<h2>Grading</h2>
<p>Assignments: 40%<br>
Midterm: 20%<br>
Final: 30%<br>
Participation: 10%</p>
"""

cursor.execute("""
INSERT INTO syllabi (
    id, course_id, content, content_type, parsed_content, is_parsed
) VALUES (?, ?, ?, ?, ?, ?)
""", (1, 1, html_syllabus, "html", "This course provides an introduction to computer science and programming.", True))

# 2. PDF link syllabus
pdf_link_syllabus = """
<p>The syllabus for this course is available as a PDF:</p>
<p><a href="https://example.com/cs102_syllabus.pdf">Download CS102 Syllabus</a></p>
"""

cursor.execute("""
INSERT INTO syllabi (
    id, course_id, content, content_type, parsed_content, is_parsed
) VALUES (?, ?, ?, ?, ?, ?)
""", (2, 2, pdf_link_syllabus, "pdf_link", "The syllabus contains information about the Data Structures course.", True))

# Commit changes
conn.commit()

print("Test database created with sample syllabi")

# Now test retrieving the syllabi
print("\nTesting syllabus retrieval:")

# Function to detect content type (simplified version)
def detect_content_type(content):
    if not content:
        return "html"
    
    if ".pdf" in content.lower() and ("<a href=" in content.lower()):
        return "pdf_link"
    elif "http" in content and len(content) < 1000:
        return "external_link"
    else:
        return "html"

# Function to retrieve syllabus with content_type
def get_syllabus(course_id, format="raw"):
    cursor.execute("""
    SELECT
        c.course_code,
        c.course_name,
        c.instructor,
        s.content,
        s.content_type,
        s.parsed_content,
        s.is_parsed
    FROM
        courses c
    JOIN
        syllabi s ON c.id = s.course_id
    WHERE
        c.id = ?
    """, (course_id,))
    
    row = cursor.fetchone()
    if not row:
        return {"error": "Syllabus not found"}
    
    result = {
        "course_code": row[0],
        "course_name": row[1],
        "instructor": row[2],
        "content_type": row[4]
    }
    
    if format == "parsed" and row[6] and row[5]:
        result["content"] = row[5]  # parsed_content
    else:
        result["content"] = row[3]  # raw content
        
    # Add helpful notes for different content types
    if result["content_type"] == "pdf_link":
        result["content_note"] = "This syllabus is available as a PDF document. The link is included in the content."
    elif result["content_type"] == "external_link":
        result["content_note"] = "This syllabus is available as an external link. The URL is included in the content."
        
    return result

# Test both syllabi
html_syllabus = get_syllabus(1)
print(f"HTML Syllabus for {html_syllabus['course_name']} ({html_syllabus['course_code']}):")
print(f"  Content type: {html_syllabus['content_type']}")
print(f"  Content preview: {html_syllabus['content'][:50]}...")

pdf_syllabus = get_syllabus(2)
print(f"\nPDF Link Syllabus for {pdf_syllabus['course_name']} ({pdf_syllabus['course_code']}):")
print(f"  Content type: {pdf_syllabus['content_type']}")
print(f"  Content preview: {pdf_syllabus['content']}")
if "content_note" in pdf_syllabus:
    print(f"  Note: {pdf_syllabus['content_note']}")

# Test the content type detection
print("\nTesting content type detection:")
test_contents = [
    ("Empty content", None),
    ("Plain text", "This is just plain text"),
    ("HTML content", "<p>This is some <strong>HTML</strong> content</p>"),
    ("PDF link", "<a href='https://example.com/syllabus.pdf'>Download PDF</a>"),
    ("External link", "https://example.com/syllabus"),
]

for label, content in test_contents:
    content_type = detect_content_type(content)
    print(f"  {label}: {content_type}")

conn.close()
print("\nTest completed")
