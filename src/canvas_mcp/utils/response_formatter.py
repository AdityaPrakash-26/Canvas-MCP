"""
Response Formatting Utilities

This module provides standardized response formatting for Canvas MCP operations.
It ensures consistent structure for success and error responses.
"""

import logging
import traceback
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    Formats responses from operations into a consistent structure.
    
    This class ensures all responses follow a standard format, making it
    easier for clients to process results and for operations to remain
    consistent in how they communicate success and failure.
    """
    
    def format_success_response(
        self, 
        data: Any, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a successful operation response.
        
        Args:
            data: Response data
            metadata: Optional metadata about the operation
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "success": True,
            "data": data
        }
        
        if metadata:
            response["metadata"] = metadata
            
        return response
    
    def format_error_response(
        self, 
        error: Exception, 
        metadata: Optional[Dict[str, Any]] = None,
        include_traceback: bool = False
    ) -> Dict[str, Any]:
        """
        Format an error response.
        
        Args:
            error: Exception that occurred
            metadata: Optional metadata about the operation
            include_traceback: Whether to include a stack trace
            
        Returns:
            Formatted error response dictionary
        """
        error_response = {
            "success": False,
            "error": {
                "type": error.__class__.__name__,
                "message": str(error)
            }
        }
        
        if include_traceback:
            error_response["error"]["traceback"] = traceback.format_exc()
            
        if metadata:
            error_response["metadata"] = metadata
            
        return error_response
    
    def format_partial_success_response(
        self, 
        data: Any, 
        error: Exception,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a partially successful operation response.
        
        Args:
            data: Partial response data
            error: Exception that caused partial failure
            metadata: Optional metadata about the operation
            
        Returns:
            Formatted partial success response dictionary
        """
        response = {
            "success": True,
            "partial": True,
            "data": data,
            "error": {
                "type": error.__class__.__name__,
                "message": str(error)
            }
        }
        
        if metadata:
            response["metadata"] = metadata
            
        return response