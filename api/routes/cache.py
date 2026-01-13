"""
MEB RAG Sistemi - Cache Routes
Cache statistics and management endpoints
"""
from fastapi import APIRouter

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.get("/stats")
async def get_cache_stats():
    """
    Get cache statistics.

    Returns hit/miss rates, Redis status, and other metrics
    for embedding and LLM caches.
    """
    try:
        from src.cache import get_all_cache_stats
        return {
            "status": "ok",
            "caches": get_all_cache_stats()
        }
    except ImportError:
        return {
            "status": "disabled",
            "message": "Cache module not available"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/clear")
async def clear_caches():
    """
    Clear all caches (Redis + in-memory).

    Use with caution - this will force all embeddings
    and responses to be regenerated.
    """
    try:
        from src.cache import clear_all_caches, get_all_cache_stats

        # Get stats before clearing
        before = get_all_cache_stats()

        # Clear (async operation)
        await clear_all_caches()

        return {
            "status": "cleared",
            "message": "All caches cleared (Redis + in-memory)",
            "previous_stats": before
        }
    except ImportError:
        return {
            "status": "disabled",
            "message": "Cache module not available"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/health")
async def cache_health():
    """
    Check cache health.

    Tests both Redis and in-memory cache functionality.
    """
    try:
        from src.cache import get_embedding_cache, get_llm_cache

        # Quick functional test
        embed_cache = get_embedding_cache()
        llm_cache = get_llm_cache()

        test_key = "__health_check__"

        # Test async operations
        await embed_cache.set(test_key, "ok", ttl=5)
        await llm_cache.set(test_key, "ok", ttl=5)

        embed_value = await embed_cache.get(test_key)
        llm_value = await llm_cache.get(test_key)

        embed_ok = embed_value == "ok"
        llm_ok = llm_value == "ok"

        # Cleanup
        await embed_cache.delete(test_key)
        await llm_cache.delete(test_key)

        if embed_ok and llm_ok:
            return {
                "status": "healthy",
                "embedding_cache": "ok",
                "llm_cache": "ok",
                "redis_available": embed_cache._redis_available
            }
        else:
            return {
                "status": "degraded",
                "embedding_cache": "ok" if embed_ok else "failed",
                "llm_cache": "ok" if llm_ok else "failed",
                "redis_available": embed_cache._redis_available
            }

    except Exception as e:
        return {"status": "error", "error": str(e)}
