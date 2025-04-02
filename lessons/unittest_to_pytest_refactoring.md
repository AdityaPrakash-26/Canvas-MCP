# Unittest to Pytest Refactoring and Mock Reduction

This document captures the approach and lessons learned while refactoring the Canvas-MCP tests from unittest to pytest, with a focus on reducing mock usage and improving test reliability.

## Refactoring Approach

### Directory Structure
We organized tests into subdirectories by component:
- `tests/test_canvas/` - Tests for Canvas API client functionality
- `tests/test_db/` - Tests for database operations
- `tests/test_server/` - Tests for MCP server endpoints

Each directory contains:
- `__init__.py` - Package marker
- `conftest.py` (where needed) - Component-specific fixtures
- Test modules organized by functionality

### Mock Reduction Strategy
1. **Identify External Boundaries**: Canvas API is the main external dependency
2. **Use In-Memory Databases**: SQLAlchemy with SQLite for DB tests
3. **Focus on Outcomes**: Test data was created, not how it was created
4. **Use Realistic Test Data**: Complete objects rather than minimal stubs

### Key Changes

1. **From Class-Based to Function-Based Tests**
   - Converted unittest `TestCase` classes to standalone pytest functions
   - Replaced `setUp`/`tearDown` with pytest fixtures
   - Converted assertion methods to pytest's `assert` statements

2. **From Global Mocks to Isolated Fixtures**
   - Moved from global mock objects to pytest fixtures
   - Each test gets fresh fixtures, preventing state leakage
   - Better isolation between tests

3. **From Implementation Details to Outcomes**
   - Reduced assertions about method calls
   - Increased assertions about resulting data
   - Focused on "what" not "how"

4. **From Deep Mocking to Boundary Mocking**
   - Only mock the Canvas API, not our own code
   - Let internal components do their actual work
   - Use real DB interactions via in-memory SQLite

## Mock Reduction Examples

### Before: Excessive Mocking
```python
def test_sync_courses(self):
    # Mock user and courses
    mock_user = MagicMock(spec=CanvasUser)
    mock_user.id = 999
    self.mock_canvas.get_current_user.return_value = mock_user
    
    mock_course = MagicMock(spec=CanvasCourse)
    mock_course.id = 12345
    # Many more attribute settings...
    
    # Excessive assertions about implementation details
    mock_user.get_courses.assert_called_once_with(include=["term", "teachers"])
    self.mock_canvas.get_course.assert_any_call(12345, include=["syllabus_body", "teachers"])
    # More assertions about how things were done...
```

### After: Outcome-Focused Testing
```python
def test_sync_courses_integration(canvas_client, db_session):
    # Only mock the external API
    mock_user = MagicMock()
    mock_user.id = 999
    canvas_client.canvas.get_current_user.return_value = mock_user
    
    # Create realistic course objects
    mock_course1 = MagicMock()
    mock_course1.id = 12345
    # Attributes set with realistic values...
    
    # Set up API responses
    mock_user.get_courses.return_value = [mock_course1, mock_course2]
    
    # Run the sync
    synced_ids = canvas_client.sync_courses()
    
    # Focus on outcomes, not implementation
    assert len(synced_ids) == 2
    
    # Verify database state directly
    courses = db_session.query(Course).order_by(Course.canvas_course_id).all()
    assert len(courses) == 2
    assert courses[0].canvas_course_id == 12345
    # More assertions about the actual data...
```

## Lessons Learned

### Database Session Management
1. **Session Isolation**: Each test needs its own isolated database session
   - In-memory SQLite databases are perfect for this
   - Create a fresh session for each test to avoid cross-test pollution

2. **Session Refreshing**: Important when testing changes made by functions under test
   - When a function creates its own session and makes changes, your test session won't see those changes automatically
   - Use `session.expire_all()` or `session.refresh(obj)` before assertions to see changes
   - Example issue: The `opt_out_course` test initially failed because the test session couldn't see the changes made by the function

3. **Transaction Management**: Pay attention to commits and rollbacks
   - SQLAlchemy tests need proper transaction handling
   - Use try/finally to ensure sessions are properly closed

### Fixture Design
1. **Fixture Scope**: Choose the right scope for performance vs isolation
   - Function scope provides maximum isolation but can be slower
   - Session/module scope is faster but requires careful state management

2. **Fixture Dependencies**: Build a hierarchy of fixtures
   - Start with low-level fixtures (e.g., DB engine)
   - Build higher-level fixtures on top (e.g., sessions, then populated data)
   - Example: `memory_db_engine` → `memory_db_session` → `canvas_client`

3. **Realistic Test Data**: Create fixtures that mirror real-world scenarios
   - Don't use empty or minimal test objects
   - Set all relevant attributes that would be present in real usage

### Effective Mocking
1. **Only Mock External Boundaries**: Identify what's truly "external"
   - External APIs (Canvas API in our case)
   - File systems, network services, etc.
   - Never mock your own internal components

2. **Return Structures vs Return Behavior**: Focus on structures, not behavior
   - Mock return values should mirror real-world data structures
   - Don't mock complex behavior unless absolutely necessary

3. **Verify Outcomes, Not Interactions**: Change your assertion focus
   - Less emphasis on "this method was called with these args"
   - More emphasis on "the end result is correct in the database"

### Implementation Challenges
1. **Method Naming Consistency**: Watch for mismatches between API and implementation
   - Example: Tests expected `get_courses` but implementation had `sync_courses`

2. **Date Handling**: SQLAlchemy requires proper Python datetime objects
   - String dates from APIs need proper conversion
   - Time zones can cause subtle comparison issues

3. **Test Independence**: Each test should be fully self-contained
   - Avoid shared state between tests
   - Reset mocks between tests (or use fresh ones)
   - Clean up any persisted data

4. **Testing Consistency vs. Testing Everything**: Find the right balance
   - Consider what actually needs testing (core functionality vs implementation details)
   - Group related tests together for better organization and maintenance

## Benefits of the Refactoring

1. **Improved Test Reliability**
   - Less coupling to implementation details
   - Tests won't break with internal refactoring
   - Reduced "test state" leakage between tests

2. **Better Test Organization**
   - Modular test structure by component
   - Easier to find relevant tests
   - Reduced test interdependence

3. **Clearer Testing Intent**
   - Tests clearly show what functionality is being verified
   - Less focus on mechanics, more on outcomes
   - Easier to understand test failures

4. **More Realistic Test Scenarios**
   - Tests operate closer to how real code runs
   - Integration-style tests verify component interactions
   - Less "test reality distortion" from excessive mocking

5. **Improved Developer Experience**
   - More intuitive test structure
   - Faster feedback on what's actually broken
   - Easier to add new tests

## Testing Guidelines Going Forward

When writing new tests:

1. **Mock only at external boundaries**:
   - Canvas API, external web services, etc.
   - Never mock internal code

2. **Use in-memory databases for DB testing**:
   - Fast, realistic, and isolated

3. **Focus assertions on outcomes**:
   - Verify data was created/updated correctly
   - Verify side effects occurred
   - Avoid asserting method call details unless necessary

4. **Maintain fixture isolation**:
   - Each test should get fresh fixtures
   - Avoid fixture state leakage
   - Use function scope for fixtures when possible

5. **Write tests to survive refactoring**:
   - Tests should verify behavior, not implementation
   - Internal code can change without breaking tests
   - Focus on stable APIs and data structures

