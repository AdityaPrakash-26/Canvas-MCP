# Canvas-MCP Database Schema Documentation

This document provides comprehensive documentation of the Canvas-MCP database schema, including table relationships, field descriptions, and usage examples. This schema is designed to store data from the Canvas Learning Management System (LMS) in a structured format for use by AI agents and other tools.

## Schema Overview

The Canvas-MCP database uses SQLite and consists of the following tables:

1. [Terms](#1-terms) - Academic terms information
2. [Courses](#2-courses) - Core course information
3. [Syllabi](#3-syllabi) - Syllabus content for each course
4. [Assignments](#4-assignments) - Assignment details and deadlines
5. [Modules](#5-modules) - Course content organization
6. [Module_Items](#6-module_items) - Individual items within modules
7. [Announcements](#7-announcements) - Course announcements
8. [Conversations](#8-conversations) - Direct messages and conversations
9. [Calendar_Events](#9-calendar_events) - Course calendar events

## Entity Relationship Diagram

```
┌─────────┐       ┌─────────┐       ┌──────────────┐
│  Terms  │◄──┐   │ Courses │◄─────┐│    Syllabi   │
└─────────┘   │   └─────────┘      │└──────────────┘
              │        ▲           │
              └────────┘           │
                       │           │
                       │           │
┌─────────────┐        │          │┌──────────────┐
│ Assignments │◄───────┘          ││ Announcements│
└─────────────┘                   │└──────────────┘
                                  │
┌─────────┐       ┌────────────┐  │┌──────────────┐
│ Modules │◄──────┤Module_Items│  ││Conversations │
└─────────┘       └────────────┘  │└──────────────┘
                                  │
                                  │┌──────────────┐
                                  └┤Calendar_Events│
                                   └──────────────┘
```

## Table Definitions

### 1. Terms

Stores information about academic terms.

```sql
CREATE TABLE IF NOT EXISTS terms (
    id INTEGER PRIMARY KEY,
    canvas_term_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| canvas_term_id | INTEGER | Canvas term ID (unique) |
| name | TEXT | Term name (e.g., "Spring 2025") |
| start_date | TIMESTAMP | Term start date |
| end_date | TIMESTAMP | Term end date |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get the current term
SELECT * FROM terms 
WHERE start_date <= CURRENT_TIMESTAMP 
AND end_date >= CURRENT_TIMESTAMP;

-- Get all courses for a specific term
SELECT c.* FROM courses c
JOIN terms t ON c.term_id = t.id
WHERE t.name = 'Spring 2025';
```

### 2. Courses

Stores core course information retrieved from Canvas.

```sql
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

CREATE INDEX IF NOT EXISTS idx_courses_course_name ON courses(course_name);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| canvas_course_id | INTEGER | Canvas course ID (unique) |
| course_code | TEXT | Course code (e.g., "CS-110-1") |
| course_name | TEXT | Full course name |
| instructor | TEXT | Course instructor name |
| description | TEXT | Course description |
| start_date | TIMESTAMP | Course start date |
| end_date | TIMESTAMP | Course end date |
| term_id | INTEGER | Foreign key to terms.id |
| syllabus_body | TEXT | HTML content of the syllabus |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get all active courses
SELECT * FROM courses 
WHERE start_date <= CURRENT_TIMESTAMP 
AND end_date >= CURRENT_TIMESTAMP;

-- Get course details by course code
SELECT * FROM courses WHERE course_code = 'CS-110-1';
```

### 3. Syllabi

Stores syllabus content for each course.

```sql
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

CREATE INDEX IF NOT EXISTS idx_syllabi_course_id ON syllabi(course_id);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| content | TEXT | Syllabus content (HTML, link, etc.) |
| content_type | TEXT | Content type ('html', 'pdf_link', etc.) |
| parsed_content | TEXT | Processed/extracted text |
| is_parsed | BOOLEAN | Whether content has been parsed |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get syllabus for a specific course
SELECT s.* FROM syllabi s
JOIN courses c ON s.course_id = c.id
WHERE c.course_code = 'CS-110-1';

-- Get all syllabi that haven't been parsed yet
SELECT * FROM syllabi WHERE is_parsed = FALSE;
```

### 4. Assignments

Records details about assignments, exams, and quizzes.

```sql
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

CREATE INDEX IF NOT EXISTS idx_assignments_course_id ON assignments(course_id);
CREATE INDEX IF NOT EXISTS idx_assignments_due_at ON assignments(due_at);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| canvas_assignment_id | INTEGER | Canvas assignment ID |
| name | TEXT | Assignment name |
| title | TEXT | Alias for name |
| description | TEXT | Assignment description |
| due_at | TIMESTAMP | Assignment due date and time |
| due_date | TIMESTAMP | Alias for due_at |
| points_possible | REAL | Maximum points possible |
| assignment_type | TEXT | Type ('assignment', 'quiz', 'exam', etc.) |
| submission_types | TEXT | Submission types ('online_text_entry', etc.) |
| source_type | TEXT | Source of the assignment |
| available_from | TIMESTAMP | When assignment becomes available |
| available_until | TIMESTAMP | When assignment is no longer available |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get upcoming assignments for a course
SELECT * FROM assignments 
WHERE course_id = 1 
AND due_at > CURRENT_TIMESTAMP 
ORDER BY due_at ASC;

-- Get assignments due in the next 7 days
SELECT c.course_code, a.name, a.due_at 
FROM assignments a
JOIN courses c ON a.course_id = c.id
WHERE a.due_at BETWEEN CURRENT_TIMESTAMP AND datetime('now', '+7 days')
ORDER BY a.due_at ASC;
```

### 5. Modules

Organizes course content into structured sections.

```sql
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

CREATE INDEX IF NOT EXISTS idx_modules_course_id ON modules(course_id);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| canvas_module_id | INTEGER | Canvas module ID |
| name | TEXT | Module name |
| description | TEXT | Module description |
| position | INTEGER | Order within course |
| unlock_date | TIMESTAMP | When module becomes available |
| require_sequential_progress | BOOLEAN | Whether items must be completed in order |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get all modules for a course in order
SELECT * FROM modules 
WHERE course_id = 1 
ORDER BY position ASC;

-- Get modules that are currently available
SELECT * FROM modules 
WHERE course_id = 1 
AND (unlock_date IS NULL OR unlock_date <= CURRENT_TIMESTAMP);
```

### 6. Module_Items

Individual items within modules (assignments, pages, links, etc.).

```sql
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

CREATE INDEX IF NOT EXISTS idx_module_items_module_id ON module_items(module_id);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| module_id | INTEGER | Foreign key to modules.id |
| canvas_module_item_id | INTEGER | Canvas module item ID |
| canvas_item_id | INTEGER | Canvas item ID |
| title | TEXT | Item title |
| position | INTEGER | Order within module |
| content_type | TEXT | Content type |
| type | TEXT | Item type |
| item_type | TEXT | Alternative item type field |
| content_id | INTEGER | ID of content in its respective table |
| url | TEXT | External URL if applicable |
| page_url | TEXT | URL for Canvas pages |
| content_details | TEXT | JSON with additional details |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get all items in a module in order
SELECT * FROM module_items 
WHERE module_id = 1 
ORDER BY position ASC;

-- Get all assignment items across all modules for a course
SELECT mi.* 
FROM module_items mi
JOIN modules m ON mi.module_id = m.id
WHERE m.course_id = 1 
AND (mi.content_type = 'Assignment' OR mi.type = 'Assignment' OR mi.item_type = 'Assignment');
```

### 7. Announcements

Records official course announcements.

```sql
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

CREATE INDEX IF NOT EXISTS idx_announcements_course_id ON announcements(course_id);
CREATE INDEX IF NOT EXISTS idx_announcements_posted_at ON announcements(posted_at);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| canvas_announcement_id | INTEGER | Canvas announcement ID |
| title | TEXT | Announcement title |
| content | TEXT | Announcement content |
| posted_by | TEXT | Author of the announcement |
| posted_at | TIMESTAMP | When the announcement was posted |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get recent announcements for a course
SELECT * FROM announcements 
WHERE course_id = 1 
ORDER BY posted_at DESC 
LIMIT 10;

-- Get announcements from the past week
SELECT c.course_code, a.title, a.posted_at, a.content 
FROM announcements a
JOIN courses c ON a.course_id = c.id
WHERE a.posted_at >= datetime('now', '-7 days')
ORDER BY a.posted_at DESC;
```

### 8. Conversations

Stores direct messages and conversations.

```sql
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

CREATE INDEX IF NOT EXISTS idx_conversations_course_id ON conversations(course_id);
CREATE INDEX IF NOT EXISTS idx_conversations_posted_at ON conversations(posted_at);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| canvas_conversation_id | INTEGER | Canvas conversation ID |
| title | TEXT | Conversation subject |
| content | TEXT | Message content |
| posted_by | TEXT | Author of the message |
| posted_at | TIMESTAMP | When the message was posted |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get recent conversations for a course
SELECT * FROM conversations 
WHERE course_id = 1 
ORDER BY posted_at DESC 
LIMIT 10;

-- Get all communications (announcements and conversations) for a course
SELECT 'Announcement' as type, title, content, posted_by, posted_at 
FROM announcements 
WHERE course_id = 1
UNION ALL
SELECT 'Conversation' as type, title, content, posted_by, posted_at 
FROM conversations 
WHERE course_id = 1
ORDER BY posted_at DESC;
```

### 9. Calendar_Events

Stores calendar events for courses.

```sql
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

CREATE INDEX IF NOT EXISTS idx_calendar_events_course_id ON calendar_events(course_id);
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| course_id | INTEGER | Foreign key to courses.id |
| canvas_event_id | INTEGER | Canvas event ID |
| title | TEXT | Event title |
| description | TEXT | Event description |
| start_at | TIMESTAMP | Event start date and time |
| end_at | TIMESTAMP | Event end date and time |
| event_date | TIMESTAMP | Primary event date (for sorting) |
| event_type | TEXT | Type of event |
| source_type | TEXT | Source of the event |
| source_id | INTEGER | ID from source table |
| location_name | TEXT | Event location name |
| location_address | TEXT | Event location address |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

#### Usage Example

```sql
-- Get upcoming calendar events for a course
SELECT * FROM calendar_events 
WHERE course_id = 1 
AND start_at > CURRENT_TIMESTAMP 
ORDER BY start_at ASC;

-- Get all events for the next 30 days across all courses
SELECT c.course_code, e.title, e.start_at, e.end_at, e.location_name 
FROM calendar_events e
JOIN courses c ON e.course_id = c.id
WHERE e.start_at BETWEEN CURRENT_TIMESTAMP AND datetime('now', '+30 days')
ORDER BY e.start_at ASC;
```

## Common Queries

### Get Upcoming Deadlines

```sql
SELECT 
    c.course_code,
    c.course_name,
    a.title,
    a.due_at,
    a.points_possible
FROM 
    assignments a
JOIN 
    courses c ON a.course_id = c.id
WHERE 
    a.due_at > CURRENT_TIMESTAMP
ORDER BY 
    a.due_at ASC
LIMIT 10;
```

### Get Course Structure with Modules and Items

```sql
SELECT 
    c.course_code,
    m.name AS module_name,
    m.position AS module_position,
    mi.title AS item_title,
    mi.item_type,
    mi.position AS item_position
FROM 
    courses c
JOIN 
    modules m ON c.id = m.course_id
JOIN 
    module_items mi ON m.id = mi.module_id
WHERE 
    c.id = 1
ORDER BY 
    m.position, mi.position;
```

### Get All Communications for a Course

```sql
SELECT 
    'Announcement' AS type,
    title,
    content,
    posted_by,
    posted_at
FROM 
    announcements
WHERE 
    course_id = 1
UNION ALL
SELECT 
    'Conversation' AS type,
    title,
    content,
    posted_by,
    posted_at
FROM 
    conversations
WHERE 
    course_id = 1
ORDER BY 
    posted_at DESC;
```

### Get Course Calendar with Assignments and Events

```sql
-- Assignments as events
SELECT 
    'Assignment' AS event_type,
    a.title,
    a.description,
    a.due_at AS start_time,
    NULL AS end_time,
    NULL AS location
FROM 
    assignments a
WHERE 
    a.course_id = 1
    AND a.due_at IS NOT NULL
UNION ALL
-- Calendar events
SELECT 
    e.event_type,
    e.title,
    e.description,
    e.start_at AS start_time,
    e.end_at AS end_time,
    e.location_name AS location
FROM 
    calendar_events e
WHERE 
    e.course_id = 1
ORDER BY 
    start_time ASC;
```

## Data Synchronization Strategy

The Canvas-MCP database is synchronized with the Canvas LMS using the following strategy:

1. **Initial Sync**:
   - Fetch all courses for the current term
   - For each course, fetch assignments, modules, announcements, etc.
   - Store all data in the local database

2. **Incremental Updates**:
   - Periodically check for changes in Canvas data
   - Update only changed records to minimize processing
   - Track last update timestamp to optimize API calls

3. **Data Relationships**:
   - Maintain foreign key relationships between tables
   - Ensure data consistency with cascading deletes
   - Use indexes for efficient querying

## Best Practices for AI Agents

When working with the Canvas-MCP database, AI agents should follow these best practices:

1. **Use Foreign Keys**: Always join tables using their foreign key relationships to ensure data consistency.

2. **Handle NULL Values**: Many fields can be NULL, especially dates and descriptions. Always check for NULL values when processing data.

3. **Use Indexes**: When querying large datasets, use indexed fields (course_id, posted_at, due_at) for better performance.

4. **Respect Data Types**: Pay attention to data types, especially when working with timestamps and booleans.

5. **Use Aliases**: The database includes some alias fields (e.g., title/name, due_date/due_at) for compatibility. Be consistent in your usage.

6. **Unified Queries**: Use UNION queries to combine related data from different tables (e.g., announcements and conversations).

7. **Date Filtering**: When working with dates, use SQLite date functions (datetime, strftime) for proper filtering.

## Conclusion

This database schema provides a comprehensive structure for storing Canvas LMS data in a way that makes it easily accessible to AI agents through the MCP server. The schema covers all key aspects of course information while providing flexibility for future enhancements.
