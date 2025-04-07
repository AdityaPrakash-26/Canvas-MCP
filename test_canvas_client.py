#!/usr/bin/env python3
"""
Test script for Canvas MCP client functionality.
This script tests various functions in the Canvas client directly.
"""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import sys
sys.path.append(str(Path(__file__).parent / "src"))
from canvas_mcp.canvas_client import CanvasClient

# Load environment variables
load_dotenv()

# Configure paths
PROJECT_DIR = Path(__file__).parent
DB_DIR = PROJECT_DIR / "data"
DB_PATH = DB_DIR / "canvas_mcp.db"

# Create Canvas client
API_KEY = os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")

print(f"Canvas API URL: {API_URL}")
print(f"Canvas API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:] if API_KEY else 'Not set'}")
print(f"Database Path: {DB_PATH}")

try:
    print("\nTesting Canvas client initialization...")
    canvas_client = CanvasClient(str(DB_PATH), API_KEY, API_URL)
    print("✓ Canvas client initialized successfully")
    
    print("\nTesting database connection...")
    conn, cursor = canvas_client.connect_db()
    print("✓ Database connection successful")
    
    # Check if courses table exists and count rows
    print("\nChecking courses table...")
    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0]
    print(f"✓ Courses table exists, contains {course_count} courses")
    
    # Display some course data if available
    if course_count > 0:
        print("\nSample course data:")
        cursor.execute("SELECT id, course_code, course_name FROM courses LIMIT 3")
        courses = cursor.fetchall()
        for course in courses:
            print(f"  - ID: {course[0]}, Code: {course[1]}, Name: {course[2]}")
    
    # Test Canvas API connection if canvasapi is installed
    print("\nTesting Canvas API connection...")
    if canvas_client.canvas:
        try:
            user = canvas_client.canvas.get_current_user()
            print(f"✓ Canvas API connected successfully (User: {user.name})")
        except Exception as e:
            print(f"✗ Canvas API connection failed: {e}")
    else:
        print("✗ canvasapi module not found, API connection not tested")
    
    # Close connection
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
