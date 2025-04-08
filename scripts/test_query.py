#!/usr/bin/env python3
"""
Test script for assignment query extraction functionality.
This script tests the query_assignment function from the Canvas MCP server.py file.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import the necessary modules
from canvas_mcp.server import get_assignment_details


def main():
    """Test the assignment query extraction functionality"""
    print("Testing Assignment Query Extraction")
    print("==================================")

    # Test direct assignment details
    print("\nTesting direct assignment details for CS 570 Assignment 2")
    try:
        # Course ID 3 is SP25_CS_570_1
        result = get_assignment_details(3, "assignment 2")
        print("\nQuery Result:")
        print(f"Success: {result.get('success', False)}")

        if "error" in result:
            print(f"Error: {result['error']}")

        if "parsed_query" in result:
            parsed = result["parsed_query"]
            print("\nParsed Query:")
            print(f"Course Code: {parsed.get('course_code')}")
            print(f"Assignment Number: {parsed.get('assignment_number')}")
            print(f"Assignment Name: {parsed.get('assignment_name')}")
            print(f"Confidence: {parsed.get('confidence')}")

        if "assignment" in result:
            assignment = result["assignment"]
            print("\nAssignment Details:")
            print(f"Title: {assignment.get('title')}")
            print(f"Due Date: {assignment.get('due_date')}")
            print(f"Points: {assignment.get('points_possible')}")

            # Print a truncated description if available
            description = assignment.get("description", "")
            if description:
                if len(description) > 100:
                    description = description[:100] + "..."
                print(f"Description Preview: {description}")

        # Print PDF files if available
        if "pdf_files" in result and result["pdf_files"]:
            pdf_count = len(result["pdf_files"])
            print(f"\nPDF Files: {pdf_count}")
            for i, pdf in enumerate(result["pdf_files"][:3], 1):  # Show up to 3 PDFs
                print(
                    f"  {i}. {pdf.get('name', 'Unnamed')} - {pdf.get('url', 'No URL')[:50]}..."
                )

        # Print links if available
        if "links" in result and result["links"]:
            link_count = len(result["links"])
            print(f"\nLinks: {link_count}")
            for i, link in enumerate(result["links"][:3], 1):  # Show up to 3 links
                print(
                    f"  {i}. {link.get('text', 'Unnamed')} - {link.get('url', 'No URL')[:50]}..."
                )

    except Exception as e:
        print(f"Error running query_assignment: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
