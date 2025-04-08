#!/usr/bin/env python3
"""
Test script for syllabus retrieval in Canvas MCP.

This script tests the get_syllabus function from the server module,
focusing specifically on retrieval for CS540.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import the necessary modules
from canvas_mcp.server import get_syllabus


def main():
    """Test the syllabus retrieval functionality for CS540."""
    print("Testing CS540 Syllabus Retrieval")
    print("================================")

    # Course ID 2 corresponds to CS540
    course_id = 2

    # Test raw format
    print("\nTesting raw format:")
    try:
        syllabus_raw = get_syllabus(course_id, format="raw")

        print(f"Course Code: {syllabus_raw.get('course_code')}")
        print(f"Course Name: {syllabus_raw.get('course_name')}")
        print(f"Content Type: {syllabus_raw.get('content_type')}")

        # Print a preview of the content
        content = syllabus_raw.get("content", "")
        if content:
            preview_length = min(500, len(content))
            print(f"\nContent Preview (first {preview_length} characters):")
            print(
                content[:preview_length] + "..."
                if len(content) > preview_length
                else content
            )
    except Exception as e:
        print(f"Error retrieving syllabus in raw format: {e}")
        import traceback

        traceback.print_exc()

    # Test parsed format
    print("\n\nTesting parsed format:")
    try:
        syllabus_parsed = get_syllabus(course_id, format="parsed")

        print(f"Course Code: {syllabus_parsed.get('course_code')}")
        print(f"Course Name: {syllabus_parsed.get('course_name')}")
        print(f"Content Type: {syllabus_parsed.get('content_type')}")

        # Print a preview of the content
        content = syllabus_parsed.get("content", "")
        if content:
            preview_length = min(500, len(content))
            print(f"\nContent Preview (first {preview_length} characters):")
            print(
                content[:preview_length] + "..."
                if len(content) > preview_length
                else content
            )
    except Exception as e:
        print(f"Error retrieving syllabus in parsed format: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
