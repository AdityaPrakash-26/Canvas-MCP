"""
Main entry point for the canvas_mcp package.
This allows running the package with `python -m canvas_mcp` or with `uv run src/canvas_mcp`.
"""
import signal

from canvas_mcp.server import mcp
import sys
import logging
from server import handle_shutdown_signal

logger = logging.getLogger("canvas_mcp")


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        mcp.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting gracefully.")
        sys.exit(0)
