# Canvas-MCP Guide for AI Assistants

This guide is specifically designed to help AI assistants like Claude understand and work with the Canvas-MCP codebase. It provides structured information about the project architecture, key components, and common patterns to help you assist users effectively.

## Project Overview

Canvas-MCP is a Model Context Protocol (MCP) server that integrates with the Canvas Learning Management System. It allows AI assistants to access structured course information such as syllabi, assignments, deadlines, and modules, helping students stay organized and succeed academically.

## Features

### Core Functionality
- **Canvas API Integration**: Sync courses, assignments, modules, and announcements
- **Syllabus Parsing**: Extract important information from course syllabi in various formats (HTML, PDF, links)
- **PDF Extraction**: Process and extract text from PDF files in courses
- **Smart Filtering**: Term-based course filtering to focus on current semester
- **Opt-Out System**: Allow users to opt out of indexing specific courses

### Data Management
- **Robust Database Schema**: Structured SQLite database with tables for courses, assignments, modules, and more
- **Incremental Updates**: Efficient synchronization that only updates changed data
- **Foreign Key Constraints**: Maintain data integrity with proper relationships

### MCP Integration
- **Comprehensive Tools**: Tools for accessing and searching course information
- **Resource URIs**: Structured resource identifiers for accessing specific data
- **AI-Friendly Responses**: Data formatted for optimal AI assistant consumption

## Tech Stack

### Core Technologies
- **Language**: Python 3.12+ with modern type annotations
- **Database**: SQLite for zero-configuration local data storage
- **Package Manager**: UV (not pip) for faster, more reliable dependency management
- **MCP Framework**: Model Context Protocol for AI integration

### API & Processing
- **API Integration**: Canvas API via canvasapi library
- **PDF Processing**: pdfplumber for text extraction from PDFs
- **Document Processing**: python-docx for Word document handling
- **HTML Parsing**: BeautifulSoup4 for HTML content extraction

### Development & Testing
- **Testing**: pytest for unit and integration tests
- **Linting**: ruff for code quality and formatting
- **Type Checking**: mypy for static type analysis
- **Logging**: structlog for structured, contextual logging

## Repository Structure

```
Canvas-MCP/
├── data/                  # Database and cached files
├── docs/                  # Documentation files
├── library_docs/          # External library documentation
├── scripts/               # Testing and utility scripts
├── src/                   # Source code
│   └── canvas_mcp/        # Main package
│       ├── sync/          # Synchronization modules
│       ├── tools/         # MCP tool implementations
│       └── utils/         # Utility functions
├── tests/                 # Test files
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests
├── .env                   # Environment variables (not in repo)
├── CLAUDE.md              # Development guidelines
└── README.md              # Main project documentation
```

## Architecture

Canvas-MCP uses a layered architecture with clear separation of concerns:

### 1. Data Access Layer
- **CanvasApiAdapter**: Wraps the Canvas API client and handles API interactions
  - Manages authentication and error handling
  - Provides methods for fetching different types of data
  - Isolates the rest of the application from API-specific details
- **DatabaseManager**: Manages database connections and operations
  - Provides connection pooling and transaction management
  - Implements the `with_connection` decorator for clean transaction handling
  - Ensures proper error handling and connection cleanup

### 2. Business Logic Layer
- **SyncService**: Orchestrates data flow between API and database
  - Coordinates the synchronization process
  - Implements business rules for data filtering and transformation
  - Uses Pydantic models for data validation
- **Models**: Define data structures and validation rules
  - Implement field validators for data transformation
  - Provide clear data contracts between layers
  - Handle type coercion and field mapping

### 3. API Layer
- **MCP Server**: Exposes tools and resources for AI assistants
  - Registers tool functions and resource handlers
  - Manages application lifecycle and resources
  - Handles request routing and response formatting
- **Tool Functions**: Implement specific functionality
  - Focus on request handling and response formatting
  - Delegate business logic to services
  - Provide clear documentation for AI assistants

