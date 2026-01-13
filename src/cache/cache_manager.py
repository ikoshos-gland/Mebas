"""
MEB RAG Sistemi - Cache Manager
Automatic fallback from Redis to in-memory cache
"""
from typing import Optional, Any
import asyncio
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.cache.redis_cache import RedisCache
from src.cache.memory_cache import MemoryCache


class CacheManager:
    """
    Smart cache manager with automatic fallback.

    Tries Redis first, falls back to in-memory cache if Redis is unavailable.
    Provides both sync and async interfaces.
    """

    def __init__(
        self,
        redis_url: str,
        name: str = "default",
        max_size: int = 10000,
        redis_enabled: bool = True,
        max_connections: int = 50
    ):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            name: Cache name
            max_size: Max size for in-memory fallback cache
            redis_enabled: Whether to try using Redis
            max_connections: Max Redis connections
        """
        self._name = name
        self._redis_enabled = redis_enabled
        self._redis_available = False

        # Always create in-memory cache as fallback
        self._memory_cache = MemoryCache(max_size=max_size, name=f"{name}_memory")

        # Create Redis cache if enabled
        self._redis_cache: Optional[RedisCache] = None
        if redis_enabled:
            try:
                self._redis_cache = RedisCache(
                    url=redis_url,
                    name=name,
                    max_connections=max_connections
                )
            except Exception:
                # Redis initialization failed - use memory cache only
                self._redis_enabled = False

    async def _check_redis_health(self) -> bool:
        """Check if Redis is available."""
        if not self._redis_enabled or not self._redis_cache:
            return False

        try:
            # Quick health check
            await self._redis_cache.set("__health__", "ok", ttl=5, school_id=None)
            result = await self._redis_cache.get("__health__", school_id=None)
            await self._redis_cache.delete("__health__", school_id=None)
            return result == "ok"
        except (RedisError, RedisConnectionError):
            return False

    async def get(self, key: str, school_id: Optional[int] = None) -> Optional[Any]:
        """
        Get value from cache (async).

        Tries Redis first, falls back to memory cache.

        Args:
            key: Cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            Cached value or None
        """
        # Try Redis first if available
        if self._redis_enabled and self._redis_cache:
            try:
                value = await self._redis_cache.get(key, school_id)
                if value is not None:
                    self._redis_available = True
                    return value
            except (RedisError, RedisConnectionError):
                # Redis failed - mark as unavailable and fall back
                self._redis_available = False

        # Fallback to memory cache (sync operation)
        # For tenant-aware memory cache, we include school_id in the key
        memory_key = f"school:{school_id}:{key}" if school_id else key
        return self._memory_cache.get(memory_key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        school_id: Optional[int] = None
    ) -> None:
        """
        Set value in cache (async).

        Stores in both Redis and memory cache for redundancy.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            school_id: Optional school ID for tenant isolation
        """
        # Try Redis first
        if self._redis_enabled and self._redis_cache:
            try:
                await self._redis_cache.set(key, value, ttl, school_id)
                self._redis_available = True
            except (RedisError, RedisConnectionError):
                self._redis_available = False

        # Always store in memory cache as fallback
        memory_key = f"school:{school_id}:{key}" if school_id else key
        self._memory_cache.set(memory_key, value, ttl)

    async def exists(self, key: str, school_id: Optional[int] = None) -> bool:
        """Check if key exists in cache."""
        if self._redis_enabled and self._redis_cache:
            try:
                return await self._redis_cache.exists(key, school_id)
            except (RedisError, RedisConnectionError):
                pass

        memory_key = f"school:{school_id}:{key}" if school_id else key
        return self._memory_cache.exists(memory_key)

    async def delete(self, key: str, school_id: Optional[int] = None) -> bool:
        """Delete key from cache."""
        deleted = False

        if self._redis_enabled and self._redis_cache:
            try:
                deleted = await self._redis_cache.delete(key, school_id)
            except (RedisError, RedisConnectionError):
                pass

        memory_key = f"school:{school_id}:{key}" if school_id else key
        deleted = self._memory_cache.delete(memory_key) or deleted

        return deleted

    async def clear(self, school_id: Optional[int] = None) -> None:
        """Clear cache entries."""
        if self._redis_enabled and self._redis_cache:
            try:
                await self._redis_cache.clear(school_id)
            except (RedisError, RedisConnectionError):
                pass

        # Clear memory cache
        if school_id is None:
            self._memory_cache.clear()
        else:
            # Clear only entries for this school from memory
            # This is a simplified approach - real implementation would need pattern matching
            pass

    def get_sync(self, key: str, school_id: Optional[int] = None) -> Optional[Any]:
        """
        Synchronous get operation.

        For compatibility with non-async code. Only uses memory cache.

        Args:
            key: Cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            Cached value or None
        """
        memory_key = f"school:{school_id}:{key}" if school_id else key
        return self._memory_cache.get(memory_key)

    def set_sync(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        school_id: Optional[int] = None
    ) -> None:
        """
        Synchronous set operation.

        For compatibility with non-async code. Only uses memory cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            school_id: Optional school ID for tenant isolation
        """
        memory_key = f"school:{school_id}:{key}" if school_id else key
        self._memory_cache.set(memory_key, value, ttl)

    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        base_stats = {
            "name": self._name,
            "redis_enabled": self._redis_enabled,
            "redis_available": self._redis_available,
            "memory_cache": self._memory_cache.stats
        }

        # Try to get Redis stats
        if self._redis_enabled and self._redis_cache:
            try:
                base_stats["redis_cache"] = self._redis_cache.stats
            except Exception:
                base_stats["redis_cache"] = {"status": "unavailable"}

        return base_stats

    def __repr__(self) -> str:
        status = "redis" if self._redis_available else "memory"
        return f"CacheManager(name='{self._name}', backend='{status}')"
