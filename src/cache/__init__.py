"""
MEB RAG Sistemi - Cache Module
Distributed Redis cache with automatic in-memory fallback
"""
from src.cache.base import BaseCache
from src.cache.memory_cache import MemoryCache
from src.cache.redis_cache import RedisCache
from src.cache.cache_manager import CacheManager

# Singleton cache instances
_embedding_cache = None
_llm_cache = None


def get_embedding_cache() -> CacheManager:
    """
    Get or create singleton embedding cache.

    Returns CacheManager with Redis + in-memory fallback.
    """
    global _embedding_cache
    if _embedding_cache is None:
        from config.settings import get_settings
        settings = get_settings()

        _embedding_cache = CacheManager(
            redis_url=settings.redis_url,
            name="embedding",
            max_size=settings.cache_max_size,
            redis_enabled=settings.redis_enabled,
            max_connections=settings.redis_max_connections
        )
    return _embedding_cache


def get_llm_cache() -> CacheManager:
    """
    Get or create singleton LLM response cache.

    Returns CacheManager with Redis + in-memory fallback.
    """
    global _llm_cache
    if _llm_cache is None:
        from config.settings import get_settings
        settings = get_settings()

        _llm_cache = CacheManager(
            redis_url=settings.redis_url,
            name="llm",
            max_size=settings.cache_max_size,
            redis_enabled=settings.redis_enabled,
            max_connections=settings.redis_max_connections
        )
    return _llm_cache


def get_all_cache_stats() -> dict:
    """Get statistics for all caches."""
    return {
        "embedding": get_embedding_cache().stats,
        "llm": get_llm_cache().stats
    }


async def clear_all_caches() -> None:
    """Clear all caches (async)."""
    await get_embedding_cache().clear()
    await get_llm_cache().clear()


def clear_all_caches_sync() -> None:
    """Clear all caches (sync - memory only)."""
    get_embedding_cache()._memory_cache.clear()
    get_llm_cache()._memory_cache.clear()


__all__ = [
    "BaseCache",
    "MemoryCache",
    "RedisCache",
    "CacheManager",
    "get_embedding_cache",
    "get_llm_cache",
    "get_all_cache_stats",
    "clear_all_caches",
    "clear_all_caches_sync"
]
