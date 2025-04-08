#!/usr/bin/env python3
"""
Script to organize the scripts folder.

This script organizes the scripts folder by:
1. Moving the most important test utilities to the top level
2. Organizing the rest into subdirectories
3. Updating the README.md file

Usage:
    python scripts/organize_scripts.py
"""

import os
import shutil
from pathlib import Path

# Define the script directory
SCRIPT_DIR = Path(__file__).parent

# Define the core test utilities that should be at the top level
CORE_UTILITIES = [
    "extract_tools_test.py",
    "direct_tools_test.py",
    "test_tools_integration.py",
    "run_all_tests.py",
]

# Define the subdirectories to create
SUBDIRECTORIES = [
    "diagnostics",  # For diagnostic scripts
    "utils",  # For utility scripts
    "legacy",  # For legacy scripts
    "checks",  # For check scripts
]

# Define which scripts go into which subdirectory
SCRIPT_CATEGORIES = {
    "diagnostics": [
        "test_error_handling.py",
        "test_full_sync_process.py",
        "check_database_relationships.py",
        "test_tools_comprehensive.py",
    ],
    "utils": [
        "cleanup_db.py",
        "update_database_schema.py",
        "clean_and_verify.py",
    ],
    "checks": [
        "check_all_announcements.py",
        "check_all_course_conversations.py",
        "check_announcements.py",
        "check_announcements_vs_inbox.py",
        "check_canvas_ids.py",
        "check_canvas_notifications.py",
        "check_database_integrity.py",
        "check_discussions.py",
        "check_ids385_communications.py",
        "check_instructor_messages.py",
        "verify_course_filter.py",
        "verify_filtering.py",
    ],
    "legacy": [
        # Any script not explicitly categorized will go here
    ],
}


def create_subdirectories():
    """Create the subdirectories if they don't exist."""
    for subdir in SUBDIRECTORIES:
        subdir_path = SCRIPT_DIR / subdir
        if not subdir_path.exists():
            print(f"Creating subdirectory: {subdir}")
            subdir_path.mkdir(parents=True, exist_ok=True)


def organize_scripts():
    """Organize the scripts into the appropriate subdirectories."""
    # Get all Python scripts in the scripts directory
    scripts = [
        f
        for f in os.listdir(SCRIPT_DIR)
        if f.endswith(".py") and f != "organize_scripts.py"
    ]

    # Move core utilities to the top level (they're already there, so just skip them)
    core_utils = [s for s in scripts if s in CORE_UTILITIES]
    print(f"Core utilities (staying at top level): {core_utils}")

    # Organize the rest into subdirectories
    for script in scripts:
        if script in CORE_UTILITIES or script == "organize_scripts.py":
            continue

        # Determine which subdirectory the script should go into
        target_subdir = None
        for subdir, subdir_scripts in SCRIPT_CATEGORIES.items():
            if script in subdir_scripts:
                target_subdir = subdir
                break

        # If not explicitly categorized, put in legacy
        if target_subdir is None:
            target_subdir = "legacy"

        # Move the script to the appropriate subdirectory
        source_path = SCRIPT_DIR / script
        target_path = SCRIPT_DIR / target_subdir / script

        # Skip if the file is already in the right place
        if target_path.exists():
            print(f"Skipping {script} (already in {target_subdir})")
            continue

        print(f"Moving {script} to {target_subdir}")
        shutil.move(source_path, target_path)


def update_readme():
    """Update the README.md file."""
    # Rename the old README.md to README_OLD.md
    old_readme = SCRIPT_DIR / "README.md"
    if old_readme.exists():
        shutil.move(old_readme, SCRIPT_DIR / "README_OLD.md")
        print("Renamed old README.md to README_OLD.md")

    # Rename README_NEW.md to README.md
    new_readme = SCRIPT_DIR / "README_NEW.md"
    if new_readme.exists():
        shutil.move(new_readme, SCRIPT_DIR / "README.md")
        print("Renamed README_NEW.md to README.md")


def main():
    """Main function to organize the scripts folder."""
    print("Organizing scripts folder...")
    create_subdirectories()
    organize_scripts()
    update_readme()
    print("Done organizing scripts folder.")


if __name__ == "__main__":
    main()