## Key Components

### 1. Server (`src/canvas_mcp/server.py`)

The server module is the entry point for the MCP server. It:
- Initializes resources (database, API adapter, sync service)
- Registers tools and resources
- Handles the application lifecycle
- Manages request routing

```python
# Create an MCP server with lifespan
mcp = FastMCP(
    "Canvas MCP",
    dependencies=[...],
    description="A Canvas integration for accessing course information, assignments, and resources.",
    lifespan=app_lifespan,
)

# Register tool modules
from canvas_mcp.tools.assignments import register_assignment_tools
# ... other imports

# Register all tools
register_assignment_tools(mcp)
# ... other registrations
```

### 2. Canvas API Adapter (`src/canvas_mcp/canvas_api_adapter.py`)

The adapter wraps the Canvas API client and provides methods for interacting with the Canvas API:
- Handles authentication and error handling
- Provides methods for fetching different types of data
- Isolates the rest of the application from API-specific details

```python
class CanvasApiAdapter:
    def __init__(self, canvas_client):
        self.canvas = canvas_client

    def get_courses(self, **kwargs):
        """Get courses from Canvas API."""
        try:
            return self.canvas.get_courses(**kwargs)
        except Exception as e:
            logger.error(f"Error getting courses: {e}")
            return []
```

### 3. Sync Service (`src/canvas_mcp/sync/service.py`)

The sync service orchestrates data flow between the Canvas API and the local database:
- Coordinates the synchronization process
- Implements business rules for data filtering and transformation
- Uses Pydantic models for data validation
# TODO: add with_connection decorator for example cuz it rlly fucking importnat

```python
class SyncService:
    def __init__(self, db_manager, api_adapter):
        self.db_manager = db_manager
        self.api_adapter = api_adapter

    def sync_courses(self):
        """Sync courses from Canvas API to database."""
        # Get courses from API
        courses = self.api_adapter.get_courses()

        # Filter courses
        filtered_courses = self._filter_courses_by_term(courses)

        # Persist courses to database
        return self._persist_courses_and_syllabi(filtered_courses)
```

### 4. Database Manager (`src/canvas_mcp/utils/db_manager.py`)

The database manager handles database connections and operations:
- Provides connection pooling and transaction management
- Implements the `with_connection` decorator for clean transaction handling
- Ensures proper error handling and connection cleanup

```python
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        """Connect to the database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor

    def with_connection(self, func):
        """Decorator for database operations."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            conn, cursor = self.connect()
            try:
                result = func(conn, cursor, *args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()
        return wrapper
```

### 5. Tool Functions (`src/canvas_mcp/tools/`)

Tool functions implement specific functionality exposed to AI assistants:
- Focus on request handling and response formatting
- Delegate business logic to services
- Provide clear documentation for AI assistants

```python
@mcp.tool()
def get_upcoming_deadlines(ctx, days=7, course_id=None):
    """
    Get upcoming assignment deadlines.

    Args:
        ctx: Request context containing resources
        days: Number of days to look ahead
        course_id: Optional course ID to filter by

    Returns:
        List of upcoming deadlines
    """
    # Get database manager from the lifespan context
    db_manager = ctx.request_context.lifespan_context["db_manager"]

    # Query the database
    # ...

    # Format and return the results
    return formatted_results
```

## Context Object Structure

The context object is passed to all tool functions and provides access to the database, API adapter, and sync service:

```python
ctx = SimpleNamespace(
    request_context=SimpleNamespace(
        lifespan_context={
            "db_manager": db_manager,  # DatabaseManager instance
            "api_adapter": api_adapter,  # CanvasApiAdapter instance
            "sync_service": sync_service,  # SyncService instance
        }
    )
)
```

To access components within a tool function:

```python
def my_tool(ctx, param1, param2):
    # Access the database manager
    db_manager = ctx.request_context.lifespan_context["db_manager"]

    # Access the API adapter
    api_adapter = ctx.request_context.lifespan_context["api_adapter"]

    # Access the sync service
    sync_service = ctx.request_context.lifespan_context["sync_service"]
```

