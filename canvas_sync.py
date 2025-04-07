#!/usr/bin/env python3
"""
Canvas File Synchronizer

This script synchronizes files from Canvas courses to a local directory.
It compares local and remote files, downloading only what has been added or changed.
"""

import os
import sys
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime
import urllib.request
from typing import Dict, List, Any, Tuple, Optional, Set
import hashlib
import shutil

from dotenv import load_dotenv
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Canvas API configuration
API_URL = os.environ.get("CANVAS_API_URL", "https://canvas.instructure.com")
API_KEY = os.environ.get("CANVAS_API_KEY")

# Output directory
DOWNLOAD_FOLDER = "downloaded_files"
ARCHIVE_FOLDER = "_archive"  # For moved/deleted files

# Maximum number of retries for downloads
MAX_RETRIES = 3


class FileInfo:
    """Represents metadata for a file."""
    
    def __init__(
        self, 
        name: str, 
        path: str, 
        size: int = 0, 
        modified_at: float = 0, 
        url: str = "", 
        file_id: Any = None,
        content_type: str = "",
        source: str = ""
    ):
        self.name = name
        self.path = path
        self.size = size
        self.modified_at = modified_at  # timestamp
        self.url = url
        self.file_id = file_id
        self.content_type = content_type
        self.source = source  # e.g., 'course_files', 'module', etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FileInfo to a dictionary for serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "modified_at": self.modified_at,
            "url": self.url,
            "file_id": self.file_id,
            "content_type": self.content_type,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInfo':
        """Create FileInfo from a dictionary."""
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            size=data.get("size", 0),
            modified_at=data.get("modified_at", 0),
            url=data.get("url", ""),
            file_id=data.get("file_id"),
            content_type=data.get("content_type", ""),
            source=data.get("source", "")
        )
    
    @classmethod
    def from_canvas_file(cls, file, relative_path: str = "", source: str = "course_files") -> 'FileInfo':
        """Create FileInfo from a Canvas file object."""
        modified_at = getattr(file, "modified_at_date", None)
        if modified_at is None:
            # Fallback if modified_at_date is not available
            modified_at = getattr(file, "updated_at_date", datetime.now())
        
        # Convert to timestamp if it's a datetime
        if isinstance(modified_at, datetime):
            modified_at = modified_at.timestamp()
            
        return cls(
            name=getattr(file, "display_name", getattr(file, "filename", "unknown")),
            path=os.path.join(relative_path, getattr(file, "display_name", getattr(file, "filename", "unknown"))),
            size=getattr(file, "size", 0),
            modified_at=modified_at,
            url=getattr(file, "url", ""),
            file_id=getattr(file, "id", None),
            content_type=getattr(file, "content_type", ""),
            source=source
        )


class SyncOperation:
    """Represents a synchronization operation."""
    
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    IGNORE = "ignore"
    
    def __init__(self, operation: str, file_info: FileInfo):
        self.operation = operation
        self.file_info = file_info


