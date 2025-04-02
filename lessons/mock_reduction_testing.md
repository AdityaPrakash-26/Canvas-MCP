# Reducing Mock Usage in Tests

This document captures the approach and lessons learned during the refactoring of tests to reduce mock usage in the Canvas-MCP project.

## Key Issues Found

1. **Date Format Issues**: Fixtures were passing string dates to SQLAlchemy models which expect Python `datetime` objects. This causes `TypeError: SQLite DateTime type only accepts Python datetime and date objects as input`.

2. **Mocking Implementation Details**: Many tests were mocking the internals of the `CanvasClient` class instead of focusing on testing outcomes.

3. **Method Name Mismatches**: Tests were trying to call methods like `get_courses`, `get_assignments`, etc., but the implementation uses `sync_*` method names.

4. **Canvas API URL Mismatch**: Tests expect "https://canvas.example.com" but the implementation defaults to "https://canvas.instructure.com".

## Approach to Reducing Mock Usage

1. **Identify boundary points**: External API calls to Canvas are appropriate for mocking. Internal interactions between our components should be tested with real implementations.

2. **Use in-memory databases**: Use SQLAlchemy with SQLite in-memory databases for testing database interactions rather than mocking them.

3. **Focus on outcomes, not interactions**: Test that functions produce the correct results, not that they call specific methods in a specific order.

4. **Create realistic test data**: Provide complete, valid data structures to tests rather than minimal mocks that only have the fields being tested.

## Examples of Mock Reduction Strategies

### Before: Excessive Mocking
```python
def test_sync_all(canvas_client, mock_user, mock_course, db_session):
    # Mock individual methods to test coordination
    canvas_client.user = mock_user
    canvas_client.get_courses = MagicMock(return_value=[mock_course])
    canvas_client.sync_course = MagicMock(return_value={"status": "success", "course_id": 1})
    canvas_client.sync_assignments = MagicMock(return_value={"status": "success", "count": 5})
    canvas_client.sync_modules = MagicMock(return_value={"status": "success", "modules_count": 3, "items_count": 10})
    canvas_client.sync_announcements = MagicMock(return_value={"status": "success", "count": 2})

    # Execute the sync
    result = canvas_client.sync_all(db_session)

    # Verify method calls
    canvas_client.get_courses.assert_called_once()
    canvas_client.sync_course.assert_called_once_with(mock_course, db_session)
    canvas_client.sync_assignments.assert_called_once()
    canvas_client.sync_modules.assert_called_once()
    canvas_client.sync_announcements.assert_called_once()
```

### After: Outcome-Focused Testing
```python
def test_sync_all_integration(canvas_client, mock_canvas_api, mock_course, db_session):
    # Only mock external API (Canvas)
    # Configure canvas_client to return mock course from Canvas API
    mock_user = MagicMock()
    mock_user.get_courses.return_value = [mock_course]
    mock_canvas_api.get_current_user.return_value = mock_user
    
    # Execute the sync with real internal components
    result = canvas_client.sync_all(db_session)
    
    # Verify database outcome (the real test is that data is correctly created)
    course = db_session.query(Course).filter_by(canvas_course_id=mock_course.id).first()
    assert course is not None
    
    # Check overall result status
    assert result["status"] == "success"
```
