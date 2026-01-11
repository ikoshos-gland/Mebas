"""
MEB RAG Sistemi - FastAPI Application
Main application with CORS, rate limiting, and routes
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import time

from api.models import HealthResponse, ErrorResponse
from api.routes.analysis import router as analysis_router
from api.routes.feedback import router as feedback_router
from api.routes.content import router as content_router
from api.routes.cache import router as cache_router
from api.routes.auth import router as auth_router
from api.routes.users import router as users_router
from api.routes.conversations import router as conversations_router
from api.routes.progress import router as progress_router
from config.settings import get_settings
from config.logging import configure_logging
import logging

# Initialize logger
logger = logging.getLogger("api.main")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    configure_logging()
    logger.info("🚀 MEB RAG API başlatılıyor...", extra={"extra_data": {"event": "startup"}})
    
    settings = get_settings()
    
    # Initialize database
    try:
        from src.database.db import init_db
        init_db()
        logger.info("✅ Veritabanı hazır")
    except Exception as e:
        logger.error(f"⚠️ Veritabanı hatası: {e}", exc_info=True)
    
    # Initialize graph
    try:
        from api.routes.analysis import get_graph
        get_graph()
        logger.info("✅ RAG Graph hazır")
    except Exception as e:
        logger.error(f"⚠️ Graph hatası: {e}", exc_info=True)
    
    yield
    
    # Shutdown
    logger.info("👋 MEB RAG API kapatılıyor...")


# Create app
app = FastAPI(
    title="MEB RAG API",
    description="""
    MEB Müfredat Kazanım Analiz Sistemi
    
    Öğrenci sorularını analiz ederek MEB kazanımlarıyla eşleştirir.
    
    ## Özellikler
    - 📷 Görsel soru analizi (GPT-4o Vision)
    - 📝 Metin soru analizi
    - 🎯 Kazanım eşleştirme
    - 📚 Ders kitabı referansları
    - 🔄 Gerçek zamanlı streaming
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================== MIDDLEWARE ==================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header and LOGGING"""
    start_time = time.time()
    
    # Log Request
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log Response
        logger.info(
            f"Request Completed",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": round(process_time, 4)
                }
            }
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request Failed",
            exc_info=True,
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": round(process_time, 4),
                    "error": str(e)
                }
            }
        )
        raise e


# ================== ERROR HANDLERS ==================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    settings = get_settings()
    
    logger.error("Global Exception Handler caught error", exc_info=True)
    
    error_detail = str(exc) if settings.debug else "Bir hata oluştu"
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=error_detail,
            status_code=500
        ).model_dump()
    )


# ================== ROUTES ==================

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversations_router)
app.include_router(progress_router)
app.include_router(analysis_router)
app.include_router(feedback_router)
app.include_router(content_router)
app.include_router(cache_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "MEB RAG API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """
    Enhanced health check endpoint.

    Returns detailed system health status including:
    - Database connectivity
    - Azure OpenAI availability (actual API call)
    - Azure Search availability (actual search call)
    - Circuit breaker states
    - Response times
    """
    import time
    import asyncio

    settings = get_settings()

    services = {}
    response_times = {}

    # 1. Check Database
    start = time.time()
    try:
        from src.database.db import get_session
        from sqlalchemy import text
        db = get_session()
        db.execute(text("SELECT 1"))
        db.close()
        services["database"] = "healthy"
        response_times["database_ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)[:50]}"
        response_times["database_ms"] = -1

    # 2. Check Azure OpenAI (actual lightweight call)
    start = time.time()
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        try:
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )

            # Minimal call - just list deployments with timeout
            await asyncio.wait_for(
                client.models.list(),
                timeout=5.0
            )
            services["azure_openai"] = "healthy"
            response_times["azure_openai_ms"] = int((time.time() - start) * 1000)
        except asyncio.TimeoutError:
            services["azure_openai"] = "timeout"
            response_times["azure_openai_ms"] = 5000
        except Exception as e:
            services["azure_openai"] = f"unhealthy: {str(e)[:50]}"
            response_times["azure_openai_ms"] = -1
    else:
        services["azure_openai"] = "not_configured"
        response_times["azure_openai_ms"] = -1

    # 3. Check Azure Search (actual search call)
    start = time.time()
    if settings.azure_search_endpoint and settings.azure_search_api_key:
        try:
            from config.azure_config import get_search_client

            client = get_search_client(settings.azure_search_index_kazanim)

            # Minimal search with timeout
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: list(client.search(search_text="test", top=1))
                ),
                timeout=5.0
            )
            services["azure_search"] = "healthy"
            response_times["azure_search_ms"] = int((time.time() - start) * 1000)
        except asyncio.TimeoutError:
            services["azure_search"] = "timeout"
            response_times["azure_search_ms"] = 5000
        except Exception as e:
            services["azure_search"] = f"unhealthy: {str(e)[:50]}"
            response_times["azure_search_ms"] = -1
    else:
        services["azure_search"] = "not_configured"
        response_times["azure_search_ms"] = -1

    # 4. Check Circuit Breaker States
    try:
        from src.utils.resilience import get_all_circuit_states
        circuit_states = get_all_circuit_states()
        services["circuit_breakers"] = {
            name: state["state"]
            for name, state in circuit_states.items()
        }
    except Exception:
        services["circuit_breakers"] = {}

    # Determine overall status
    core_services = ["database", "azure_openai", "azure_search"]
    all_healthy = all(
        services.get(svc, "").startswith("healthy") or services.get(svc, "") == "not_configured"
        for svc in core_services
    )

    # Check if any circuit breaker is open
    any_circuit_open = any(
        state == "open"
        for state in services.get("circuit_breakers", {}).values()
    )

    if any_circuit_open:
        status = "degraded"
    elif all_healthy:
        status = "healthy"
    else:
        status = "degraded"

    return HealthResponse(
        status=status,
        version="1.0.0",
        services=services
    )


# ================== RUN ==================

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
