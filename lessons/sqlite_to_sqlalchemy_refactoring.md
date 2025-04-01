# SQLite to SQLAlchemy Refactoring Lessons

This document captures lessons learned during the refactoring from plain SQLite to SQLAlchemy ORM.

## Test Fixes Required

1. **Python typing.Any vs. SQLAlchemy types**
   - Issue: Using `Any` from Python's typing module caused `TypeError: Any cannot be instantiated` in SQLAlchemy functions expecting a database type.
   - Solution: Replace `typing.Any` with appropriate SQLAlchemy types (e.g., `String`) or with `object` in type annotations.

2. **Mock objects and SQLAlchemy**
   - Issue: When a MagicMock object is passed to SQLAlchemy, it causes `sqlite3.ProgrammingError: Error binding parameter: type 'MagicMock' is not supported`.
   - Solution: Set real string/int values on mock objects instead of letting them create nested MagicMock objects.

3. **Test isolation for mocks**
   - Issue: Using global mock objects led to state leakage between tests, causing assertion failures on call counts.
   - Solution: Create fresh mocks for each test in the setUp method and make them instance attributes.

4. **DateTime comparison with timezone info**
   - Issue: Comparing datetime objects with timezone info to naive datetime objects causes assertion failures.
   - Solution: Compare individual date/time components (year, month, day, etc.) instead of comparing full datetime objects.

5. **Using a MagicMock as a spec for another MagicMock**
   - Issue: Calling `MagicMock(spec=MagicMock_object)` causes a `unittest.mock.InvalidSpecError`.
   - Solution: Use real classes as specs, or create concrete classes to serve as specs.

## General SQLAlchemy Patterns

1. **SQLAlchemy Column Type References**
   - Use `from sqlalchemy.types import Integer, String, Text, DateTime, Float` when needed in test code.
   - For implementation code, these types are typically imported from `sqlalchemy` directly.

2. **Return Types in SQLAlchemy Functions**
   - Type annotations for functions that return dictionaries of query results should use `Dict[str, object]` rather than `Dict[str, Any]`.

3. **Session Creation Pattern**
   - In the client module, a session factory is passed in rather than creating sessions directly.
   - Tests pass in a test session factory bound to an in-memory database.

4. **ORM Query Result Conversion**
   - Row objects from queries need to be converted to dictionaries for API responses.
   - Use methods like `_asdict()` or custom helpers like `orm_to_dict()`.

## Test Framework Patterns

1. **Test Isolation**
   - Each test should clean up its own resources and not rely on setUp/tearDown from other tests.
   - Use instance attributes for mocks instead of module-level variables.

2. **Patch Dict Usage**
   - When using `patch.dict()` to mock modules, ensure proper cleanup in tearDown.
   - Reset patches in setUp to ensure a clean state for each test.

3. **Assertion Strategies**
   - Use `assert_any_call()` instead of strict ordering assertions when possible.
   - Be careful with `assert_called_once()` as it's very brittle to implementation changes.

4. **Mock Setup**
   - Set concrete attribute values on mocks instead of relying on nested MagicMocks.
   - Supply detailed specs to mocks to ensure they have the expected attributes and methods.
