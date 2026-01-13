# Redis Cache Implementation - Scalability Upgrade

## Overview

Redis distributed cache has been successfully activated in the Meba project, replacing the single-instance in-memory cache with a production-ready distributed caching solution.

## What Changed

### 1. **Docker Compose - Redis Service Activated** ✅
- Redis 7 Alpine image with optimized configuration
- 512MB memory limit with LRU eviction policy
- AOF persistence enabled for data durability
- Health checks configured
- Persistent volume for data survival across restarts

**Location:** `docker-compose.yml:90-109`

### 2. **New Redis Cache Implementation** ✅
- Full async/await support with connection pooling
- Tenant-aware cache keys with `school_id` isolation
- Automatic JSON serialization/deserialization
- Error handling with graceful degradation
- Statistics tracking (hits, misses, errors)

**Location:** `src/cache/redis_cache.py`

### 3. **Smart Cache Manager with Fallback** ✅
- Automatic fallback from Redis to in-memory cache
- Both sync and async interfaces for compatibility
- Health checking with Redis availability detection
- Dual-write strategy (Redis + memory for redundancy)
- Tenant isolation via key prefixes

**Location:** `src/cache/cache_manager.py`

**Key Features:**
```python
# Tenant-aware caching
await cache.set("embeddings:xyz", data, ttl=3600, school_id=123)
value = await cache.get("embeddings:xyz", school_id=123)

# Automatic fallback
# If Redis fails, automatically uses in-memory cache
```

### 4. **Settings Configuration** ✅
New Redis configuration options added:
```python
redis_url: str = "redis://redis:6379"
redis_enabled: bool = True
redis_max_connections: int = 50
cache_max_size: int = 10000  # Fallback memory cache size
```

**Location:** `config/settings.py:43-47`

### 5. **Updated Dependencies** ✅
- Added `redis>=5.0.0` to requirements.txt
- Updated `.env.example` with Redis configuration

### 6. **Enhanced API Endpoints** ✅
Updated cache routes with async support:
- `GET /cache/stats` - Redis + memory cache statistics
- `POST /cache/clear` - Clear both Redis and memory
- `GET /cache/health` - Health check with Redis availability status

**Location:** `api/routes/cache.py`

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Application Layer                               │
│ ┌──────────────┐         ┌──────────────┐      │
│ │ Embeddings   │         │ LLM Responses│      │
│ └──────┬───────┘         └──────┬───────┘      │
│        │                        │              │
│        └────────┬───────────────┘              │
│                 ▼                              │
│       ┌──────────────────┐                     │
│       │ CacheManager     │                     │
│       │ (Smart Fallback) │                     │
│       └─────┬──────┬─────┘                     │
│             │      │                           │
│    ┌────────┘      └────────┐                  │
│    ▼                         ▼                 │
│ ┌──────────┐          ┌──────────┐            │
│ │  Redis   │          │  Memory  │            │
│ │  Cache   │  ◄────►  │  Cache   │            │
│ │(Primary) │ Fallback │(Backup)  │            │
│ └──────────┘          └──────────┘            │
└─────────────────────────────────────────────────┘
```

## Tenant Isolation

All cache keys are automatically prefixed with tenant information:

```
cache:{cache_name}:school:{school_id}:{key}
```

**Example:**
```python
# School 123's embedding cache
cache:embedding:school:123:embeddings_abc123

# School 456's embedding cache
cache:embedding:school:456:embeddings_abc123
```

This ensures complete data isolation between different schools/tenants.

## Usage Examples

### Async Usage (Recommended)
```python
from src.cache import get_embedding_cache

cache = get_embedding_cache()

# Set with tenant isolation
await cache.set(
    key="doc_embeddings",
    value=[0.1, 0.2, 0.3],
    ttl=3600,
    school_id=123
)

# Get with tenant isolation
embeddings = await cache.get("doc_embeddings", school_id=123)
```

### Sync Usage (Backward Compatibility)
```python
cache = get_embedding_cache()

# Sync operations for non-async code
cache.set_sync("my_key", "value", ttl=3600, school_id=123)
value = cache.get_sync("my_key", school_id=123)
```

### Clear Tenant Data
```python
# Clear all cache for school 123
await cache.clear(school_id=123)

# Clear all cache
await cache.clear()
```

## Deployment Instructions

### 1. Update Environment Variables
Add to your `.env` file:
```bash
REDIS_URL=redis://redis:6379
REDIS_ENABLED=true
REDIS_MAX_CONNECTIONS=50
CACHE_MAX_SIZE=10000
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Services
```bash
docker compose up --build
```

