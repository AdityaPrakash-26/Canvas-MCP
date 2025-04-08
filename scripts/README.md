# Canvas-MCP Testing Utilities

This directory contains essential testing utilities for the Canvas-MCP application. These tools are designed to help developers test, debug, and extend the functionality of Canvas-MCP.

## Core Testing Utilities

The following are the most important testing utilities that should be used for development and testing:

### 1. Extract Tools Test (`extract_tools_test.py`)

This is the primary utility for testing Canvas MCP tools. It extracts tool functions from the MCP server and allows you to test them directly.

**Key Features:**
- Extract and test tools without running the full server
- Interactive mode for manual testing
- Automated testing of all tools
- Support for testing individual tools with custom arguments

**Usage:**
```bash
# Interactive mode
python scripts/extract_tools_test.py

# Run all tests
python scripts/extract_tools_test.py --test

# List all available tools
python scripts/extract_tools_test.py --list

# Test a specific tool
python scripts/extract_tools_test.py --tool get_course_list

# Test a tool with arguments
python scripts/extract_tools_test.py --tool get_course_modules --args '{"course_id": 1}'
```

### 2. Direct Tools Test (`direct_tools_test.py`)

This utility directly tests Canvas MCP tools without using the client-server architecture. It's useful for debugging and development.

**Key Features:**
- Direct testing of tools without server overhead
- Interactive mode for manual testing
- Automated testing of all tools

**Usage:**
```bash
# Interactive mode
python scripts/direct_tools_test.py

# Run all tests
python scripts/direct_tools_test.py --test

# Test a specific tool
python scripts/direct_tools_test.py --tool get_course_list
```

### 3. Tools Integration Test (`diagnostics/test_tools_integration.py`)

This utility tests the integration between different tools and components to ensure they work together correctly.

**Key Features:**
- Tests the full workflow from sync to tool usage
- Verifies data consistency across tools
- Tests error handling and edge cases

**Usage:**
```bash
# Run the integration tests
python scripts/diagnostics/test_tools_integration.py

# Run with verbose logging
python scripts/diagnostics/test_tools_integration.py --verbose
```

## Development Workflow

### Adding a New Tool

When adding a new tool to Canvas-MCP, follow these steps:

1. **Create the tool module**:
   - Add a new file in `src/canvas_mcp/tools/` or use an existing one
   - Implement the tool function with proper type hints and docstrings
   - Create a registration function (e.g., `register_my_tools`)

2. **Register the tool**:
   - Import the registration function in `src/canvas_mcp/server.py`
   - Call the registration function in the server setup

3. **Update test utilities**:
   - Import the registration function in `scripts/extract_tools_test.py`
   - Add the tool to the test_tools function in `scripts/extract_tools_test.py`
   - Update `scripts/diagnostics/test_tools_integration.py` to test the new tool

4. **Test the tool**:
   - Run `python scripts/extract_tools_test.py --tool your_new_tool`
   - Run `python scripts/extract_tools_test.py --test` to test all tools
   - Run `python scripts/diagnostics/test_tools_integration.py` for integration testing

### Testing Database Operations

For tools that interact with the database:

1. **Initialize the database**:
   ```python
   from src.canvas_mcp.init_db import create_database
   create_database("test_database.db")
   ```

2. **Create a database manager**:
   ```python
   from src.canvas_mcp.utils.db_manager import DatabaseManager
   db_manager = DatabaseManager("test_database.db")
   ```

3. **Create a context object**:
   ```python
   from types import SimpleNamespace
   ctx = SimpleNamespace(
       request_context=SimpleNamespace(
           lifespan_context={
               "db_manager": db_manager,
               "api_adapter": api_adapter,
               "sync_service": sync_service,
           }
       )
   )
   ```

4. **Call the tool with the context**:
   ```python
   result = your_tool(ctx, arg1=value1, arg2=value2)
   ```

## Common Issues and Solutions

### Tool Not Found

If a tool is not found when testing:
- Check that the tool is properly registered in `src/canvas_mcp/server.py`
- Verify that the registration function is imported in `scripts/extract_tools_test.py`
- Make sure the tool name matches exactly (case-sensitive)

### Database Errors

If you encounter database errors:
- Ensure the database is initialized with `create_database()`
- Check that foreign key constraints are enabled
- Verify that the database schema matches the expected schema for the tool

### API Errors

If you encounter API errors:
- Check that your Canvas API credentials are set in the environment variables
- Verify that the API adapter is properly initialized
- Check for rate limiting or permission issues

## Additional Resources

- **Canvas API Documentation**: [https://canvas.instructure.com/doc/api/](https://canvas.instructure.com/doc/api/)
- **Canvas-MCP Documentation**: See the main README.md in the project root
- **Testing Documentation**: See `docs/testing.md` for more detailed testing information
