# Canvas-MCP Refactoring Guide

This document provides guidance on refactoring the Canvas-MCP codebase, based on lessons learned during the transition from an object-oriented approach to a more functional approach with explicit dependency injection.

## Architectural Changes

### From Object-Oriented to Functional

The Canvas-MCP codebase has been refactored from a monolithic `CanvasClient` class with instance methods to a more modular architecture with:

1. **SyncService**: Orchestrates synchronization operations
2. **CanvasApiAdapter**: Handles Canvas API interactions
3. **DatabaseManager**: Manages database connections and operations

This change improves testability, separation of concerns, and makes the code more maintainable.

## Function Signature Changes

When refactoring from instance methods (using `self`) to standalone functions (using explicit parameters), follow these guidelines:

### 1. Update Function Signatures

```python
# Before: Instance method
def sync_courses(self, user_id: str | None = None, term_id: int | None = -1) -> list[int]:
    # Implementation using self.api_adapter, self.db_manager, etc.

# After: Standalone function
def sync_courses(sync_service, user_id: str | None = None, term_id: int | None = -1) -> list[int]:
    # Implementation using sync_service.api_adapter, sync_service.db_manager, etc.
```

### 2. Update All Call Sites

Ensure all places where the function is called are updated with the new parameter structure:

```python
# Before
course_ids = self.sync_courses(user_id, term_id)

# After
course_ids = sync_service.sync_courses(user_id, term_id)
```

### 3. Handle Database Connection Wrappers

Pay special attention to functions that use database connection wrappers:

```python
# Before refactoring (instance method)
def _wrap_with_connection(self, func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return self.db_manager.with_connection(func)(self, *args, **kwargs)
    return wrapper

# After refactoring (standalone function)
def _wrap_with_connection(self, func):
    @wraps(func)
    def wrapper(sync_service, *args, **kwargs):
        # Create a new function that takes conn and cursor as first arguments
        def db_func(conn, cursor, *inner_args, **inner_kwargs):
            return func(sync_service, conn, cursor, *inner_args, **inner_kwargs)
        
        # Call the database manager's with_connection with our new function
        return self.db_manager.with_connection(db_func)(*args, **kwargs)
    return wrapper
```

## Database Operations

### Direct Database Access

For simpler functions, consider using direct database access instead of wrappers:

```python
# Direct database access
conn, cursor = sync_service.db_manager.connect()
try:
    # Database operations
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    conn.commit()
    return dict(course) if course else None
except Exception as e:
    conn.rollback()
    logger.error(f"Error getting course: {e}")
    return None
finally:
    conn.close()
```

### Date Handling in SQLite

When working with dates in SQLite:

1. **Timezone Awareness**: Be aware that SQLite date functions may not handle timezone information correctly.
2. **String Manipulation**: For reliable date comparison, consider using string manipulation functions like `substr()`:

```python
# More reliable date comparison in SQLite
query = """
SELECT * FROM assignments
WHERE substr(due_date, 1, 10) >= ?
AND substr(due_date, 1, 10) <= ?
"""
```

## Testing Considerations

### Updating Test Fixtures

When refactoring, ensure test fixtures are updated to match the new architecture:

1. **Replace `canvas_client` with `sync_service` and `api_adapter`** in test fixtures
2. **Update mock objects** to match the new function signatures
3. **Check database initialization** in tests to ensure proper setup

### Troubleshooting Test Failures

When tests fail after refactoring:

1. **Examine Root Causes**: Look for missing database records or incorrect parameter passing
2. **Use Diagnostic Tools**: Check the `scripts/` directory for diagnostic tools
3. **Fix Underlying Issues**: Address the root cause rather than modifying tests to work around issues

## Best Practices

1. **Incremental Changes**: Make small, focused changes and test after each change
2. **Consistent Parameter Naming**: Use consistent parameter names across related functions
3. **Error Handling**: Ensure proper error handling, especially for database operations
4. **Documentation**: Update documentation to reflect architectural changes
5. **Test Coverage**: Maintain or improve test coverage during refactoring
