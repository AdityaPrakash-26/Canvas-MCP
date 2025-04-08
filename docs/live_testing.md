# Canvas-MCP Live Testing Guide

This document outlines the process for live testing the Canvas-MCP server, including how to set up a testing loop for rapid development and debugging.

## Prerequisites

- A working Canvas-MCP installation
- Valid Canvas API credentials
- Python 3.12+ environment with required dependencies

## The Development-Testing Loop

The development-testing loop for Canvas-MCP follows these steps:

1. Make code changes
2. Reset the database
3. Run the sync process
4. Test specific tools
5. Analyze results and repeat

### Step 1: Reset the Database

Before testing, it's often helpful to start with a clean database:

```bash
rm -f data/canvas_mcp.db && python -m src.canvas_mcp.init_db
```

This command:
- Removes the existing database file
- Initializes a new database with the current schema

### Step 2: Run the Sync Process

After resetting the database, sync data from Canvas:

```bash
python scripts/extract_tools_test.py --tool sync_canvas_data
```

This will:
- Fetch courses from Canvas
- Sync assignments, modules, announcements, and conversations
- Store all data in the local database

### Step 3: Test Specific Tools

Once data is synced, you can test specific tools:

```bash
python scripts/extract_tools_test.py --tool get_course_communications --args '{"course_id": 4}'
```

Replace `get_course_communications` with any tool you want to test, and provide appropriate arguments in JSON format.

### Step 4: Analyze and Iterate

After testing:
1. Check the output for errors or unexpected behavior
2. Make necessary code changes
3. Repeat the process from Step 1

## Common Testing Scenarios

### Testing Database Schema Changes

When modifying the database schema:

1. Update the schema in `src/canvas_mcp/init_db.py`
2. Update corresponding models in `src/canvas_mcp/models.py`
3. Update sync functions in `src/canvas_mcp/sync/` modules
4. Reset the database and run the sync process
5. Test affected tools

### Testing New Features

When adding new features:

1. Implement the feature code
2. Add necessary database tables/columns
3. Update sync functions if needed
4. Reset the database and run the sync process
5. Test the new feature with appropriate tools

## Troubleshooting

### Sync Process Errors

If the sync process fails:

1. Check the error message for specific issues
2. Verify that database schema matches the models
3. Check that all required fields are present in the database
4. Ensure sync functions handle all fields correctly

### Tool Execution Errors

If a tool fails to execute:

1. Check the error message for specific issues
2. Verify that the tool has access to required data
3. Check that the tool's arguments are valid
4. Ensure the database contains the expected data

## Example: Testing the Conversations Feature

Here's an example of testing the conversations feature:

```bash
# Reset the database
rm -f data/canvas_mcp.db && python -m src.canvas_mcp.init_db

# Sync data from Canvas
python scripts/extract_tools_test.py --tool sync_canvas_data

# Test the get_course_communications tool
python scripts/extract_tools_test.py --tool get_course_communications --args '{"course_id": 4}'
```

This process allows you to verify that:
1. The database schema correctly supports conversations
2. The sync process successfully fetches and stores conversations
3. The get_course_communications tool correctly retrieves and formats conversations

## Best Practices

1. **Incremental Testing**: Test one change at a time to isolate issues
2. **Database Inspection**: Use SQLite tools to inspect the database directly when needed
3. **Logging**: Enable detailed logging during testing to track the execution flow
4. **Error Handling**: Add robust error handling to make debugging easier
5. **Version Control**: Commit working changes frequently to maintain a stable baseline