class CanvasSnapshot:
    """Takes a snapshot of files on Canvas."""
    
    def __init__(self, course):
        self.course = course
        self.snapshot = {}  # path -> FileInfo
        self.tabs = None
    
    def get_tabs(self) -> List[str]:
        """Get available tabs for the course."""
        if self.tabs is None:
            self.tabs = [tab.id for tab in self.course.get_tabs()]
        return self.tabs
    
    def take_snapshot(self) -> Dict[str, FileInfo]:
        """Take a snapshot of Canvas files."""
        logger.info(f"Taking snapshot of course {self.course.name} (ID: {self.course.id})")
        
        # Process files tab if available
        if 'files' in self.get_tabs():
            self.process_files_tab()
        
        # Process modules tab if available
        if 'modules' in self.get_tabs():
            self.process_modules_tab()
        
        # Process assignments if available
        if 'assignments' in self.get_tabs():
            self.process_assignments_tab()
        
        logger.info(f"Found {len(self.snapshot)} files in course {self.course.name}")
        return self.snapshot
    
    def process_files_tab(self):
        """Process files from the Files tab."""
        logger.info("Processing Files tab")
        
        try:
            # Get all folders to determine paths
            folders = {folder.id: folder for folder in self.course.get_folders()}
            
            # Get all files
            for file in self.course.get_files():
                # Determine relative path based on folder
                folder_path = ""
                if hasattr(file, "folder_id") and file.folder_id in folders:
                    folder = folders[file.folder_id]
                    folder_path = sanitize_path(folder.full_name)
                    if folder_path.startswith("course files/"):
                        folder_path = folder_path[len("course files/"):]
                
                file_info = FileInfo.from_canvas_file(file, folder_path)
                self.snapshot[file_info.path] = file_info
            
            logger.info(f"Found {len(self.snapshot)} files in Files tab")
        except ResourceDoesNotExist:
            logger.warning("Files tab is not accessible")
        except Exception as e:
            logger.error(f"Error processing Files tab: {e}")
    
    def process_modules_tab(self):
        """Process files from the Modules tab."""
        logger.info("Processing Modules tab")
        
        try:
            # Get all modules
            modules = list(self.course.get_modules())
            module_count = len(modules)
            logger.info(f"Found {module_count} modules")
            
            # Track files that have been found in modules
            module_file_ids = set()
            
            for module_idx, module in enumerate(modules):
                try:
                    # Get module name and sanitize it
                    module_name = sanitize_path(module.name)
                    module_position = getattr(module, "position", module_idx + 1)
                    module_folder = f"{module_position}_{module_name}"
                    
                    logger.info(f"Processing module: {module_name}")
                    
                    # Get module items
                    items = list(module.get_module_items())
                    for item in items:
                        if item.type == "File":
                            try:
                                # Retrieve file by ID
                                file_id = item.content_id
                                file = self.course.get_file(file_id)
                                
                                # Remember we've seen this file in a module
                                module_file_ids.add(file_id)
                                
                                # Create FileInfo
                                file_info = FileInfo.from_canvas_file(
                                    file,
                                    f"modules/{module_folder}",
                                    f"module_{module.id}"
                                )
                                self.snapshot[file_info.path] = file_info
                            except Exception as e:
                                logger.error(f"Error processing module item {item.title}: {e}")
                except Exception as e:
                    logger.error(f"Error processing module {module.name}: {e}")
        except ResourceDoesNotExist:
            logger.warning("Modules tab is not accessible")
        except Exception as e:
            logger.error(f"Error processing Modules tab: {e}")
    
    def process_assignments_tab(self):
        """Process files from the Assignments tab."""
        logger.info("Processing Assignments tab")
        
        try:
            assignments = list(self.course.get_assignments())
            logger.info(f"Found {len(assignments)} assignments")
            
            for assignment in assignments:
                # Only process if the assignment has a description (potential file references)
                if not hasattr(assignment, "description") or not assignment.description:
                    continue
                
                assignment_name = sanitize_path(assignment.name)
                
                # Extract file IDs from the description using regex
                try:
                    file_id_pattern = re.compile(r'/files/(\d+)')
                    file_ids = file_id_pattern.findall(assignment.description)
                    
                    for file_id in file_ids:
                        try:
                            # Get the file by ID
                            file = self.course.get_file(file_id)
                            
                            # Create FileInfo
                            file_info = FileInfo.from_canvas_file(
                                file,
                                f"assignments/{assignment_name}",
                                f"assignment_{assignment.id}"
                            )
                            self.snapshot[file_info.path] = file_info
                        except Exception as e:
                            logger.error(f"Error processing file {file_id} in assignment {assignment.name}: {e}")
                except Exception as e:
                    logger.error(f"Error processing file IDs in assignment {assignment.name}: {e}")
        except ResourceDoesNotExist:
            logger.warning("Assignments tab is not accessible")
        except Exception as e:
            logger.error(f"Error processing Assignments tab: {e}")


