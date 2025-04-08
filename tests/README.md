# Canvas-MCP Testing Guide

## Testing Architecture

Canvas-MCP uses a comprehensive testing approach with both unit tests and integration tests:

- **Unit Tests**: Located in `tests/unit/`, these test individual components in isolation using fakes and mocks.
- **Integration Tests**: Located in `tests/integration/`, these test the system as a whole using real Canvas API responses.

## Test Data

- Integration tests use course SP25_CS_540_1 (ID: 146127) as the primary test course.
- Tests should not hardcode internal IDs since different students will run these tests.
- Tests use a separate test database, not the main application database.
- Tests don't recreate the database for each test to save time (as long as tests don't have destructive operations).

## Running Tests

### Running All Tests

```bash
python -m pytest
```

### Running Specific Test Files

```bash
python -m pytest tests/unit/test_canvas_client.py
python -m pytest tests/integration/test_courses.py
```

### Running Specific Test Functions

```bash
python -m pytest tests/unit/test_canvas_client.py::TestCanvasClient::test_sync_courses_filters_by_enrollment_state
```

## Test Fixtures

Canvas-MCP uses fixtures to provide test data and setup/teardown functionality:

- **Unit Test Fixtures**: Located in `tests/unit/conftest.py` and `tests/conftest.py`.
- **Integration Test Fixtures**: Located in `tests/integration/conftest.py` and `tests/conftest.py`.
- **Fake Canvas API**: Located in `tests/fakes/fake_canvasapi.py`.
- **Test Data**: Located in `tests/fakes/fixtures/`.

### Generating Fixtures

To generate new fixtures from real Canvas API responses, use the `tests/generate_fixtures.py` script:

```bash
python tests/generate_fixtures.py
```

## Troubleshooting Common Issues

### Course Filtering Issues

When troubleshooting course filtering issues (e.g., dropped courses still showing up), consider:

1. **Enrollment State Filtering**: Canvas API uses `enrollment_state` parameter to filter courses by enrollment status (active, invited, completed, deleted).
   - In `canvas_client.py`, we use `enrollment_state='active'` to filter out dropped courses.
   - Test this with: `user.get_courses(enrollment_state='active')`

2. **Term Filtering**: Canvas API returns courses from all terms by default.
   - In `canvas_client.py`, we use `term_id=-1` to filter to only the most recent term.
   - This is implemented in the `sync_courses` method.

3. **Database Persistence**: Courses synced in previous runs may still be in the database.
   - When testing filtering changes, clean the database first: `DELETE FROM courses`

### Test Data Discrepancies

If tests are failing due to unexpected data:

1. **Fixture Issues**: Ensure fixtures have the necessary attributes for testing.
   - For enrollment state testing, courses need `enrollments` with `enrollment_state` values.
   - For term filtering, courses need `enrollment_term_id` values.

2. **Fake API Implementation**: Check if the fake Canvas API correctly implements filtering.
   - The `get_courses` method in `FakeUser` class should properly filter by `enrollment_state` and other parameters.

### Integration Test Setup

For integration tests to work properly:

1. **Environment Variables**: Set `CANVAS_API_KEY` and `CANVAS_API_URL` before running tests.
2. **Test Database**: Use a separate test database (configured in `conftest.py`).
3. **Test Course**: Ensure the test course (SP25_CS_540_1) is accessible with your API key.

## Case Study: Fixing Course Filtering

We recently fixed an issue where dropped courses were still being displayed. Here's the process we followed:

1. **Problem Identification**:
   - Dropped courses (like Info Visualization) were still showing up in the course list.
   - The user expected to see only 4 current semester courses but was seeing 9.

2. **Investigation**:
   - Created test scripts to understand how Canvas API handles enrollment states.
   - Discovered that `enrollment_state='active'` filters out dropped courses.
   - Found that term filtering was not enabled by default.

3. **Solution**:
   - Modified `sync_courses` to use `enrollment_state='active'` when fetching courses.
   - Changed the default `term_id` parameter from `None` to `-1` to filter by most recent term.

4. **Testing**:
   - Created scripts to verify the fix with real Canvas API.
   - Updated unit tests to verify enrollment state and term filtering.
   - Ensured integration tests pass with the new filtering behavior.

5. **Verification**:
   - Confirmed that dropped courses no longer appear in the course list.
   - Verified that only current semester courses (4 courses) are displayed.

## Testing Best Practices

1. **Mock Boundaries, Not Internals**: Test the behavior of components, not their implementation details.
2. **Assert on Outcomes, Not Mocks**: Verify the end result, not how it was achieved.
3. **Use Realistic Test Data**: Generate fixtures from real API responses when possible.
4. **Clean Database Before Tests**: When testing database operations, start with a clean state.
5. **Test Edge Cases**: Include tests for empty results, error conditions, and boundary cases.
6. **Avoid Hardcoding**: Don't hardcode IDs or values that might change between environments.
7. **Balance Test Coverage**: Use both unit and integration tests appropriately.
