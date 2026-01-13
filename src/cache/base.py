"""
MEB RAG Sistemi - Base Cache Interface
Abstract base class for cache implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import hashlib
import json


class BaseCache(ABC):
    """
    Abstract base class for caching implementations.
    
    Provides common utilities like key generation and
    defines the interface for cache operations.
    """
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate a deterministic hash key from arguments.
        
        Args:
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash
            
        Returns:
            32-character hex string key
        """
        try:
            content = json.dumps(
                {"args": args, "kwargs": kwargs}, 
                sort_keys=True, 
                default=str,
                ensure_ascii=False
            )
        except (TypeError, ValueError):
            # Fallback for non-serializable content
            content = str(args) + str(kwargs)
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default 1 hour)
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is valid
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from cache."""
        pass
    
    @property
    @abstractmethod
    def stats(self) -> dict:
        """Get cache statistics."""
        pass
