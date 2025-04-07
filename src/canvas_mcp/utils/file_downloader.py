"""
Utility for downloading files from Canvas LMS.

This module provides functions for downloading files from Canvas courses
and organizing them in a local directory structure.
"""

import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_download_directory(base_dir: str, course_id: int) -> str:
    """
    Create a directory structure for downloaded files.

    Args:
        base_dir: Base directory for downloads
        course_id: Course ID

    Returns:
        Path to course download directory
    """
    # Create base directory if it doesn't exist
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # Create course directory
    course_dir = os.path.join(base_dir, f"course_{course_id}")
    if not os.path.exists(course_dir):
        os.makedirs(course_dir)

    return course_dir


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace characters that are invalid in filenames
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    
    # Limit filename length
    if len(filename) > 255:
        base, ext = os.path.splitext(filename)
        filename = base[:255 - len(ext)] + ext
    
    return filename


def download_file(url: str, destination: str) -> Tuple[bool, str]:
    """
    Download a file from a URL to a local destination.

    Args:
        url: URL of the file to download
        destination: Local path to save the file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Download the file
        urllib.request.urlretrieve(url, destination)
        
        return True, f"Successfully downloaded to {destination}"
    except urllib.error.URLError as e:
        return False, f"Error downloading {url}: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def download_course_files(
    canvas_instance, 
    course_id: int,
    base_dir: str = "downloaded_files",
    file_types: Optional[List[str]] = None,
    download_submissions: bool = False,
) -> Dict[str, Any]:
    """
    Download files from a Canvas course.

    Args:
        canvas_instance: CanvasClient instance
        course_id: Canvas course ID
        base_dir: Base directory to store downloads
        file_types: Optional list of file extensions to download (e.g. ['.pdf', '.docx'])
                   If None, download all file types
        download_submissions: Whether to download assignment submissions

    Returns:
        Dictionary with download summary
    """
    start_time = datetime.now()
    course_dir = create_download_directory(base_dir, course_id)
    
    # Create manifest to track downloaded files
    manifest = {
        "course_id": course_id,
        "download_date": start_time.isoformat(),
        "files": [],
        "download_status": {
            "total_files": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
        }
    }
    
    try:
        # Get Canvas course
        canvas_course = canvas_instance.canvas.get_course(course_id)
        logger.info(f"Processing course: {canvas_course.name} (ID: {course_id})")
        
        # Download course files
        try:
            files = canvas_course.get_files()
            manifest["download_status"]["total_files"] += len(list(files))
            
            # Create 'files' subdirectory
            files_dir = os.path.join(course_dir, "files")
            os.makedirs(files_dir, exist_ok=True)
            
            for file in files:
                # Check if file matches requested types
                if file_types and not any(file.filename.lower().endswith(ft.lower()) for ft in file_types):
                    continue
                
                filename = sanitize_filename(file.filename)
                destination = os.path.join(files_dir, filename)
                
                file_info = {
                    "id": file.id,
                    "filename": file.filename,
                    "content_type": getattr(file, "content_type", "unknown"),
                    "size": getattr(file, "size", 0),
                    "created_at": getattr(file, "created_at", ""),
                    "updated_at": getattr(file, "updated_at", ""),
                    "download_path": destination,
                    "source": "course_files",
                }
                
                logger.info(f"Downloading file: {file.filename}")
                success, message = download_file(file.url, destination)
                
                file_info["download_success"] = success
                file_info["download_message"] = message
                
                if success:
                    manifest["download_status"]["successful_downloads"] += 1
                else:
                    manifest["download_status"]["failed_downloads"] += 1
                
                manifest["files"].append(file_info)
                
        except Exception as e:
            logger.error(f"Error downloading course files: {e}")
            
        # Download files from modules
        try:
            modules = canvas_course.get_modules()
            
            # Create 'modules' subdirectory
            modules_dir = os.path.join(course_dir, "modules")
            
            for module in modules:
                module_name = sanitize_filename(module.name)
                module_dir = os.path.join(modules_dir, module_name)
                os.makedirs(module_dir, exist_ok=True)
                
                try:
                    items = module.get_module_items()
                    
                    for item in items:
                        # Check if item is a file
                        if hasattr(item, "type") and item.type == "File":
                            file_id = getattr(item, "content_id", None)
                            
                            if file_id:
                                try:
                                    file = canvas_course.get_file(file_id)
                                    
                                    # Check if file matches requested types
                                    if file_types and not any(file.filename.lower().endswith(ft.lower()) for ft in file_types):
                                        continue
                                    
                                    filename = sanitize_filename(file.filename)
                                    destination = os.path.join(module_dir, filename)
                                    
                                    manifest["download_status"]["total_files"] += 1
                                    
                                    file_info = {
                                        "id": file.id,
                                        "filename": file.filename,
                                        "content_type": getattr(file, "content_type", "unknown"),
                                        "size": getattr(file, "size", 0),
                                        "created_at": getattr(file, "created_at", ""),
                                        "updated_at": getattr(file, "updated_at", ""),
                                        "download_path": destination,
                                        "source": f"module_{module.id}",
                                    }
                                    
                                    logger.info(f"Downloading module file: {file.filename}")
                                    success, message = download_file(file.url, destination)
                                    
                                    file_info["download_success"] = success
                                    file_info["download_message"] = message
                                    
                                    if success:
                                        manifest["download_status"]["successful_downloads"] += 1
                                    else:
                                        manifest["download_status"]["failed_downloads"] += 1
                                    
                                    manifest["files"].append(file_info)
                                    
                                except Exception as e:
                                    logger.error(f"Error downloading module file {file_id}: {e}")
                                    
                except Exception as e:
                    logger.error(f"Error processing module items for module {module.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing modules: {e}")
            
        # Download files from assignments
        if download_submissions:
            try:
                assignments = canvas_course.get_assignments()
                
                # Create 'assignments' subdirectory
                assignments_dir = os.path.join(course_dir, "assignments")
                
                for assignment in assignments:
                    assignment_name = sanitize_filename(assignment.name)
                    assignment_dir = os.path.join(assignments_dir, assignment_name)
                    
                    # Check for attachments in assignment
                    if hasattr(assignment, "description") and assignment.description:
                        os.makedirs(assignment_dir, exist_ok=True)
                        
                        # Extract file IDs from the description
                        try:
                            import re
                            file_id_pattern = re.compile(r'/files/(\d+)')
                            file_ids = file_id_pattern.findall(assignment.description)
                            
                            for file_id in file_ids:
                                try:
                                    file = canvas_course.get_file(file_id)
                                    
                                    # Check if file matches requested types
                                    if file_types and not any(file.filename.lower().endswith(ft.lower()) for ft in file_types):
                                        continue
                                    
                                    filename = sanitize_filename(file.filename)
                                    destination = os.path.join(assignment_dir, filename)
                                    
                                    manifest["download_status"]["total_files"] += 1
                                    
                                    file_info = {
                                        "id": file.id,
                                        "filename": file.filename,
                                        "content_type": getattr(file, "content_type", "unknown"),
                                        "size": getattr(file, "size", 0),
                                        "created_at": getattr(file, "created_at", ""),
                                        "updated_at": getattr(file, "updated_at", ""),
                                        "download_path": destination,
                                        "source": f"assignment_{assignment.id}",
                                    }
                                    
                                    logger.info(f"Downloading assignment file: {file.filename}")
                                    success, message = download_file(file.url, destination)
                                    
                                    file_info["download_success"] = success
                                    file_info["download_message"] = message
                                    
                                    if success:
                                        manifest["download_status"]["successful_downloads"] += 1
                                    else:
                                        manifest["download_status"]["failed_downloads"] += 1
                                    
                                    manifest["files"].append(file_info)
                                    
                                except Exception as e:
                                    logger.error(f"Error downloading file {file_id} from assignment {assignment.id}: {e}")
                        except Exception as e:
                            logger.error(f"Error parsing file IDs from assignment {assignment.id}: {e}")
                            
            except Exception as e:
                logger.error(f"Error processing assignments: {e}")
                
    except Exception as e:
        logger.error(f"Error processing course {course_id}: {e}")
        
    # Write manifest to file
    end_time = datetime.now()
    manifest["download_duration_seconds"] = (end_time - start_time).total_seconds()
    
    try:
        manifest_path = os.path.join(course_dir, "download_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing manifest file: {e}")
        
    return manifest


def download_multiple_courses(
    canvas_instance,
    course_ids: List[int],
    base_dir: str = "downloaded_files",
    file_types: Optional[List[str]] = None,
    download_submissions: bool = False,
) -> Dict[str, Any]:
    """
    Download files from multiple Canvas courses.

    Args:
        canvas_instance: CanvasClient instance
        course_ids: List of Canvas course IDs
        base_dir: Base directory to store downloads
        file_types: Optional list of file extensions to download
        download_submissions: Whether to download assignment submissions

    Returns:
        Dictionary with download summary
    """
    overall_manifest = {
        "download_date": datetime.now().isoformat(),
        "courses": [],
        "download_status": {
            "total_courses": len(course_ids),
            "processed_courses": 0,
            "total_files": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
        }
    }
    
    for course_id in course_ids:
        try:
            course_manifest = download_course_files(
                canvas_instance,
                course_id,
                base_dir,
                file_types,
                download_submissions
            )
            
            overall_manifest["courses"].append({
                "course_id": course_id,
                "download_status": course_manifest["download_status"]
            })
            
            overall_manifest["download_status"]["processed_courses"] += 1
            overall_manifest["download_status"]["total_files"] += course_manifest["download_status"]["total_files"]
            overall_manifest["download_status"]["successful_downloads"] += course_manifest["download_status"]["successful_downloads"]
            overall_manifest["download_status"]["failed_downloads"] += course_manifest["download_status"]["failed_downloads"]
            
        except Exception as e:
            logger.error(f"Error processing course {course_id}: {e}")
            
    # Write overall manifest
    try:
        manifest_path = os.path.join(base_dir, "overall_download_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(overall_manifest, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing overall manifest file: {e}")
        
    return overall_manifest
