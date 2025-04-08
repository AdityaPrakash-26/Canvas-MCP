# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Build/Test/Lint Commands

- Run server: `uv run mcp dev src/canvas_mcp/server.py`
- Install to Claude: `uv run mcp install src/canvas_mcp/server.py`
- Run tests: `uv run pytest`
- Run single test: `uv run pytest path/to/test.py::test_function`
- Format code: `uv run ruff format .`
- Lint check: `uv run ruff check .`
- Lint fix: `uv run ruff check . --fix`
- Type check: `uv run mypy src`
- Run Canvas-MCP: `uv run --directory $DIRECTORY canvas-mcp`

## Code Style

- Line length: 88 chars max
- Type hints: Required for all code
- Docstrings: Required for public APIs
- Import style: Use absolute imports, sorted with `ruff`
- String quotes: Single quotes preferred
- Error handling: Use specific exception types, provide context
- Function size: Small, focused functions (< 50 lines)
- Naming: snake_case for variables/functions, PascalCase for classes

## Package Management

- ONLY use uv, NEVER pip
- Installation: `uv add package`
- Running tools: `uv run tool`
- Upgrading: `uv add --dev package --upgrade-package package`
- FORBIDDEN: `uv pip install`, `@latest` syntax

## Version Control Workflow

- Create feature branches before starting work
- Commit frequently with meaningful messages
- For issues: `git commit --trailer "Github-Issue:#<number>"`
- NEVER include "co-authored-by" or mention tooling
- Create detailed PR descriptions focusing on problem & solution

## MCP Server Requirements

- Use `FastMCP` from `mcp.server.fastmcp`
- Tools must be properly typed with docstrings
- Resources must have well-defined URI templates
- Follow existing patterns in `src/canvas_mcp`
- Document all APIs thoroughly

## Canvas-MCP Architecture

### Layered Architecture

- **Tools Layer** (`src/canvas_mcp/tools/`): Tool functions exposed to users
- **Sync Layer** (`src/canvas_mcp/sync/`): Synchronization of data from Canvas API
- **Utilities Layer** (`src/canvas_mcp/utils/`): Utility functions and classes
- **API Adapter** (`src/canvas_mcp/canvas_api_adapter.py`): Wrapper for Canvas API
- **Server** (`src/canvas_mcp/server.py`): MCP server implementation

### Database Schema

- **Terms**: Academic terms information
- **Courses**: Core course information
- **Syllabi**: Syllabus content for each course
- **Assignments**: Assignment details and deadlines
- **Modules**: Course content organization
- **Module_Items**: Individual items within modules
- **Announcements**: Course announcements
- **Conversations**: Direct messages and conversations
- **Calendar_Events**: Course calendar events

### Key Components

- **DatabaseManager**: Handles database operations
- **CanvasApiAdapter**: Wraps the Canvas API client
- **SyncService**: Orchestrates data synchronization
- **Tool Functions**: Implement specific functionality

## Testing

### Core Test Utilities

- **Extract Tools Test**: `python scripts/extract_tools_test.py`
  - Test tools without running the full server
  - Use `--test` flag to run all tests
  - Use `--tool tool_name` to test a specific tool
  - Use `--list` to see all available tools

- **Direct Tools Test**: `python scripts/direct_tools_test.py`
  - Test tools directly without server overhead
  - Use `--test` flag to run all tests

- **Integration Tests**: `python scripts/diagnostics/test_tools_integration.py`
  - Test the full workflow from sync to tool usage
  - Verifies data consistency across tools

- **Run All Tests**: `python scripts/run_all_tests.py`
  - Comprehensive test suite that runs all tests
  - Use `--verbose` for detailed output
  - Use `--fix` to attempt to fix identified issues

### Testing Best Practices

- Always run tests before making changes to understand current state
- Use a separate test database, not the main application database
- Wipe the database before running integration tests
- Use direct SQLite queries to verify database state during testing
- Mock boundaries not internals, assert on outcomes not mocks

## Documentation

- **ALWAYS check README files** in each directory upon initialization
- Key documentation files:
  - `docs/db_schema_updated.md`: Database schema documentation
  - `docs/ARCHITECTURE.md`: System architecture overview
  - `docs/live_testing.md`: Testing procedures
  - `scripts/README.md`: Testing utilities documentation
  - `scripts/AI_AGENT_GUIDE.md`: Specific guidance for AI agents

- Document all APIs thoroughly with proper docstrings
- Update documentation when making significant changes

## Development Workflow

### Adding a New Tool

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

### Database Operations

- Initialize database with `create_database()` from `src/canvas_mcp/init_db.py`
- Enable foreign key constraints during database initialization
- Use `DatabaseManager` for database operations
- Create proper context object for tools:
  ```python
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

## Troubleshooting

### Common Issues

- **Tool Not Found**:
  - Check that the tool is properly registered in `src/canvas_mcp/server.py`
  - Verify that the registration function is imported in `scripts/extract_tools_test.py`
  - Make sure the tool name matches exactly (case-sensitive)

- **Database Errors**:
  - Ensure the database is initialized with `create_database()`
  - Check that foreign key constraints are enabled
  - Verify that the database schema matches the expected schema for the tool

- **API Errors**:
  - Check that Canvas API credentials are set in the environment variables
  - Verify that the API adapter is properly initialized
  - Check for rate limiting or permission issues

### Debugging Tips

- Use `logger.debug()` for detailed logging during development
- Check the database directly with SQLite queries to verify state
- Use the test utilities to isolate and debug specific components
- Canvas-MCP testing loop: reset DB, sync data, test tools, analyze results, repeat

## Information Gathering

- Search `library_docs` for reference documentation
- Check the Canvas API documentation at https://canvas.instructure.com/doc/api/
- Create new lessons in `lessons/` when you learn something
- Document mistakes for future reference