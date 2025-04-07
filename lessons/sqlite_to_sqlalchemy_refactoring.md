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

## Lessons Learned

- We should follow the testing guidelines for mocks:

Mocks can be useful but carry significant risks. Follow these principles carefully:

### When to Use Mocks:
- External calls that are slow, flaky, or unreliable.
- Interactions with expensive or side-effect-producing APIs.
- Testing rare or difficult-to-reproduce conditions (e.g., network errors).

### Best Practices:
- **Mock at boundaries:** Only mock external dependencies or APIs; never your internal methods or functions.
- **Assert outcomes, not interactions:** Test behavior, not exact method calls or internal implementation details.
- **Prefer realistic fakes/stubs:** Use in-memory databases or stable API fakes over mocking whenever possible.
- **Balance mocks with integration tests:** Ensure integration tests exist to validate your mocks and confirm real-world behavior.

Always critically evaluate:

> "Are my mocks reflecting real-world behavior, or are they obscuring potential issues?"
