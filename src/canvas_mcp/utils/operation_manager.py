"""
Operation Manager for Canvas MCP

This module provides a centralized manager for operations within the Canvas MCP system.
It coordinates between different components, handles errors, implements retries, and
manages operation status.
"""

import time
import logging
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast
from datetime import datetime, timedelta

from canvas_mcp.utils.cache_manager import CacheManager
from canvas_mcp.utils.response_formatter import ResponseFormatter

# Type variable for the return type
T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)

class OperationStatus:
    """Status of an operation in the system"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    PARTIALLY_SUCCEEDED = "partially_succeeded"


class Operation:
    """Represents an operation in the system with its status and metadata"""
    
    def __init__(self, operation_id: str, params: Dict[str, Any]):
        """
        Initialize a new operation.
        
        Args:
            operation_id: Unique identifier for the operation
            params: Parameters for the operation
        """
        self.id = operation_id
        self.params = params
        self.status = OperationStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.attempts = 0
        self.error = None
        self.result = None
        
    def mark_started(self):
        """Mark the operation as started"""
        self.status = OperationStatus.IN_PROGRESS
        self.start_time = datetime.now()
        
    def mark_succeeded(self, result: Any):
        """
        Mark the operation as succeeded.
        
        Args:
            result: Result of the operation
        """
        self.status = OperationStatus.SUCCEEDED
        self.end_time = datetime.now()
        self.result = result
        
    def mark_failed(self, error: Exception):
        """
        Mark the operation as failed.
        
        Args:
            error: Exception that caused the failure
        """
        self.status = OperationStatus.FAILED
        self.end_time = datetime.now()
        self.error = error
        
    def mark_retrying(self):
        """Mark the operation as retrying"""
        self.status = OperationStatus.RETRYING
        self.attempts += 1
        
    def mark_partially_succeeded(self, result: Any, error: Exception):
        """
        Mark the operation as partially succeeded.
        
        Args:
            result: Partial result of the operation
            error: Exception that caused the partial failure
        """
        self.status = OperationStatus.PARTIALLY_SUCCEEDED
        self.end_time = datetime.now()
        self.result = result
        self.error = error
        
    def get_duration(self) -> Optional[float]:
        """
        Get the duration of the operation in seconds.
        
        Returns:
            Duration in seconds or None if the operation has not completed
        """
        if self.start_time is None:
            return None
            
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the operation to a dictionary.
        
        Returns:
            Dictionary representation of the operation
        """
        return {
            "id": self.id,
            "params": self.params,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration(),
            "attempts": self.attempts,
            "error": str(self.error) if self.error else None
        }


