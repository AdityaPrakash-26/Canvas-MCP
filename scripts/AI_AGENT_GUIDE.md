# Canvas-MCP Guide for AI Agents

This guide is specifically designed to help AI agents understand and work with the Canvas-MCP codebase. It provides a structured approach to navigating the codebase, understanding its architecture, and effectively testing changes.

## Codebase Structure

Canvas-MCP follows a layered architecture with the following key components:

### 1. Tools Layer (`src/canvas_mcp/tools/`)

This layer contains the tool functions that are exposed to users. Each tool is a function that takes a context object and additional parameters, and returns a result.

**Key Files:**
- `assignments.py`: Tools for working with course assignments
- `calendar.py`: Tools for working with course calendar events
- `courses.py`: Tools for working with course information
- `modules.py`: Tools for working with course modules
- `syllabus.py`: Tools for working with course syllabi
- `sync.py`: Tools for synchronizing data from Canvas API

### 2. Sync Layer (`src/canvas_mcp/sync/`)

This layer handles synchronization of data from the Canvas API to the local database.

**Key Files:**
- `service.py`: The main SyncService class that orchestrates synchronization
- `courses.py`: Functions for syncing course data
- `assignments.py`: Functions for syncing assignment data
- `modules.py`: Functions for syncing module data
- `announcements.py`: Functions for syncing announcement data

### 3. Utilities Layer (`src/canvas_mcp/utils/`)

This layer provides utility functions and classes used throughout the codebase.

**Key Files:**
- `db_manager.py`: The DatabaseManager class for database operations
- `file_extractor.py`: Functions for extracting text from files

### 4. API Adapter (`src/canvas_mcp/canvas_api_adapter.py`)

This file contains the CanvasApiAdapter class that wraps the Canvas API client and provides methods for interacting with the Canvas API.

### 5. Server (`src/canvas_mcp/server.py`)

This file contains the MCP server implementation that registers and exposes the tools.

## Context Object Structure

The context object is passed to all tool functions and provides access to the database, API adapter, and sync service. Understanding its structure is crucial for working with the codebase.

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
    
    # Use these components to implement the tool
    # ...
```

## Tool Registration Process

Tools are registered using registration functions that add them to a tools dictionary. This process involves several steps:

1. **Define the tool function** in a module under `src/canvas_mcp/tools/`
2. **Create a registration function** in the same module
3. **Call the registration function** in `src/canvas_mcp/server.py`
4. **Import the registration function** in `scripts/extract_tools_test.py`

Example registration function:

```python
def register_my_tools(tools_dict):
    """Register my tools in the tools dictionary."""
    tools_dict["my_tool"] = my_tool
    return tools_dict
```

## Testing Workflow

### Step 1: Extract and Test Tools

Use `extract_tools_test.py` to extract and test tools:

```bash
# Test a specific tool
python scripts/extract_tools_test.py --tool my_tool --args '{"param1": "value1"}'

# Run all tests
python scripts/extract_tools_test.py --test
```

### Step 2: Test Integration

Use `test_tools_integration.py` to test integration between tools:

```bash
python scripts/diagnostics/test_tools_integration.py
```

### Step 3: Test in Direct Mode

Use `direct_tools_test.py` to test tools directly:

```bash
python scripts/direct_tools_test.py --test
```

## Database Schema

Understanding the database schema is essential for working with the codebase. Here's a simplified overview:

- **courses**: Stores course information
  - id (INTEGER): Primary key
  - canvas_course_id (INTEGER): Canvas course ID
  - course_code (TEXT): Course code
  - course_name (TEXT): Course name

- **assignments**: Stores assignment information
  - id (INTEGER): Primary key
  - course_id (INTEGER): Foreign key to courses.id
  - canvas_assignment_id (INTEGER): Canvas assignment ID
  - name (TEXT): Assignment name
  - due_at (TEXT): Due date

- **modules**: Stores module information
  - id (INTEGER): Primary key
  - course_id (INTEGER): Foreign key to courses.id
  - canvas_module_id (INTEGER): Canvas module ID
  - name (TEXT): Module name

- **module_items**: Stores module item information
  - id (INTEGER): Primary key
  - module_id (INTEGER): Foreign key to modules.id
  - canvas_item_id (INTEGER): Canvas item ID
  - title (TEXT): Item title
  - type (TEXT): Item type

- **announcements**: Stores announcement information
  - id (INTEGER): Primary key
  - course_id (INTEGER): Foreign key to courses.id
  - canvas_announcement_id (INTEGER): Canvas announcement ID
  - title (TEXT): Announcement title
  - message (TEXT): Announcement message

- **conversations**: Stores conversation information
  - id (INTEGER): Primary key
  - canvas_conversation_id (INTEGER): Canvas conversation ID
  - subject (TEXT): Conversation subject
  - message (TEXT): Conversation message

- **calendar_events**: Stores calendar event information
  - id (INTEGER): Primary key
  - course_id (INTEGER): Foreign key to courses.id
  - canvas_event_id (INTEGER): Canvas event ID
  - title (TEXT): Event title
  - description (TEXT): Event description
  - start_at (TEXT): Start date/time
  - end_at (TEXT): End date/time

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

## Troubleshooting Guide

### Issue: Tool not found

**Solution:**
- Check that the tool is registered in the tools dictionary
- Verify that the registration function is called in server.py
- Make sure the registration function is imported in extract_tools_test.py

### Issue: Database error

**Solution:**
- Check that the database is initialized
- Verify that foreign key constraints are enabled
- Ensure the database schema matches the expected schema

### Issue: API error

**Solution:**
- Check that API credentials are set
- Verify that the API adapter is properly initialized
- Check for rate limiting or permission issues

## Best Practices for AI Agents

1. **Start with the test utilities**: Use the test utilities to understand how tools work before modifying them.

2. **Understand the context object**: The context object is passed to all tools and provides access to essential components.

3. **Follow existing patterns**: Look at similar tools to understand the patterns used in the codebase.

4. **Test incrementally**: Test changes incrementally using the test utilities.

5. **Check database schema**: Understand the database schema before making changes that affect the database.

6. **Use proper error handling**: Follow the existing error handling patterns in the codebase.

7. **Document changes**: Add proper docstrings and comments to explain changes.

8. **Update tests**: Update tests to cover new functionality or changes to existing functionality.
