"""
Cache Management Utilities

This module provides utilities for managing caches within the Canvas MCP system.
It implements various caching strategies with expiration policies.
"""

import time
import logging
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages in-memory caches with TTL (time-to-live) expiration.
    
    This class provides a simple but effective caching mechanism for reducing
    redundant operations and API calls. Items in the cache expire after a 
    configurable TTL.
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
            max_size: Maximum number of items to store in the cache
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        
    def get(self, key: str) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        value, expiry_time = self.cache[key]
        current_time = time.time()
        
        if current_time > expiry_time:
            # Item has expired
            del self.cache[key]
            return None
            
        return value
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        # Evict items if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_items()
            
        # Set expiry time
        ttl = ttl if ttl is not None else self.default_ttl
        expiry_time = time.time() + ttl
        
        # Store in cache
        self.cache[key] = (value, expiry_time)
        
    def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was found and deleted, False otherwise
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
        
    def clear(self) -> None:
        """Clear all items from the cache."""
        self.cache.clear()
        
    def _evict_items(self) -> None:
        """
        Evict items from the cache when it's full.
        Uses a combination of expiration and LRU-like strategy.
        """
        current_time = time.time()
        
        # First, remove expired items
        expired_keys = [
            k for k, (_, expiry_time) in self.cache.items() 
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        # If still too many items, remove based on expiration time (closest to expiring)
        if len(self.cache) >= self.max_size:
            # Sort by expiry time (earliest first)
            sorted_items = sorted(
                self.cache.items(), 
                key=lambda item: item[1][1]  # Sort by expiry_time
            )
            
            # Remove oldest ~20% of items
            num_to_remove = max(1, len(sorted_items) // 5)
            for i in range(num_to_remove):
                if i < len(sorted_items):
                    del self.cache[sorted_items[i][0]]
                    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        current_time = time.time()
        active_items = 0
        expired_items = 0
        
        for _, expiry_time in self.cache.values():
            if current_time <= expiry_time:
                active_items += 1
            else:
                expired_items += 1
                
        return {
            "total_items": len(self.cache),
            "active_items": active_items,
            "expired_items": expired_items,
            "max_size": self.max_size
        }
        
    def cleanup(self) -> int:
        """
        Remove all expired items from the cache.
        
        Returns:
            Number of items removed
        """
        current_time = time.time()
        expired_keys = [
            k for k, (_, expiry_time) in self.cache.items() 
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        return len(expired_keys)