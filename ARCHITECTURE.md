# Canvas MCP Architecture Guide

This document provides an overview of the Canvas MCP project architecture, design decisions, and component interactions.

## System Architecture

Canvas MCP follows a three-layer architecture:

1. **Data Access Layer**: Handles Canvas API communication and database operations
2. **Business Logic Layer**: Implements synchronization, parsing, and data processing
3. **API Layer**: Exposes MCP tools and resources for AI assistants

```
┌───────────────────┐     ┌───────────────────┐
│                   │     │                   │
│  Claude Desktop   │     │ MCP Inspector     │
│                   │     │                   │
└─────────┬─────────┘     └─────────┬─────────┘
          │                         │
          │                         │
┌─────────▼─────────────────────────▼─────────┐
│                                             │
│             MCP Protocol (JSON-RPC)         │
│                                             │
└─────────────────────┬─────────────────────┬─┘
                      │                     │
┌─────────────────────▼──────┐  ┌───────────▼───────────┐
│                            │  │                       │
│     Canvas MCP Server      │  │    Canvas MCP Tools   │
│    (server.py)             │  │    & Resources        │
│                            │  │                       │
└─────────────┬──────────────┘  └───────────┬───────────┘
              │                             │
┌─────────────▼─────────────────────────────▼─────────┐
│                                                     │
│               Canvas Client (canvas_client.py)      │
│                                                     │
└─────────────────────────┬───────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
┌─────────▼────────────┐     ┌────────────▼─────────┐
│                      │     │                      │
│    Canvas API        │     │    SQLite Database   │
│                      │     │                      │
└──────────────────────┘     └──────────────────────┘
```

## Key Components

### 1. Canvas Client (`canvas_client.py`)

The Canvas client handles all communication with the Canvas API and synchronizes data to the local SQLite database.

**Key responsibilities:**
- Authenticate with Canvas API
- Retrieve course, assignment, module, and announcement data
- Handle term filtering for current semester focus
- Extract PDF documents and links
- Implement syllabus parsing and content type detection

### 2. MCP Server (`server.py`)

The MCP server exposes tools and resources that AI assistants can use to access Canvas data.

**Key responsibilities:**
- Provide tools for data synchronization and querying
- Expose resources for course information, deadlines, syllabi, etc.
- Handle database connections and queries
- Format data for AI-friendly consumption

### 3. PDF Extractor (`utils/pdf_extractor.py`)

Utilities for extracting text content from PDF files, either local or from URLs.

**Key responsibilities:**
- Download PDFs from URLs
- Extract text and structured content
- Process tables and formatted content

### 4. Database Schema

The database schema is defined in `docs/db_schema.md` and implemented in `init_db.py`. It consists of 12 tables covering all Canvas data types.

**Key tables:**
- Courses - Core course information
- Syllabi - Syllabus content for each course
- Assignments - Assignment, exam, and quiz details
- Modules - Course content organization
- Module_Items - Individual items within modules
- Calendar_Events - Unified view of all time-based events
- User_Courses - User preferences for course indexing

## Data Flow

1. **Synchronization**:
   - User requests data sync through Claude
   - MCP server calls `sync_canvas_data` tool
   - Canvas client connects to Canvas API
   - Retrieved data is stored in SQLite database

2. **Query Flow**:
   - User asks Claude for information (e.g., "What's due this week?")
   - Claude calls appropriate MCP tool (e.g., `get_upcoming_deadlines`)
   - MCP server queries the SQLite database
   - Results are formatted and returned to Claude
   - Claude presents information to the user

3. **PDF Extraction**:
   - User asks about PDF content
   - Claude calls `get_course_pdf_files` to find PDFs
   - Claude then calls `extract_text_from_course_pdf` for a specific PDF
   - PDF extractor downloads and processes the PDF
   - Extracted text is returned to Claude

## Design Decisions

### SQLite Database

We chose SQLite for its:
- Zero-configuration setup
- Single file storage
- Cross-platform compatibility
- Embedded operation (no separate server)
- SQL query capability

### Term Filtering

Term filtering focuses on the current semester to:
- Reduce data volume
- Improve relevance
- Speed up synchronization
- Focus on active courses

### Content Type Detection

Syllabus content type detection allows handling various syllabus formats:
- HTML content directly in Canvas
- PDF documents linked from syllabi
- External links to course websites
- JSON structured data

### PDF Extraction

PDF extraction provides access to content in:
- Course syllabi provided as PDFs
- Lecture notes and slides
- Assignment instructions and rubrics
- Course materials and readings

## Extension Points

The architecture is designed for easy extension:

1. **Additional Data Sources**:
   - Add new Canvas API endpoints by extending the Canvas client
   - Implement new synchronization methods for specific data types

2. **Enhanced Processing**:
   - Add NLP capabilities for better syllabus parsing
   - Implement ML-based document structure analysis
   - Add OCR for scanned document support

3. **New MCP Tools**:
   - Create specialized tools for specific use cases
   - Implement subscription capabilities for data updates
   - Add personalization features based on user preferences

4. **Advanced Resources**:
   - Create recommendation resources
   - Implement study planning resources
   - Add grade tracking and performance analysis

## Database Diagrams

### Core Tables Relationship

```
  ┌──────────────┐
  │    courses   │
  └───────┬──────┘
          │
          │ 1:N
          ▼
┌─────────┴─────────┐     ┌───────────────┐
│     syllabi       │     │  assignments  │
└───────────────────┘     └───────┬───────┘
                                  │
                                  │ 1:N
                          ┌───────┴───────┐
                          │calendar_events│
                          └───────────────┘
```

### Module Relationship

```
┌──────────────┐
│    courses   │
└───────┬──────┘
        │
        │ 1:N
        ▼
┌───────┴──────┐
│   modules    │
└───────┬──────┘
        │
        │ 1:N
        ▼
┌───────┴──────┐
│ module_items │
└──────────────┘
```

## Performance Considerations

1. **Data Volume**: Canvas installations can have hundreds of courses with thousands of assignments, modules, and files. We optimize by:
   - Implementing term filtering
   - Using SQLite indexes
   - Implementing incremental updates

2. **API Rate Limiting**: Canvas API can impose rate limits. Our approach:
   - Batch requests where possible
   - Cache results to reduce API calls
   - Use incremental sync to minimize data transfer

3. **PDF Processing**: PDF extraction can be resource-intensive. We optimize by:
   - Limiting extraction to requested PDFs only
   - Caching extracted content
   - Setting maximum page limits

## Security Considerations

1. **API Credentials**: Canvas API keys are sensitive. We protect them by:
   - Storing only in `.env` file (not committed to repository)
   - Using environment variables
   - Avoiding logging of credentials

2. **Local Data Storage**: SQLite database contains educational data. We ensure:
   - Database is stored locally
   - No cloud synchronization of database file
   - Opt-out capability for sensitive courses

3. **MCP Communication**: MCP uses local JSON-RPC. Security is maintained by:
   - Local-only communication (no network exposure)
   - Single-user access model
   - Limited server capabilities

## Future Architecture Directions

1. **Multi-User Support**:
   - User authentication system
   - Per-user databases
   - Role-based access control

2. **Enhanced Extraction**:
   - ML-based document understanding
   - Video lecture transcription
   - Structured information extraction

3. **Learning Analytics**:
   - Performance tracking
   - Study pattern analysis
   - Personalized recommendations

4. **Integration Expansion**:
   - Additional LMS support beyond Canvas
   - Integration with other educational tools
   - Export capabilities to study apps
