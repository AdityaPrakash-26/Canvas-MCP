#!/bin/bash
# Run the refactored tests
echo "Running refactored tests..."

# Canvas tests
echo "Running canvas client tests..."
uv run pytest tests/test_canvas/test_canvas_client_integration.py -v

# DB tests
echo "Running database initialization tests..."
uv run pytest tests/test_db/test_init_db.py -v

# Server tests
echo "Running server endpoints tests..."
uv run pytest tests/test_server/ -v
