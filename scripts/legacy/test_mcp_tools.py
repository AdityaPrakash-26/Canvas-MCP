#!/usr/bin/env python3
"""
Canvas MCP Tools Tester

This script provides a client for testing the Canvas MCP server tools.
It connects to the server, lists available tools, and allows you to interact with them.

Usage:
    python scripts/test_mcp_tools.py [--server PATH]

Options:
    --server        Path to the server script (default: src/canvas_mcp/server.py)
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
except ImportError:
    print("MCP SDK not found. Installing...")
    import subprocess

    try:
        # Try using uv first
        subprocess.check_call(["uv", "pip", "install", "mcp"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fall back to pip if uv is not available
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters, stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("canvas_mcp_tester")


class CanvasMCPTester:
    """Client for testing the Canvas MCP server tools."""

    def __init__(self, server_path: str):
        """
        Initialize the Canvas MCP tester.

        Args:
            server_path: Path to the server script
        """
        self.server_path = server_path
        self.tools = []

    async def list_tools(self, session):
        """
        List available tools.

        Args:
            session: MCP client session

        Returns:
            List of tools
        """
        tools_response = await session.list_tools()
        self.tools = tools_response.tools

        logger.info(f"Available tools: {', '.join(tool.name for tool in self.tools)}")

        return self.tools

    async def call_tool(self, session, tool_name: str, arguments=None):
        """
        Call a tool on the server.

        Args:
            session: MCP client session
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool result
        """
        if arguments is None:
            arguments = {}

        try:
            result = await session.call_tool(name=tool_name, arguments=arguments)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}

    async def test_all_tools(self, session):
        """
        Test all available tools with sample arguments.

        Args:
            session: MCP client session
        """
        logger.info("Testing all available tools...")

        results = {}

        # Get course list first to use in other tests
        logger.info("Testing get_course_list...")
        courses_result = await self.call_tool(session, "get_course_list")
        results["get_course_list"] = courses_result

        # Check if we have courses
        if not courses_result or (
            isinstance(courses_result, dict) and "error" in courses_result
        ):
            logger.warning(
                "No courses found or error occurred. Some tests may be skipped."
            )
            return results

        # Parse the course list from the content if needed
        course_list = courses_result
        if hasattr(courses_result, "content") and courses_result.content:
            for content_item in courses_result.content:
                if hasattr(content_item, "text"):
                    try:
                        course_list = json.loads(content_item.text)
                        break
                    except json.JSONDecodeError:
                        pass

        # Get the first course ID for testing
        try:
            course_id = course_list[0]["id"]
            logger.info(f"Using course ID {course_id} for testing")

            # Test course details
            logger.info("Testing get_course_details...")
            results["get_course_details"] = await self.call_tool(
                session, "get_course_details", {"course_id": course_id}
            )

            # Test assignments
            logger.info("Testing get_course_assignments...")
            results["get_course_assignments"] = await self.call_tool(
                session, "get_course_assignments", {"course_id": course_id}
            )

            # Test upcoming deadlines
            logger.info("Testing get_upcoming_deadlines...")
            results["get_upcoming_deadlines"] = await self.call_tool(
                session, "get_upcoming_deadlines", {"days": 30}
            )

            # Test modules
            logger.info("Testing get_course_modules...")
            results["get_course_modules"] = await self.call_tool(
                session, "get_course_modules", {"course_id": course_id}
            )

            # Test modules with items
            logger.info("Testing get_course_modules with include_items=True...")
            results["get_course_modules_with_items"] = await self.call_tool(
                session,
                "get_course_modules",
                {"course_id": course_id, "include_items": True},
            )

            # Test syllabus
            logger.info("Testing get_syllabus...")
            results["get_syllabus"] = await self.call_tool(
                session, "get_syllabus", {"course_id": course_id}
            )

            # Test announcements
            logger.info("Testing get_course_announcements...")
            results["get_course_announcements"] = await self.call_tool(
                session, "get_course_announcements", {"course_id": course_id}
            )

            # Test files
            logger.info("Testing get_course_files...")
            results["get_course_files"] = await self.call_tool(
                session, "get_course_files", {"course_id": course_id}
            )

            # Test search
            logger.info("Testing search_course_content...")
            results["search_course_content"] = await self.call_tool(
                session,
                "search_course_content",
                {"course_id": course_id, "query": "assignment"},
            )

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error extracting course ID: {e}")

        # Test sync (this should be done last as it might take time)
        logger.info("Testing sync_canvas_data...")
        results["sync_canvas_data"] = await self.call_tool(session, "sync_canvas_data")

        return results

    async def interactive_mode(self, session):
        """
        Run an interactive session with the Canvas MCP server.

        Args:
            session: MCP client session
        """
        print("\nCanvas MCP Tool Tester")
        print("=====================")
        print("Type 'help' for available commands")
        print("Type 'exit' to quit")

        while True:
            try:
                command = input("\n> ").strip()

                if command.lower() in ["exit", "quit"]:
                    break

                if command.lower() == "help":
                    self._print_help()
                    continue

                if command.lower() == "tools":
                    tools = await self.list_tools(session)
                    print("\nAvailable Tools:")
                    for tool in tools:
                        print(f"  - {tool.name}: {tool.description}")
                        print(
                            f"    Input schema: {json.dumps(tool.inputSchema, indent=2)}"
                        )
                        print()
                    continue

                if command.lower() == "test":
                    print("Running tests on all tools...")
                    results = await self.test_all_tools(session)
                    print("\nTest Results Summary:")
                    for tool_name, result in results.items():
                        # Check for error in different result formats
                        has_error = False

                        if isinstance(result, dict) and "error" in result:
                            has_error = True
                        elif hasattr(result, "content") and result.content:
                            for content_item in result.content:
                                if (
                                    hasattr(content_item, "text")
                                    and "error" in content_item.text.lower()
                                ):
                                    has_error = True
                                    break

                        status = "SUCCESS" if result and not has_error else "FAILED"
                        print(f"  - {tool_name}: {status}")
                    continue

                if command.lower().startswith("tool "):
                    # Parse tool command: tool <name> [args as JSON]
                    parts = command.split(" ", 2)
                    if len(parts) < 2:
                        print("Usage: tool <name> [args as JSON]")
                        continue

                    tool_name = parts[1]
                    args = {}

                    if len(parts) > 2:
                        try:
                            args = json.loads(parts[2])
                        except json.JSONDecodeError:
                            print("Error: Arguments must be valid JSON")
                            continue

                    print(f"Calling tool {tool_name} with args: {args}")
                    result = await self.call_tool(session, tool_name, args)
                    print("\nResult:")

                    # Handle different result formats
                    if hasattr(result, "content") and result.content:
                        for content_item in result.content:
                            if hasattr(content_item, "text"):
                                try:
                                    # Try to parse as JSON for pretty printing
                                    parsed = json.loads(content_item.text)
                                    print(json.dumps(parsed, indent=2))
                                except json.JSONDecodeError:
                                    # If not JSON, print as is
                                    print(content_item.text)
                    else:
                        # Fall back to direct printing
                        print(
                            json.dumps(result, indent=2)
                            if isinstance(result, dict)
                            else result
                        )
                    continue

                print("Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _print_help(self):
        """Print help information."""
        print("\nAvailable Commands:")
        print("  help              - Show this help message")
        print("  tools             - List available tools with their schemas")
        print("  test              - Run tests on all tools")
        print("  tool <name> [args]- Call a tool with optional JSON arguments")
        print("  exit              - Exit the tester")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Canvas MCP Tool Tester")
    parser.add_argument(
        "--server",
        default="src/canvas_mcp/server.py",
        help="Path to the server script",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run tests automatically and exit",
    )
    args = parser.parse_args()

    tester = CanvasMCPTester(args.server)

    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command=sys.executable,  # Python executable
        args=[args.server],  # Server script
    )

    logger.info(f"Connecting to Canvas MCP server at {args.server}")

    # Use the async context manager properly
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Create a client session from the streams
        session = ClientSession(read_stream, write_stream)

        logger.info("Connected to Canvas MCP server")

        # List available tools
        await tester.list_tools(session)

        if args.test:
            # Run tests automatically
            print("Running tests on all tools...")
            results = await tester.test_all_tools(session)
            print("\nTest Results Summary:")
            for tool_name, result in results.items():
                # Check for error in different result formats
                has_error = False

                if isinstance(result, dict) and "error" in result:
                    has_error = True
                elif hasattr(result, "content") and result.content:
                    for content_item in result.content:
                        if (
                            hasattr(content_item, "text")
                            and "error" in content_item.text.lower()
                        ):
                            has_error = True
                            break

                status = "SUCCESS" if result and not has_error else "FAILED"
                print(f"  - {tool_name}: {status}")
        else:
            # Run interactive mode
            await tester.interactive_mode(session)

    logger.info("Disconnected from Canvas MCP server")


if __name__ == "__main__":
    asyncio.run(main())
