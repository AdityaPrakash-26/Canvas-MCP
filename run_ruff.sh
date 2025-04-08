#!/bin/bash

echo "Running ruff check..."
ruff check --fix . || echo "Ruff check found issues but continuing..."

echo "Running ruff format..."
ruff format . || echo "Ruff format found issues but continuing..."

# Always exit with success
exit 0
