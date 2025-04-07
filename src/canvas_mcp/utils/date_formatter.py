"""
Date Formatting Utilities

This module provides utilities for consistent date formatting across the Canvas MCP system.
"""

import logging
from datetime import datetime
from typing import Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

def format_due_date(date_string: Optional[str], include_time: bool = True) -> str:
    """
    Format a due date string in a consistent format.
    
    Args:
        date_string: ISO format date string or None
        include_time: Whether to include time in the formatted output
        
    Returns:
        Formatted date string or "Not specified" if date_string is None
    """
    if not date_string:
        return "Not specified"
        
    try:
        due_datetime = datetime.fromisoformat(date_string)
        if include_time:
            formatted_date = due_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
        else:
            formatted_date = due_datetime.strftime("%A, %B %d, %Y")
        return formatted_date
    except (ValueError, TypeError):
        # If parsing fails, return the original string
        return date_string
    
def get_date_range_filter(days: int) -> tuple[str, str]:
    """
    Get ISO string date range for filtering.
    
    Args:
        days: Number of days to include in the range from today
        
    Returns:
        Tuple of (start_date_iso, end_date_iso)
    """
    from datetime import timedelta
    
    now = datetime.now()
    end_date = now + timedelta(days=days)
    
    # Convert to ISO format strings
    now_iso = now.isoformat()
    end_date_iso = end_date.isoformat()
    
    return (now_iso, end_date_iso)
    
def is_date_in_range(date_string: Optional[str], days: int) -> bool:
    """
    Check if a date is within a specific range from today.
    
    Args:
        date_string: ISO format date string or None
        days: Number of days to include in the range from today
        
    Returns:
        True if the date is within range, False otherwise or if date_string is None
    """
    if not date_string:
        return False
        
    try:
        date = datetime.fromisoformat(date_string)
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        return now <= date <= end_date
    except (ValueError, TypeError):
        return False