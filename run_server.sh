#!/bin/bash
# Kill any existing MCP processes
lsof -i :5173 -i :3000 | grep node | awk '{print $2}' | xargs kill 2>/dev/null || true

# Run the server
uv run -m canvas_mcp
