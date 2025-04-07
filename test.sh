#!/bin/bash

# Run all tests
uv run pytest -v

# Run specific test categories
# uv run pytest -v tests/test_db/
# uv run pytest -v tests/test_canvas/
# uv run pytest -v tests/test_server/

# Run a specific test file
# uv run pytest -v tests/test_db/test_init.py

# Run a specific test
# uv run pytest -v tests/test_db/test_init.py::test_create_database
