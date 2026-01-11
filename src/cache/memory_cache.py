"""
MEB RAG Sistemi - In-Memory Cache
Thread-safe LRU cache with TTL support
"""
from typing import Optional, Any, Dict, Tuple
import time
import threading
from collections import OrderedDict

from src.cache.base import BaseCache


class MemoryCache(BaseCache):
    """
    Thread-safe in-memory cache with TTL and LRU eviction.
    
    Features:
    - O(1) get/set operations
    - Automatic TTL-based expiration
    - LRU eviction when max_size is reached
    - Thread-safe with RLock
    - Hit/miss statistics
    """
    
    def __init__(self, max_size: int = 10000, name: str = "default"):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of entries before LRU eviction
            name: Cache name for logging/stats
        """
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._name = name
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Moves accessed key to end (LRU) and checks TTL.
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                
                if time.time() < expiry:
                    # Valid entry - move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    # Expired - remove it
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Store value in cache with TTL.
        
        Evicts LRU entries if at capacity.
        """
        with self._lock:
            # If key exists, update it
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, time.time() + ttl)
                return
            
            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                self._evict_one()
            
            # Add new entry
            self._cache[key] = (value, time.time() + ttl)
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        with self._lock:
            if key in self._cache:
                _, expiry = self._cache[key]
                if time.time() < expiry:
                    return True
                # Expired - clean it up
                del self._cache[key]
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries and reset stats."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def _evict_one(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            self._cache.popitem(last=False)
            self._evictions += 1
    
    def _evict_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            k for k, (_, expiry) in self._cache.items() 
            if now >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / max(1, total_requests)
            
            return {
                "name": self._name,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 4),
                "hit_rate_percent": f"{hit_rate * 100:.1f}%"
            }
    
    def __len__(self) -> int:
        """Return current cache size."""
        return len(self._cache)
    
    def __repr__(self) -> str:
        return f"MemoryCache(name='{self._name}', size={len(self)}, max={self._max_size})"
