#!/usr/bin/env python
"""
Generate test fixtures from real Canvas API responses.

This script connects to the Canvas API and generates fixture files
for use in unit tests with the fake Canvas API implementation.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from canvasapi import Canvas

# Create fixtures directory if it doesn't exist
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fakes" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Target course ID for detailed fixtures
TARGET_COURSE_ID = 65920000000146127  # SP25_CS_540_1


def save_fixture(filename: str, data: Any) -> None:
    """
    Save data to a fixture file.

    Args:
        filename: Name of the fixture file
        data: Data to save (must be JSON serializable)
    """
    filepath = FIXTURES_DIR / filename
    
    # Convert data to JSON
    json_data = json.dumps(data, indent=2, default=str)
    
    # Save to file
    with open(filepath, "w") as f:
        f.write(json_data)
    
    print(f"Saved fixture: {filepath}")


def object_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert a Canvas API object to a dictionary.

    Args:
        obj: Canvas API object

    Returns:
        Dictionary representation of the object
    """
    # If the object has a to_json method, use it
    if hasattr(obj, "to_json") and callable(getattr(obj, "to_json")):
        return obj.to_json()
    
    # Otherwise, get all attributes that don't start with _
    result = {}
    for attr in dir(obj):
        if not attr.startswith("_") and not callable(getattr(obj, attr)):
            try:
                value = getattr(obj, attr)
                # Skip methods and complex objects
                if not callable(value):
                    result[attr] = value
            except Exception:
                # Skip attributes that can't be accessed
                pass
    
    return result


def generate_fixtures() -> None:
    """Generate fixture files from real Canvas API responses."""
    # Get API credentials from environment
    api_key = os.environ.get("CANVAS_API_KEY")
    api_url = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
    
    if not api_key:
        print("Error: CANVAS_API_KEY environment variable is required")
        return
    
    # Initialize Canvas API
    canvas = Canvas(api_url, api_key)
    
    try:
        # Get current user
        user = canvas.get_current_user()
        save_fixture("current_user.json", object_to_dict(user))
        
        # Get courses
        courses = list(user.get_courses())
        courses_data = [object_to_dict(course) for course in courses]
        save_fixture("courses.json", courses_data)
        
        # Find target course
        target_course = None
        for course in courses:
            if course.id == TARGET_COURSE_ID:
                target_course = course
                break
        
        if not target_course:
            print(f"Warning: Target course {TARGET_COURSE_ID} not found")
            # Use the first course as fallback
            if courses:
                target_course = courses[0]
            else:
                print("Error: No courses found")
                return
        
        # Get assignments for target course
        try:
            assignments = list(target_course.get_assignments())
            assignments_data = [object_to_dict(assignment) for assignment in assignments]
            save_fixture(f"assignments_{target_course.id}.json", assignments_data)
        except Exception as e:
            print(f"Error getting assignments: {e}")
        
        # Get modules for target course
        try:
            modules = list(target_course.get_modules())
            modules_data = [object_to_dict(module) for module in modules]
            save_fixture(f"modules_{target_course.id}.json", modules_data)
            
            # Get module items for each module
            for module in modules:
                try:
                    items = list(module.get_module_items())
                    items_data = [object_to_dict(item) for item in items]
                    save_fixture(f"module_items_{module.id}.json", items_data)
                except Exception as e:
                    print(f"Error getting module items for module {module.id}: {e}")
        except Exception as e:
            print(f"Error getting modules: {e}")
        
        # Get announcements for target course
        try:
            announcements = list(target_course.get_discussion_topics(only_announcements=True))
            announcements_data = [object_to_dict(announcement) for announcement in announcements]
            save_fixture(f"announcements_{target_course.id}.json", announcements_data)
        except Exception as e:
            print(f"Error getting announcements: {e}")
        
        # Get files for target course
        try:
            files = list(target_course.get_files())
            files_data = [object_to_dict(file) for file in files]
            save_fixture(f"files_{target_course.id}.json", files_data)
        except Exception as e:
            print(f"Error getting files: {e}")
        
        print("Fixture generation complete!")
        
    except Exception as e:
        print(f"Error generating fixtures: {e}")


if __name__ == "__main__":
    generate_fixtures()
