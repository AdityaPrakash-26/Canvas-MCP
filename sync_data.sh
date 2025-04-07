#!/bin/bash
# Script to sync data from Canvas to the local database

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if we have uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed or not in the PATH."
    echo "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Running the server for a moment to sync data
echo "Starting Canvas MCP server temporarily to sync data..."
echo "This will take a few seconds..."

# Launch server in background
uv run mcp dev src/canvas_mcp/server.py &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Make a request to sync data
echo "Syncing data from Canvas..."
RESULT=$(curl -s "http://127.0.0.1:6274/invoke/sync_canvas_data" -H "Content-Type: application/json" -d '{"force": true}')

# Stop the server
kill $SERVER_PID

# Display results
echo "Sync complete! Results:"
echo $RESULT | python3 -m json.tool

exit 0