class LocalSnapshot:
    """Takes a snapshot of files in a local directory."""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.snapshot = {}  # path -> FileInfo
        self.manifest_path = os.path.join(base_dir, "manifest.json")
    
    def take_snapshot(self) -> Dict[str, FileInfo]:
        """Take a snapshot of local files."""
        logger.info(f"Taking snapshot of local directory: {self.base_dir}")
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Created directory: {self.base_dir}")
            return {}
        
        # First try to load from manifest
        manifest_data = self.load_manifest()
        if manifest_data and "files" in manifest_data:
            for file_data in manifest_data["files"]:
                file_info = FileInfo.from_dict(file_data)
                # Verify the file actually exists
                full_path = os.path.join(self.base_dir, file_info.path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    self.snapshot[file_info.path] = file_info
        
        logger.info(f"Found {len(self.snapshot)} files in local directory from manifest")
        return self.snapshot
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load manifest data from disk."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading manifest: {e}")
        return {}
    
    def save_manifest(self, manifest_data: Dict[str, Any]):
        """Save manifest data to disk."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            logger.info(f"Saved manifest to {self.manifest_path}")
        except Exception as e:
            logger.error(f"Error saving manifest: {e}")


class SyncPlanner:
    """Plans synchronization operations by comparing snapshots."""
    
    def __init__(self, delete_files: bool = False):
        self.delete_files = delete_files
    
    def create_plan(
        self, 
        canvas_snapshot: Dict[str, FileInfo], 
        local_snapshot: Dict[str, FileInfo]
    ) -> List[SyncOperation]:
        """Create a plan for synchronization."""
        plan = []
        
        # Find files to add or update
        for path, canvas_file in canvas_snapshot.items():
            if path not in local_snapshot:
                # File is in Canvas but not local - add it
                plan.append(SyncOperation(SyncOperation.ADD, canvas_file))
            else:
                # File is in both - check if updated
                local_file = local_snapshot[path]
                if self.is_file_updated(canvas_file, local_file):
                    plan.append(SyncOperation(SyncOperation.UPDATE, canvas_file))
                else:
                    # File is unchanged
                    plan.append(SyncOperation(SyncOperation.IGNORE, canvas_file))
        
        # Find files to delete (if enabled)
        if self.delete_files:
            for path, local_file in local_snapshot.items():
                if path not in canvas_snapshot:
                    # File is local but not in Canvas - delete it
                    plan.append(SyncOperation(SyncOperation.DELETE, local_file))
        
        return plan
    
    def is_file_updated(self, canvas_file: FileInfo, local_file: FileInfo) -> bool:
        """Check if a file has been updated by comparing metadata."""
        # Compare file size
        if canvas_file.size != local_file.size:
            return True
        
        # Compare modification time if available
        if canvas_file.modified_at and local_file.modified_at:
            # Allow a 1-second difference to account for timestamp precision issues
            if abs(canvas_file.modified_at - local_file.modified_at) > 1:
                return True
        
        return False


class FileSynchronizer:
    """Executes synchronization operations."""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.archive_dir = os.path.join(base_dir, ARCHIVE_FOLDER)
        self.manifest = {"files": [], "last_sync": None}
    
    def execute_plan(self, plan: List[SyncOperation]) -> Dict[str, int]:
        """Execute a synchronization plan."""
        # Group operations by type for reporting
        report = {
            SyncOperation.ADD: 0,
            SyncOperation.UPDATE: 0,
            SyncOperation.DELETE: 0,
            SyncOperation.IGNORE: 0
        }
        
        for operation in plan:
            logger.info(f"{operation.operation}: {operation.file_info.path}")
            
            if operation.operation in (SyncOperation.ADD, SyncOperation.UPDATE):
                success = self.download_file(operation.file_info)
                if success:
                    self.manifest["files"].append(operation.file_info.to_dict())
                    report[operation.operation] += 1
            
            elif operation.operation == SyncOperation.DELETE:
                success = self.delete_file(operation.file_info)
                if success:
                    # Remove from manifest
                    self.manifest["files"] = [
                        f for f in self.manifest["files"] 
                        if f.get("path") != operation.file_info.path
                    ]
                    report[operation.operation] += 1
            
            elif operation.operation == SyncOperation.IGNORE:
                # Keep file in manifest
                report[operation.operation] += 1
        
        # Update last sync time
        self.manifest["last_sync"] = datetime.now().isoformat()
        return report
    
    def download_file(self, file_info: FileInfo) -> bool:
        """Download a file from Canvas."""
        if not file_info.url:
            logger.warning(f"No URL available for {file_info.path}")
            return False
        
        # Create destination path
        dest_path = os.path.join(self.base_dir, file_info.path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Download with retries
        temp_path = f"{dest_path}.tmp"
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Downloading {file_info.name} (Attempt {attempt + 1}/{MAX_RETRIES})")
                
                # Download to temp file
                urllib.request.urlretrieve(file_info.url, temp_path)
                
                # Verify file size
                if os.path.getsize(temp_path) != file_info.size and file_info.size > 0:
                    logger.warning(
                        f"Size mismatch for {file_info.path}: "
                        f"expected {file_info.size}, got {os.path.getsize(temp_path)}"
                    )
                    os.remove(temp_path)
                    continue
                
                # Replace existing file
                if os.path.exists(dest_path):
                    os.replace(temp_path, dest_path)
                else:
                    os.rename(temp_path, dest_path)
                
                # Set file modified time
                if file_info.modified_at:
                    os.utime(dest_path, (time.time(), file_info.modified_at))
                
                logger.info(f"Successfully downloaded {file_info.path}")
                return True
                
            except Exception as e:
                logger.error(f"Error downloading {file_info.path}: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Wait before retry
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
        
        logger.error(f"Failed to download {file_info.path} after {MAX_RETRIES} attempts")
        return False
    
    def delete_file(self, file_info: FileInfo) -> bool:
        """Delete a file (move to archive)."""
        source_path = os.path.join(self.base_dir, file_info.path)
        if not os.path.exists(source_path):
            logger.warning(f"File {file_info.path} does not exist, nothing to delete")
            return True
        
        try:
            # Create archive path
            archive_path = os.path.join(self.archive_dir, file_info.path)
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            
            # Move file to archive
            shutil.move(source_path, archive_path)
            logger.info(f"Moved {file_info.path} to archive")
            return True
        except Exception as e:
            logger.error(f"Error deleting {file_info.path}: {e}")
            return False


def sanitize_path(path: str) -> str:
    """Sanitize a path by removing/replacing invalid characters."""
    # Replace Windows/Unix illegal filename chars
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', path)
    
    # Remove any leading/trailing spaces or dots
    sanitized = sanitized.strip('. ')
    
    # Replace multiple spaces with a single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    return sanitized


def get_course_directory(base_dir: str, course) -> str:
    """Create a directory name for a course."""
    course_id = course.id
    course_name = sanitize_path(course.name)
    course_dir = os.path.join(base_dir, f"{course_id}_{course_name}")
    os.makedirs(course_dir, exist_ok=True)
    return course_dir


def sync_course(canvas, course, base_dir: str, delete_files: bool = False) -> Dict[str, Any]:
    """Synchronize files for a single course."""
    # Get course directory
    course_dir = get_course_directory(base_dir, course)
    
    # Take snapshots
    canvas_snapshot_taker = CanvasSnapshot(course)
    canvas_snapshot = canvas_snapshot_taker.take_snapshot()
    
    local_snapshot_taker = LocalSnapshot(course_dir)
    local_snapshot = local_snapshot_taker.take_snapshot()
    
    # Create sync plan
    planner = SyncPlanner(delete_files)
    plan = planner.create_plan(canvas_snapshot, local_snapshot)
    
    # Execute plan
    synchronizer = FileSynchronizer(course_dir)
    report = synchronizer.execute_plan(plan)
    
    # Save manifest
    local_snapshot_taker.save_manifest(synchronizer.manifest)
    
    return {
        "course_id": course.id,
        "course_name": course.name,
        "operations": report,
        "snapshot_size": len(canvas_snapshot)
    }


def sync_all_courses(canvas, base_dir: str, delete_files: bool = False, current_term_only: bool = True) -> List[Dict[str, Any]]:
    """Synchronize files for all available courses.
    
    Args:
        canvas: Canvas API instance
        base_dir: Base directory for downloads
        delete_files: Whether to delete local files that don't exist in Canvas
        current_term_only: Whether to only sync courses from the current term
    """
    # Get available courses
    try:
        all_courses = list(canvas.get_courses())
        logger.info(f"Found {len(all_courses)} courses")
        
        # Filter for available courses (those with a name attribute)
        available_courses = [course for course in all_courses if hasattr(course, 'name')]
        logger.info(f"{len(available_courses)} courses are available for sync")
        
        # Filter for current term if requested
        courses = available_courses
        if current_term_only:
            # Get term IDs from all courses
            term_ids = []
            for course in available_courses:
                term_id = getattr(course, 'enrollment_term_id', None)
                if term_id is not None:
                    term_ids.append(term_id)
            
            if term_ids:
                # Find the most recent term (highest term_id)
                most_recent_term_id = max(term_ids)
                logger.info(f"Filtering to courses from term ID: {most_recent_term_id}")
                
                # Filter courses to only include those from the most recent term
                courses = [
                    course for course in available_courses
                    if getattr(course, 'enrollment_term_id', None) == most_recent_term_id
                ]
                logger.info(f"{len(courses)} courses are in the current term")
            else:
                logger.warning("Could not determine current term, using all available courses")
        
        reports = []
        for idx, course in enumerate(courses):
            logger.info(f"Processing course {idx+1}/{len(courses)}: {course.name} (ID: {course.id})")
            report = sync_course(canvas, course, base_dir, delete_files)
            reports.append(report)
        
        return reports
    
    except Exception as e:
        logger.error(f"Error synchronizing courses: {e}")
        return []


def main():
    # Parse command-line arguments
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Synchronize Canvas files to local directory",
        epilog="""
