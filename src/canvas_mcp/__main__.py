"""
Main entry point for the canvas_mcp package.
This allows running the package with `python -m canvas_mcp` or with `uv run src/canvas_mcp`.
"""

from canvas_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
