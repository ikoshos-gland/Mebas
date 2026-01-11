"""
MEB RAG Sistemi - Cache Module
Provides caching for embeddings and LLM responses
"""
from src.cache.base import BaseCache
from src.cache.memory_cache import MemoryCache

# Singleton cache instances
_embedding_cache = None
_llm_cache = None


def get_embedding_cache() -> MemoryCache:
    """Get or create singleton embedding cache."""
    global _embedding_cache
    if _embedding_cache is None:
        from config.settings import get_settings
        settings = get_settings()
        max_size = getattr(settings, 'cache_max_size', 10000)
        _embedding_cache = MemoryCache(max_size=max_size, name="embedding")
    return _embedding_cache


def get_llm_cache() -> MemoryCache:
    """Get or create singleton LLM response cache."""
    global _llm_cache
    if _llm_cache is None:
        from config.settings import get_settings
        settings = get_settings()
        max_size = getattr(settings, 'cache_max_size', 10000)
        _llm_cache = MemoryCache(max_size=max_size, name="llm")
    return _llm_cache


def get_all_cache_stats() -> dict:
    """Get statistics for all caches."""
    return {
        "embedding": get_embedding_cache().stats,
        "llm": get_llm_cache().stats
    }


def clear_all_caches() -> None:
    """Clear all caches."""
    get_embedding_cache().clear()
    get_llm_cache().clear()


__all__ = [
    "BaseCache",
    "MemoryCache", 
    "get_embedding_cache",
    "get_llm_cache",
    "get_all_cache_stats",
    "clear_all_caches"
]