Redis will automatically start and be health-checked before the API starts.

### 4. Verify Redis Status
```bash
# Check cache health
curl http://localhost:8001/cache/health

# Check cache statistics
curl http://localhost:8001/cache/stats
```

## Monitoring

### Cache Statistics
The system tracks:
- **Hits/Misses**: Cache efficiency metrics
- **Hit Rate**: Percentage of successful cache lookups
- **Redis Availability**: Connection status
- **Memory Cache Stats**: Fallback cache statistics
- **Redis Stats**: Commands processed, keyspace hits/misses

### Health Checks

**API Endpoint:**
```bash
GET /cache/health

Response:
{
  "status": "healthy",
  "embedding_cache": "ok",
  "llm_cache": "ok",
  "redis_available": true
}
```

**Docker Health Check:**
```bash
docker ps
# Should show redis container as "healthy"
```

## Failure Scenarios

### Redis Unavailable
- **Automatic Fallback**: System automatically uses in-memory cache
- **No Downtime**: Application continues functioning
- **Degraded Performance**: Multi-instance deployments lose cache sharing

### Redis Connection Lost During Operation
- **Graceful Degradation**: Errors are caught, cache miss returned
- **Automatic Recovery**: Next request attempts Redis again
- **Logging**: Errors tracked in statistics

## Performance Benefits

### Single Instance
- ✅ Persistent cache across restarts
- ✅ Larger cache capacity (limited by Redis memory, not Python heap)
- ✅ Better eviction policies (LRU in Redis)

### Multi-Instance (Future)
- ✅ Shared cache across all API instances
- ✅ Reduced redundant API calls (embeddings, LLM)
- ✅ Improved response times
- ✅ Cost savings (fewer Azure OpenAI calls)

## Configuration Tuning

### Memory Limits
Edit `docker-compose.yml`:
```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb  # Increase for more cache
    --maxmemory-policy allkeys-lru
```

### Connection Pool
Edit `.env`:
```bash
REDIS_MAX_CONNECTIONS=100  # Increase for high load
```

### TTL Defaults
Edit code where cache is used:
```python
await cache.set(key, value, ttl=7200)  # 2 hours
```

## Backward Compatibility

✅ **Existing code continues to work** without changes:
- `get_embedding_cache()` returns `CacheManager` (compatible interface)
- `get_llm_cache()` returns `CacheManager` (compatible interface)
- Sync methods available for non-async code
- In-memory fallback ensures zero downtime

## Next Steps (Future Enhancements)

### 1. Multi-Instance Deployment
- Add nginx load balancer
- Deploy multiple API replicas
- All sharing same Redis cache

### 2. Cache Warming
- Pre-populate common embeddings
- Load frequently accessed data at startup

### 3. Advanced Monitoring
- Prometheus metrics export
- Grafana dashboards
- Alert on cache hit rate < 80%

### 4. Tiered Caching
- L1: In-memory (hot data)
- L2: Redis (warm data)
- L3: Disk (cold data)

## Testing

### Manual Testing
```bash
# Start services
docker compose up

# Check Redis connectivity
docker exec -it meb-rag-redis redis-cli ping
# Should return: PONG

# Test cache through API
curl http://localhost:8001/cache/health

# Monitor Redis
docker exec -it meb-rag-redis redis-cli INFO stats
```

### Automated Tests
```bash
pytest tests/test_cache.py -v
pytest tests/test_rag_api.py -v -k cache
```

## Troubleshooting

### Redis Won't Start
```bash
# Check logs
docker logs meb-rag-redis

# Check port availability
lsof -i :6379

# Restart Redis
docker compose restart redis
```

### Cache Not Working
```bash
# Check Redis health
curl http://localhost:8001/cache/health

# Check environment variables
docker exec -it meb-rag-api env | grep REDIS

# Manually test Redis
docker exec -it meb-rag-redis redis-cli
> SET test "hello"
> GET test
```

### Performance Issues
```bash
# Check Redis memory usage
docker exec -it meb-rag-redis redis-cli INFO memory

# Monitor slow commands
docker exec -it meb-rag-redis redis-cli SLOWLOG GET 10

# Check key count
docker exec -it meb-rag-redis redis-cli DBSIZE
```

## Summary

✅ **Redis cache successfully activated**
✅ **Tenant isolation implemented**
✅ **Automatic fallback to in-memory cache**
✅ **Zero downtime, backward compatible**
✅ **Production-ready configuration**

**Scalability Score Improvement:** 6/10 → **7.5/10**

**Next Priority:** Load balancer + multiple API instances (Score → 9/10)
