# Database Schema for Canvas MCP

This document defines the database schema for the Canvas MCP server, which stores information from the Canvas LMS to provide an AI assistant with structured access to course information.

## Schema Overview

The database uses SQLite and consists of the following tables:

1. [Courses](#1-courses) - Core course information
2. [Syllabi](#2-syllabi) - Syllabus content for each course
3. [Assignments](#3-assignments) - Assignment, exam, and quiz details
4. [Modules](#4-modules) - Course content organization 
5. [Module_Items](#5-module_items) - Individual items within modules
6. [Calendar_Events](#6-calendar_events) - Unified view of all time-based events
7. [User_Courses](#7-user_courses) - User preferences for course indexing
8. [Discussions](#8-discussions) - Discussion threads and forum posts
9. [Announcements](#9-announcements) - Official course announcements
10. [Grades](#10-grades) - Student performance tracking
11. [Lectures](#11-lectures) - Lecture-specific information
12. [Files](#12-files) - Course files and documents

## Table Definitions

### 1. Courses

Stores core course information retrieved from Canvas.

```sql
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

CREATE INDEX idx_courses_canvas_id ON courses(canvas_course_id);
```

### 2. Syllabi

Stores syllabus content for each course.

```sql
CREATE TABLE syllabi (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    content TEXT,  -- Content from Canvas (HTML, link, etc.)
    content_type TEXT DEFAULT 'html', -- 'html', 'pdf_link', 'external_link', 'json', etc.
    parsed_content TEXT, -- Processed/extracted text
    is_parsed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE INDEX idx_syllabi_course_id ON syllabi(course_id);
```

### 3. Assignments

Records details about assignments, exams, and quizzes.

```sql
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    canvas_assignment_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    assignment_type TEXT, -- 'assignment', 'exam', 'quiz', etc.
    due_date TIMESTAMP,
    available_from TIMESTAMP,
    available_until TIMESTAMP,
    points_possible REAL,
    submission_types TEXT, -- 'online_text_entry', 'online_upload', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (course_id, canvas_assignment_id)
);

CREATE INDEX idx_assignments_course_id ON assignments(course_id);
CREATE INDEX idx_assignments_due_date ON assignments(due_date);
```

### 4. Modules

Organizes course content into structured sections.

```sql
CREATE TABLE modules (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    canvas_module_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    unlock_date TIMESTAMP,
    position INTEGER, -- Order within course
    require_sequential_progress BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (course_id, canvas_module_id)
);

CREATE INDEX idx_modules_course_id ON modules(course_id);
```

### 5. Module_Items

Individual items within modules (assignments, pages, links, etc.).

```sql
CREATE TABLE module_items (
    id INTEGER PRIMARY KEY,
    module_id INTEGER NOT NULL,
    canvas_item_id INTEGER,
    title TEXT NOT NULL,
    item_type TEXT NOT NULL, -- 'Assignment', 'File', 'Page', 'Discussion', etc.
    content_id INTEGER, -- ID of the content in its respective table
    position INTEGER, -- Order within module
    url TEXT, -- External URL if applicable
    page_url TEXT, -- For Canvas pages
    content_details TEXT, -- JSON with additional details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE INDEX idx_module_items_module_id ON module_items(module_id);
CREATE INDEX idx_module_items_item_type ON module_items(item_type);
```

### 6. Calendar_Events

Unified view of time-based events (assignments, exams, lectures, etc.).

```sql
CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT NOT NULL, -- 'assignment', 'exam', 'lecture', 'other'
    source_type TEXT, -- 'assignment', 'module_item', 'syllabus', etc.
    source_id INTEGER, -- ID from source table
    event_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    all_day BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE INDEX idx_calendar_events_course_id ON calendar_events(course_id);
CREATE INDEX idx_calendar_events_event_date ON calendar_events(event_date);
CREATE INDEX idx_calendar_events_event_type ON calendar_events(event_type);
```

### 7. User_Courses

Allows users to opt out of indexing specific courses.

```sql
CREATE TABLE user_courses (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL, -- User identifier
    course_id INTEGER NOT NULL,
    indexing_opt_out BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (user_id, course_id)
);

CREATE INDEX idx_user_courses_user_id ON user_courses(user_id);
CREATE INDEX idx_user_courses_opt_out ON user_courses(indexing_opt_out);
```

### 8. Discussions

Stores discussion threads and forum posts.

```sql
CREATE TABLE discussions (
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

CREATE INDEX idx_discussions_course_id ON discussions(course_id);
```

### 9. Announcements

Records official course announcements.

```sql
CREATE TABLE announcements (
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

CREATE INDEX idx_announcements_course_id ON announcements(course_id);
CREATE INDEX idx_announcements_posted_at ON announcements(posted_at);
```

### 10. Grades

Stores grades and feedback for assignments.

```sql
CREATE TABLE grades (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    assignment_id INTEGER,
    student_id TEXT NOT NULL, -- Identifier for the student
    grade REAL,
    feedback TEXT,
    graded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE SET NULL,
    UNIQUE (assignment_id, student_id)
);

CREATE INDEX idx_grades_course_id ON grades(course_id);
CREATE INDEX idx_grades_assignment_id ON grades(assignment_id);
CREATE INDEX idx_grades_student_id ON grades(student_id);
```

### 11. Lectures

Stores lecture-specific information and notes.

```sql
CREATE TABLE lectures (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    lecture_date TIMESTAMP,
    location TEXT,
    content TEXT, -- Lecture notes or summary
    recording_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE INDEX idx_lectures_course_id ON lectures(course_id);
CREATE INDEX idx_lectures_lecture_date ON lectures(lecture_date);
```

### 12. Files

Stores information about course files and documents.

```sql
CREATE TABLE files (
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

CREATE INDEX idx_files_course_id ON files(course_id);
CREATE INDEX idx_files_content_type ON files(content_type);
```

## SQL Views

### Upcoming Deadlines View

This view consolidates upcoming assignment deadlines for quick access.

```sql
CREATE VIEW upcoming_deadlines AS
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
    a.due_date > CURRENT_TIMESTAMP
ORDER BY 
    a.due_date ASC;
```

### Course Summary View

This view provides a summary of course content and deadlines.

```sql
CREATE VIEW course_summary AS
SELECT 
    c.id AS course_id,
    c.course_code,
    c.course_name,
    c.instructor,
    COUNT(DISTINCT a.id) AS assignment_count,
    COUNT(DISTINCT m.id) AS module_count,
    MIN(a.due_date) AS next_due_date,
    (SELECT title FROM assignments WHERE course_id = c.id AND due_date > CURRENT_TIMESTAMP ORDER BY due_date ASC LIMIT 1) AS next_assignment
FROM 
    courses c
LEFT JOIN 
    assignments a ON c.id = a.course_id
LEFT JOIN 
    modules m ON c.id = m.course_id
GROUP BY 
    c.id;
```

## Data Synchronization Strategy

1. **Initial Import**:
   - Fetch all courses, assignments, modules, etc. from Canvas API
   - Parse syllabus content to extract key dates and information
   - Populate database tables with retrieved data

2. **Incremental Updates**:
   - Periodically check for changes in Canvas data (daily or on request)
   - Update only changed records to minimize processing
   - Track last update timestamp to optimize API calls

3. **Event Processing**:
   - Extract calendar events from assignments, syllabus, and other sources
   - Maintain a unified timeline of all course-related events

## MCP Integration

The database schema is designed to be easily accessible through the MCP server:

1. **Resources**: 
   - Course information
   - Assignment details
   - Calendar events
   - Module structure

2. **Tools**:
   - Query upcoming deadlines
   - Search course content
   - Retrieve specific course materials
   - Update user preferences

## Conclusion

This database schema provides a comprehensive structure for storing Canvas LMS data in a way that makes it easily accessible to an AI assistant through the MCP server. The schema covers all the key aspects of course information while providing flexibility for future enhancements.