## Database Schema

The database schema includes the following key tables:

### Terms Table
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

### Courses Table
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
```

### Assignments Table
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
```

For a complete schema, see `docs/db_schema_updated.md`.

## Common Patterns

### Database Queries

```python
# Get a single record
record = db_manager.execute_query(
    "SELECT * FROM table WHERE id = ?", (id,)
).fetchone()

# Get multiple records
records = db_manager.execute_query(
    "SELECT * FROM table WHERE field = ?", (value,)
).fetchall()

# Insert a record
db_manager.execute_query(
    "INSERT INTO table (field1, field2) VALUES (?, ?)",
    (value1, value2),
)

# Update a record
db_manager.execute_query(
    "UPDATE table SET field = ? WHERE id = ?",
    (new_value, id),
)
```

### API Requests

```python
# Get a course
course = api_adapter.get_course(course_id)

# Get assignments for a course
assignments = api_adapter.get_course_assignments(course_id)

# Get modules for a course
modules = api_adapter.get_course_modules(course_id)
```

### Sync Operations

```python
# Sync all data
sync_result = sync_service.sync_all()

# Sync specific course
sync_service.sync_course(course_id)

# Sync assignments for a course
sync_service.sync_assignments(course_id)
```

## Tool Registration Process

Tools are registered using registration functions that add them to a tools dictionary:

1. Define the tool function in a module under `src/canvas_mcp/tools/`
2. Create a registration function in the same module
3. Call the registration function in `src/canvas_mcp/server.py`

Example registration function:

```python
def register_my_tools(mcp):
    """Register my tools with the MCP server."""

    @mcp.tool()
    def my_tool(ctx, param1, param2):
        """Tool documentation."""
        # Implementation
        return result
```

## Testing Approach

Canvas-MCP uses a comprehensive testing approach with multiple levels:

### 1. Unit Testing
- Tests individual components in isolation
- Uses pytest for test framework
- Mocks external dependencies
- Focuses on business logic and edge cases

### 2. Integration Testing
- Tests interactions between components
- Uses a test database with real schema
- Verifies data flow between layers
- Tests error handling and recovery

### 3. Tool Testing
- Tests MCP tools directly without server overhead
- Verifies tool functionality and response format
- Uses the `extract_tools_test.py` utility
- Supports both automated and interactive testing

### 4. End-to-End Testing
- Tests the full workflow from sync to tool usage
- Verifies integration with Canvas API
- Tests the complete user experience
- Uses the `test_tools_integration.py` utility

## Testing Workflow

### Extract and Test Tools

Use `extract_tools_test.py` to extract and test tools:

```bash
# Test a specific tool
python scripts/extract_tools_test.py --tool my_tool --args '{"param1": "value1"}'

# Run all tests
python scripts/extract_tools_test.py --test
```

### Test Integration

Use `test_tools_integration.py` to test integration between tools:

```bash
python scripts/diagnostics/test_tools_integration.py
```

### Test in Direct Mode

Use `direct_tools_test.py` to test tools directly:

```bash
python scripts/direct_tools_test.py --test
```

## Troubleshooting Guide

### Common Issues

#### Installation Issues

- **UV Not Found**: Ensure UV is installed correctly with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Package Installation Fails**: Try `uv sync --upgrade` to update all dependencies
- **Python Version Error**: Ensure you're using Python 3.12 or higher

#### API Connection Issues

