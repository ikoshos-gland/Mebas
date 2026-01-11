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
    
    Returns hit/miss rates, sizes, and other metrics
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


@router.post("/clear")
async def clear_caches():
    """
    Clear all caches.
    
    Use with caution - this will force all embeddings
    and responses to be regenerated.
    """
    try:
        from src.cache import clear_all_caches, get_all_cache_stats
        
        # Get stats before clearing
        before = get_all_cache_stats()
        
        # Clear
        clear_all_caches()
        
        return {
            "status": "cleared",
            "cleared_entries": {
                "embedding": before["embedding"]["size"],
                "llm": before["llm"]["size"]
            }
        }
    except ImportError:
        return {
            "status": "disabled",
            "message": "Cache module not available"
        }


@router.get("/health")
async def cache_health():
    """
    Check cache health.
    
    Returns OK if caches are functioning properly.
    """
    try:
        from src.cache import get_embedding_cache, get_llm_cache
        
        # Quick functional test
        embed_cache = get_embedding_cache()
        llm_cache = get_llm_cache()
        
        test_key = "__health_check__"
        embed_cache.set(test_key, "ok", ttl=1)
        llm_cache.set(test_key, "ok", ttl=1)
        
        embed_ok = embed_cache.get(test_key) == "ok"
        llm_ok = llm_cache.get(test_key) == "ok"
        
        # Cleanup
        embed_cache.delete(test_key)
        llm_cache.delete(test_key)
        
        if embed_ok and llm_ok:
            return {"status": "healthy", "embedding_cache": "ok", "llm_cache": "ok"}
        else:
            return {"status": "degraded", "embedding_cache": embed_ok, "llm_cache": llm_ok}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}
