"""
Main entry point for the canvas_mcp package.
Ensures database is checked/initialized before starting the server.
"""
import os
import sys

# Ensure the project root is in the path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import necessary components
# The import of database itself triggers the init check
from canvas_mcp.database import DB_PATH, init_db, engine
from canvas_mcp.server import mcp

def main():
    """Main execution function."""
    print("Starting Canvas MCP...")

    # Double-check database initialization (database.py should handle this, but belts and suspenders)
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) == 0:
        print(f"Database at {DB_PATH} appears missing or empty. Running init...")
        try:
            # Need to ensure models are loaded before init_db if called explicitly here
            from canvas_mcp import models # pylint: disable=import-outside-toplevel, W0611
            init_db(engine)
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error during explicit database initialization: {e}")
            print("Please check database configuration and permissions.")
            sys.exit(1)
    else:
        print(f"Database found at {DB_PATH}.")

    # Run the MCP server
    print("Launching MCP server...")
    mcp.run()

if __name__ == "__main__":
    main()