class OperationManager:
    """
    Manager for operations in the Canvas MCP system.
    
    This class coordinates between different components, handles retries,
    manages operation status, and provides caching.
    """
    
    def __init__(self, 
                 cache_manager: Optional[CacheManager] = None,
                 response_formatter: Optional[ResponseFormatter] = None,
                 max_retry_attempts: int = 3,
                 initial_retry_delay: float = 0.5,
                 retry_backoff_factor: float = 2.0,
                 operation_timeout: int = 60):
        """
        Initialize the operation manager.
        
        Args:
            cache_manager: Cache manager instance (creates one if None)
            response_formatter: Response formatter instance (creates one if None)
            max_retry_attempts: Maximum number of retry attempts
            initial_retry_delay: Initial delay between retries (seconds)
            retry_backoff_factor: Exponential backoff factor for retries
            operation_timeout: Maximum time an operation can run (seconds)
        """
        self.cache_manager = cache_manager or CacheManager()
        self.response_formatter = response_formatter or ResponseFormatter()
        self.max_retry_attempts = max_retry_attempts
        self.initial_retry_delay = initial_retry_delay
        self.retry_backoff_factor = retry_backoff_factor
        self.operation_timeout = operation_timeout
        
        # Track active operations
        self.active_operations: Dict[str, Operation] = {}
        
        # Operation history (recent operations)
        self.operation_history: List[Operation] = []
        self.max_history_size = 50
        
    def generate_operation_key(self, operation_id: str, params: Dict[str, Any]) -> str:
        """
        Generate a unique key for an operation based on its ID and parameters.
        
        Args:
            operation_id: Operation ID
            params: Operation parameters
            
        Returns:
            Unique operation key for caching
        """
        # Convert parameters to a sorted string representation
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{operation_id}:{param_str}"
        
    def execute(self, 
                operation_id: str,
                operation_func: Callable[..., T],
                operation_params: Dict[str, Any],
                cache_ttl: Optional[int] = None,
                allow_partial_results: bool = False,
                force_refresh: bool = False) -> Dict[str, Any]:
        """
        Execute an operation with proper error handling, retries, and caching.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_func: Function to execute
            operation_params: Parameters for the function
            cache_ttl: Time-to-live for cached results (seconds, None for no caching)
            allow_partial_results: Whether to allow partial results on failure
            force_refresh: Whether to force a refresh (ignore cache)
            
        Returns:
            Standardized response dictionary with the operation result or error
        """
        # Create operation object
        operation = Operation(operation_id, operation_params)
        operation_key = self.generate_operation_key(operation_id, operation_params)
        
        # Add to active operations
        self.active_operations[operation_key] = operation
        
        # Check cache first unless force refresh is requested
        if cache_ttl is not None and not force_refresh:
            cached_result = self.cache_manager.get(operation_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for operation: {operation_id}")
                
                # Cache hit, bypass execution
                operation.mark_started()
                operation.mark_succeeded(cached_result)
                self._update_history(operation)
                
                result = self.response_formatter.format_success_response(
                    data=cached_result,
                    metadata={
                        "operation_id": operation_id,
                        "cached": True,
                        "params": operation_params
                    }
                )
                return result
        
        # Execute operation with retries
        try:
            operation.mark_started()
            logger.debug(f"Starting operation: {operation_id}")
            
            result = self._execute_with_retries(
                operation=operation,
                func=operation_func,
                params=operation_params,
                allow_partial=allow_partial_results
            )
            
            # Cache successful results if caching is enabled
            if cache_ttl is not None and operation.status == OperationStatus.SUCCEEDED:
                self.cache_manager.set(operation_key, result, ttl=cache_ttl)
            
            # Format the response based on operation status
            if operation.status == OperationStatus.SUCCEEDED:
                response = self.response_formatter.format_success_response(
                    data=result,
                    metadata={
                        "operation_id": operation_id,
                        "cached": False,
                        "duration": operation.get_duration(),
                        "params": operation_params
                    }
                )
            elif operation.status == OperationStatus.PARTIALLY_SUCCEEDED:
                response = self.response_formatter.format_partial_success_response(
                    data=result,
                    error=operation.error,
                    metadata={
                        "operation_id": operation_id,
                        "cached": False,
                        "duration": operation.get_duration(),
                        "params": operation_params
                    }
                )
            else:
                # Should not happen, but handle just in case
                response = self.response_formatter.format_error_response(
                    error=operation.error or Exception("Unknown error"),
                    metadata={
                        "operation_id": operation_id,
                        "cached": False,
                        "duration": operation.get_duration(),
                        "params": operation_params
                    }
                )
            
            self._update_history(operation)
            return response
            
        except Exception as e:
            # Unexpected error during operation handling
            logger.error(f"Unexpected error in operation {operation_id}: {e}")
            logger.debug(traceback.format_exc())
            
            operation.mark_failed(e)
            self._update_history(operation)
            
            return self.response_formatter.format_error_response(
                error=e,
                metadata={
                    "operation_id": operation_id,
                    "cached": False,
                    "duration": operation.get_duration(),
                    "params": operation_params
                }
            )
        finally:
            # Remove from active operations
            if operation_key in self.active_operations:
                del self.active_operations[operation_key]
    
    def _execute_with_retries(self, 
                             operation: Operation,
                             func: Callable[..., T],
                             params: Dict[str, Any],
                             allow_partial: bool) -> Any:
        """
        Execute a function with automatic retries.
        
        Args:
            operation: Operation object to track status
            func: Function to execute
            params: Parameters for the function
            allow_partial: Whether to allow partial results
            
        Returns:
            Result of the function execution
        """
        last_error = None
        
        for attempt in range(self.max_retry_attempts):
            try:
                # First attempt or retry
                if attempt > 0:
                    operation.mark_retrying()
                    
                    # Calculate delay with exponential backoff
                    delay = self.initial_retry_delay * (self.retry_backoff_factor ** (attempt - 1))
                    logger.debug(f"Retrying operation {operation.id}, attempt {attempt + 1}/{self.max_retry_attempts} after {delay:.2f}s")
                    time.sleep(delay)
                
                # Execute the function
                result = func(**params)
                
                # Success
                operation.mark_succeeded(result)
                return result
                
            except Exception as e:
                # Check if this is a retriable error
                if self._is_retriable_error(e):
                    logger.debug(f"Retriable error in operation {operation.id}, attempt {attempt + 1}: {e}")
                    last_error = e
                    continue
                else:
                    # Non-retriable error, fail immediately
                    logger.error(f"Non-retriable error in operation {operation.id}: {e}")
                    operation.mark_failed(e)
                    raise
        
        # All retry attempts failed
        if allow_partial and hasattr(last_error, 'partial_result'):
            # Allow partial results if available
            partial_result = getattr(last_error, 'partial_result', None)
            operation.mark_partially_succeeded(partial_result, last_error)
            return partial_result
        else:
            # Complete failure
            operation.mark_failed(last_error)
            raise last_error
    
    def _is_retriable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retriable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if the error is retriable, False otherwise
        """
        # Retriable errors: network issues, timeouts, rate limits
        retriable_error_types = (
            TimeoutError,
            ConnectionError,
            ConnectionResetError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,  # For 429, 500, 502, 503, 504
        )
        
        if isinstance(error, retriable_error_types):
            return True
        
        # Check for HTTP error status codes that are retriable
        if isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, 'status_code', 0)
            return status_code in (429, 500, 502, 503, 504)
            
        # Some errors might have 'is_retriable' attribute
        if hasattr(error, 'is_retriable'):
            return bool(error.is_retriable)
            
        return False
    
    def _update_history(self, operation: Operation):
        """
        Update operation history.
        
        Args:
            operation: Completed operation to add to history
        """
        # Add to history
        self.operation_history.append(operation)
        
        # Trim history if needed
        if len(self.operation_history) > self.max_history_size:
            self.operation_history = self.operation_history[-self.max_history_size:]
    
    def get_operation_status(self, operation_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the status of an operation.
        
        Args:
            operation_id: Operation ID
            params: Operation parameters
            
        Returns:
            Status dictionary or None if not found
        """
        operation_key = self.generate_operation_key(operation_id, params)
        
        # Check active operations
        if operation_key in self.active_operations:
            return self.active_operations[operation_key].to_dict()
            
        # Check history
        for op in reversed(self.operation_history):
            if self.generate_operation_key(op.id, op.params) == operation_key:
                return op.to_dict()
                
        return None
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """
        Get all active operations.
        
        Returns:
            List of active operation dictionaries
        """
        return [op.to_dict() for op in self.active_operations.values()]
    
    def get_operation_history(self) -> List[Dict[str, Any]]:
        """
        Get operation history.
        
        Returns:
            List of recent operation dictionaries
        """
        return [op.to_dict() for op in self.operation_history]
    
    def cancel_operation(self, operation_id: str, params: Dict[str, Any]) -> bool:
        """
        Cancel an active operation if possible.
        
        Args:
            operation_id: Operation ID
            params: Operation parameters
            
        Returns:
            True if the operation was cancelled, False otherwise
        """
        # Currently a placeholder for future implementation
        # Would likely involve timeout or interrupt mechanism
        logger.warning("Operation cancellation not yet implemented")
        return False


# Create a singleton instance for convenience
operation_manager = OperationManager()


def with_operation_manager(operation_id: str,
                          cache_ttl: Optional[int] = 300,
                          allow_partial_results: bool = False):
    """
    Decorator for functions that should be managed by the operation manager.
    
    Args:
        operation_id: Base operation ID (will be combined with function name)
        cache_ttl: Time-to-live for cached results (seconds, None for no caching)
        allow_partial_results: Whether to allow partial results on failure
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Combine base ID with function name
            full_operation_id = f"{operation_id}.{func.__name__}"
            
            # Extract force_refresh from kwargs if present
            force_refresh = kwargs.pop('force_refresh', False)
            
            # Execute via operation manager
            return operation_manager.execute(
                operation_id=full_operation_id,
                operation_func=func,
                operation_params=kwargs,
                cache_ttl=cache_ttl,
                allow_partial_results=allow_partial_results,
                force_refresh=force_refresh
            )
        return wrapper
    return decorator
