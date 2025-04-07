"""
Query Parser Utilities

This module provides utilities for parsing and understanding natural language
queries related to Canvas courses and assignments.
"""

import re
from typing import Dict, Any, Optional, Tuple, List


def _extract_course_code(query: str) -> tuple[str, float]:
    """
    Extract course code from a query string.

    Args:
        query: The natural language query string

    Returns:
        Tuple of (course_code, confidence)
    """
    query_lower = query.lower()
    
    # Try advanced patterns for course recognition
    # Look for course patterns including department codes
    course_patterns = [
        # Standard CS course code
        r'\b(cs[-\s]?\d{3})\b',
        # Department codes followed by numbers
        r'\b(math|phys|chem|biol|hist|econ|psyc|soc|anth|phil|eng|ling)[-\s]?\d{3}\b',
        # Just course numbers in various formats (less confidence)
        r'\b\d{3}[-\s]?\d{1,3}\b'  # e.g., 570-1 or 570 1
    ]
    
    # Try each pattern with decreasing confidence
    confidence_levels = [0.9, 0.7, 0.5]
    
    for pattern, confidence in zip(course_patterns, confidence_levels):
        matches = re.findall(pattern, query_lower)
        if matches:
            course_code = matches[0].replace(" ", "").replace("-", "")
            return course_code, confidence
            
    return "", 0.0


def _extract_assignment_info(query: str) -> tuple[str, str, float]:
    """
    Extract assignment number and name from a query string.

    Args:
        query: The natural language query string

    Returns:
        Tuple of (assignment_number, assignment_name, confidence)
    """
    query_lower = query.lower()
    
    # Check for specific assignment keywords
    assignment_keywords = [
        "assignment", "homework", "hw", "project", "quiz", "exam", 
        "midterm", "final", "problem set", "pset"
    ]
    
    # Try to identify the assignment type
    assignment_type = None
    assignment_score = 0
    
    for keyword in assignment_keywords:
        if keyword in query_lower:
            # Count occurrences and position
            count = query_lower.count(keyword)
            position = query_lower.find(keyword)
            # Earlier positions and multiple occurrences increase score
            score = count * (100 - min(position, 100)) / 100
            
            if score > assignment_score:
                assignment_score = score
                assignment_type = keyword
    
    # Advanced assignment number extraction
    # Look for ordinals and number words
    ordinals = {
        "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
        "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10"
    }
    
    for word, number in ordinals.items():
        if word in query_lower:
            if assignment_type:
                return number, f"{assignment_type} {number}", 0.8
    
    # Match "assignment X" or "assignment #X"
    assignment_patterns = [
        # Match "assignment X" or "assignment #X"
        (re.compile(r'assignment\s+(?:#)?(\d+)'), "assignment"),
        # Match "homework X" or "homework #X"
        (re.compile(r'homework\s+(?:#)?(\d+)'), "homework"),
        # Match "hw X" or "hw#X"
        (re.compile(r'hw\s*(?:#)?(\d+)'), "homework"),
        # Match "assignmentX", "assignment_X", etc.
        (re.compile(r'assignment[-_]?(\d+)'), "assignment"),
        # Match "homeworkX", "homework_X", etc.
        (re.compile(r'homework[-_]?(\d+)'), "homework"),
        # Match "hwX", "hw_X", etc.
        (re.compile(r'hw[-_]?(\d+)'), "homework"),
        # Match "assignX", etc.
        (re.compile(r'assign[-_]?(\d+)'), "assignment"),
    ]
    
    for pattern, assignment_type in assignment_patterns:
        matches = pattern.findall(query_lower)
        if matches:
            # Use the first match
            return matches[0], f"{assignment_type} {matches[0]}", 0.9
    
    # Look for homework file pattern like "CS570_HW2.pdf" or "CS570_Homework2.pdf"
    file_pattern = re.compile(r'(?:cs\d{3})?[-_]?(?:hw|homework|assignment)[-_]?(\d+)(?:\.pdf)?', re.IGNORECASE)
    file_matches = file_pattern.findall(query)
    
    if file_matches:
        return file_matches[0], f"assignment {file_matches[0]}", 0.7
            
    return "", "", 0.0


def parse_assignment_query(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query for assignment information.
    
    Examples:
        - "what is my assignment2 for cs570"
        - "details about cs570_homework2.pdf"
        - "show me assignment 1 in CS 441"
    
    Args:
        query: The natural language query
    
    Returns:
        Dict with extracted information:
            {
                "course_code": str,  # e.g., "cs570"
                "assignment_number": int or str,  # e.g., 2 or "2"
                "assignment_name": str,  # e.g., "assignment2"
                "confidence": float  # confidence score between 0 and 1
            }
    """
    result = {
        "course_code": None,
        "assignment_number": None,
        "assignment_name": None,
        "confidence": 0.0
    }
    
    # Extract course code
    course_code, course_confidence = _extract_course_code(query)
    if course_code:
        result["course_code"] = course_code
        result["confidence"] = course_confidence
    
    # Extract assignment info
    assignment_number, assignment_name, assignment_confidence = _extract_assignment_info(query)
    if assignment_number:
        result["assignment_number"] = assignment_number
        result["assignment_name"] = assignment_name
        # Average the confidences if we have both course and assignment
        if result["course_code"]:
            result["confidence"] = (course_confidence + assignment_confidence) / 2
        else:
            result["confidence"] = assignment_confidence
    
    return result


def find_course_id_by_code(db_cursor, course_code: str) -> Optional[int]:
    """
    Find the local course ID given a course code.
    
    Args:
        db_cursor: SQLite cursor
        course_code: Course code (e.g., "cs570")
    
    Returns:
        Local course ID if found, None otherwise
    """
    # Format the course code for SQL pattern matching
    search_pattern = f"%{course_code}%"
    
    # Query the database
    db_cursor.execute(
        "SELECT id FROM courses WHERE LOWER(course_code) LIKE ?",
        (search_pattern,)
    )
    
    row = db_cursor.fetchone()
    if row:
        return row["id"]
    
    return None
