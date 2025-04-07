#!/bin/bash
# Script to run the Canvas MCP server

# Kill any existing MCP processes
lsof -i :5173 -i :3000 | grep node | awk '{print $2}' | xargs kill 2>/dev/null || true

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if we have uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed or not in the PATH."
    echo "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Run the server with uv
echo "Starting Canvas MCP server..."
echo "URL: http://127.0.0.1:6274"
echo "Press Ctrl+C to stop"
echo "--------------------------------"

# Run the server with uv
uv run mcp dev src/canvas_mcp/server.py
