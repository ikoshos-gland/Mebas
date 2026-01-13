"""
MEB RAG Sistemi - Redis Cache Implementation
Distributed cache with tenant isolation support
"""
from typing import Optional, Any
import json
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.cache.base import BaseCache


class RedisCache(BaseCache):
    """
    Distributed Redis cache with tenant-aware keys.

    Features:
    - Tenant isolation via school_id prefixes
    - Async operations with connection pooling
    - Automatic JSON serialization
    - TTL support
    - Statistics tracking
    """

    def __init__(
        self,
        url: str = "redis://redis:6379",
        name: str = "default",
        max_connections: int = 50
    ):
        """
        Initialize Redis cache.

        Args:
            url: Redis connection URL
            name: Cache name for logging/stats
            max_connections: Max connections in pool
        """
        self._url = url
        self._name = name
        self._max_connections = max_connections
        self._client: Optional[Redis] = None
        self._hits = 0
        self._misses = 0
        self._errors = 0

    async def _get_client(self) -> Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self._max_connections,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self._client

    def _make_key(self, key: str, school_id: Optional[int] = None) -> str:
        """
        Generate tenant-aware cache key.

        Args:
            key: Base cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            Prefixed key: "cache:{name}:school:{school_id}:{key}" or "cache:{name}:{key}"
        """
        if school_id is not None:
            return f"cache:{self._name}:school:{school_id}:{key}"
        return f"cache:{self._name}:{key}"

    async def get(self, key: str, school_id: Optional[int] = None) -> Optional[Any]:
        """
        Retrieve value from Redis cache.

        Args:
            key: Cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            Cached value or None if not found
        """
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key, school_id)

            data = await client.get(prefixed_key)

            if data is not None:
                self._hits += 1
                return json.loads(data)

            self._misses += 1
            return None

        except (RedisError, json.JSONDecodeError) as e:
            self._errors += 1
            # Log error but don't crash - return cache miss
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        school_id: Optional[int] = None
    ) -> None:
        """
        Store value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds
            school_id: Optional school ID for tenant isolation
        """
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key, school_id)

            # Serialize to JSON
            serialized = json.dumps(value, ensure_ascii=False, default=str)

            # Store with TTL
            await client.setex(prefixed_key, ttl, serialized)

        except (RedisError, TypeError, ValueError) as e:
            self._errors += 1
            # Silently fail - cache is optional
            pass

    async def exists(self, key: str, school_id: Optional[int] = None) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            True if key exists
        """
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key, school_id)
            return await client.exists(prefixed_key) > 0
        except RedisError:
            self._errors += 1
            return False

    async def delete(self, key: str, school_id: Optional[int] = None) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key
            school_id: Optional school ID for tenant isolation

        Returns:
            True if key was deleted
        """
        try:
            client = await self._get_client()
            prefixed_key = self._make_key(key, school_id)
            result = await client.delete(prefixed_key)
            return result > 0
        except RedisError:
            self._errors += 1
            return False

    async def clear(self, school_id: Optional[int] = None) -> None:
        """
        Clear cache entries.

        Args:
            school_id: If provided, only clear entries for this school.
                      If None, clear all entries for this cache name.
        """
        try:
            client = await self._get_client()

            if school_id is not None:
                # Clear only for specific school
                pattern = f"cache:{self._name}:school:{school_id}:*"
            else:
                # Clear all for this cache name
                pattern = f"cache:{self._name}:*"

            # Scan and delete matching keys
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break

            # Reset stats if clearing all
            if school_id is None:
                self._hits = 0
                self._misses = 0
                self._errors = 0

        except RedisError as e:
            self._errors += 1
            pass

    async def get_stats(self) -> dict:
        """Get cache statistics including Redis info."""
        try:
            client = await self._get_client()
            info = await client.info("stats")

            total_requests = self._hits + self._misses
            hit_rate = self._hits / max(1, total_requests)

            return {
                "name": self._name,
                "type": "redis",
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "hit_rate": round(hit_rate, 4),
                "hit_rate_percent": f"{hit_rate * 100:.1f}%",
                "redis_connected": True,
                "redis_total_commands": info.get("total_commands_processed", 0),
                "redis_keyspace_hits": info.get("keyspace_hits", 0),
                "redis_keyspace_misses": info.get("keyspace_misses", 0)
            }
        except RedisError:
            return {
                "name": self._name,
                "type": "redis",
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "redis_connected": False,
                "error": "Redis connection failed"
            }

    @property
    def stats(self) -> dict:
        """Sync property wrapper for stats (requires event loop)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't block in running loop - return basic stats
                total_requests = self._hits + self._misses
                hit_rate = self._hits / max(1, total_requests)
                return {
                    "name": self._name,
                    "type": "redis",
                    "hits": self._hits,
                    "misses": self._misses,
                    "errors": self._errors,
                    "hit_rate": round(hit_rate, 4),
                    "hit_rate_percent": f"{hit_rate * 100:.1f}%"
                }
            else:
                return loop.run_until_complete(self.get_stats())
        except RuntimeError:
            # No event loop - create one
            return asyncio.run(self.get_stats())

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def __repr__(self) -> str:
        return f"RedisCache(name='{self._name}', url='{self._url}')"