- **API Key Invalid**: Check that the Canvas API key is correct in the .env file
- **API URL Incorrect**: Verify the Canvas instance URL (e.g., https://canvas.emory.edu)
- **Rate Limiting**: Canvas API may impose rate limits; try again later

#### Sync Issues

- **No Courses Found**: Check that the user has active courses in the current term
- **Sync Fails**: Check Canvas API credentials and network connection
- **Database Errors**: Try resetting the database with `rm -f data/canvas_mcp.db && python -m src.canvas_mcp.init_db`

#### MCP Integration Issues

- **Claude Can't Find Tools**: Verify the MCP server is running and properly configured in Claude Desktop
- **Tool Execution Errors**: Check the server logs for detailed error messages
- **Resource Not Found**: Ensure the resource URI is correctly formatted

### Specific Issues

#### Issue: Tool not found

**Solution:**
- Check that the tool is registered in the tools dictionary
- Verify that the registration function is called in server.py
- Make sure the registration function is imported in extract_tools_test.py

#### Issue: Database error

**Solution:**
- Check that the database is initialized
- Verify that foreign key constraints are enabled
- Ensure the database schema matches the expected schema

#### Issue: API error

**Solution:**
- Check that API credentials are set
- Verify that the API adapter is properly initialized
- Check for rate limiting or permission issues

### Debugging Techniques

1. **Check Logs**: Look for error messages in the server logs
2. **Inspect Database**: Use SQLite tools to inspect the database directly
3. **Test API Connection**: Use the API adapter directly to test API connectivity
4. **Isolate Components**: Test individual components in isolation
5. **Enable Debug Logging**: Set logging level to DEBUG for more detailed logs

## Best Practices for AI Assistants

1. **Start with the test utilities**: Use the test utilities to understand how tools work before suggesting modifications.

2. **Understand the context object**: The context object is passed to all tools and provides access to essential components.

3. **Follow existing patterns**: Look at similar tools to understand the patterns used in the codebase.

4. **Test incrementally**: Suggest testing changes incrementally using the test utilities.

5. **Check database schema**: Understand the database schema before suggesting changes that affect the database.

6. **Use proper error handling**: Follow the existing error handling patterns in the codebase.

7. **Document changes**: Suggest adding proper docstrings and comments to explain changes.

8. **Update tests**: Recommend updating tests to cover new functionality or changes to existing functionality.

## MCP Tools & Resources

### Synchronization Tools

- `sync_canvas_data`: Synchronize all data from Canvas to the local database
  - Fetches courses, assignments, modules, announcements, and more
  - Filters by term to focus on current semester
  - Updates only changed data for efficiency

### Course Information Tools

- `get_course_list`: Get a list of all available courses
  - Returns course ID, name, code, and term information
  - Filters to show only active courses by default
- `get_syllabus`: Get a course syllabus
  - Supports both raw HTML and parsed text formats
  - Extracts content from various syllabus formats
- `get_course_modules`: Get modules for a specific course
  - Returns module structure with items and content
  - Preserves module ordering and relationships

### Assignment & Deadline Tools

- `get_upcoming_deadlines`: Get assignments due in the next X days
  - Customizable time window (default: 7 days)
  - Optional filtering by course
  - Includes assignment details and points possible
- `get_course_assignments`: Get assignments for a specific course
  - Returns all assignments with due dates and descriptions
  - Supports filtering by assignment type

### Content & Communication Tools

- `get_course_communications`: Get all communications for a course
  - Combines announcements and conversations in a unified view
  - Includes sender information and timestamps
- `get_course_pdf_files`: Get PDF files in a course
  - Lists all PDF files with URLs and metadata
- `extract_text_from_course_file`: Extract text from a course file
  - Supports PDF, Word documents, and other formats
  - Preserves text structure where possible
- `search_course_content`: Search across all course content
  - Full-text search across syllabi, assignments, and modules
  - Returns contextual matches with source information

### User Preference Tools

- `opt_out_course`: Opt out of indexing a specific course
  - Prevents synchronization of sensitive course content
  - Can be reversed at any time

## Documentation References

- `CLAUDE.md`: Development guidelines and best practices
- `docs/ARCHITECTURE.md`: Comprehensive architecture overview
- `docs/sync_architecture.md`: Sync system design
- `docs/db_schema_updated.md`: Database schema documentation
- `scripts/README.md`: Testing utilities documentation
- `docs/live_testing.md`: Testing procedures
