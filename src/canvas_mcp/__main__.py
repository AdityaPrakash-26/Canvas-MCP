"""
Main entry point for the canvas_mcp package.
This allows running the package with `python -m canvas-mcp` or with `uv run src/canvas-mcp`.
"""
import uvloop

uvloop.install()

from canvas_mcp.server import mcp

if __name__ == "__main__":

    # Turn profiling on

    mcp.run()

    # Turn profiling off