Examples:
  python canvas_sync.py                    # Sync only current term courses (default)
  python canvas_sync.py --all-terms        # Sync courses from all terms
  python canvas_sync.py --delete           # Delete local files that no longer exist in Canvas
  python canvas_sync.py --output-dir=files # Save files to a custom directory
        """
    )
    parser.add_argument("--all-terms", action="store_true", help="Sync courses from all terms, not just the current term")
    parser.add_argument("--delete", action="store_true", help="Delete local files that don't exist in Canvas")
    parser.add_argument("--output-dir", default=DOWNLOAD_FOLDER, help=f"Output directory (default: {DOWNLOAD_FOLDER})")
    args = parser.parse_args()
    
    # Print sync mode
    if args.all_terms:
        logger.info("Synchronizing courses from ALL terms")
    else:
        logger.info("Synchronizing courses from CURRENT term only")
    
    if args.delete:
        logger.info("Files that no longer exist in Canvas WILL be deleted locally (moved to archive)")
    else:
        logger.info("Files that no longer exist in Canvas will NOT be deleted locally")
    
    logger.info(f"Files will be saved to: {args.output_dir}")
    
    # Check for API key
    if not API_KEY:
        logger.error("No Canvas API key found. Please set CANVAS_API_KEY in environment or .env file")
        sys.exit(1)
    
    # Initialize Canvas API
    try:
        canvas = Canvas(API_URL, API_KEY)
        user = canvas.get_current_user()
        logger.info(f"Logged in as: {user.name} (ID: {user.id})")
    except Exception as e:
        logger.error(f"Error connecting to Canvas API: {e}")
        sys.exit(1)
    
    # Synchronize courses
    reports = sync_all_courses(
        canvas, 
        args.output_dir, 
        delete_files=args.delete,
        current_term_only=not args.all_terms
    )
    
    # Print summary
    total_added = sum(report["operations"]["add"] for report in reports)
    total_updated = sum(report["operations"]["update"] for report in reports)
    total_deleted = sum(report["operations"]["delete"] for report in reports)
    total_unchanged = sum(report["operations"]["ignore"] for report in reports)
    
    logger.info("Synchronization complete")
    logger.info(f"Total courses processed: {len(reports)}")
    logger.info(f"Files added: {total_added}")
    logger.info(f"Files updated: {total_updated}")
    logger.info(f"Files deleted: {total_deleted}")
    logger.info(f"Files unchanged: {total_unchanged}")


if __name__ == "__main__":
    main()
