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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
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
app.include_router(analysis_router)
app.include_router(feedback_router)
app.include_router(content_router)


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
    Health check endpoint.
    
    Returns system health status.
    """
    settings = get_settings()
    
    services = {
        "database": "unknown",
        "azure_openai": "unknown",
        "azure_search": "unknown"
    }
    
    # Check database
    try:
        from src.database.db import get_session
        db = get_session()
        db.execute("SELECT 1")
        db.close()
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"
    
    # Check Azure OpenAI (just config, not actual call)
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        services["azure_openai"] = "configured"
    else:
        services["azure_openai"] = "not_configured"
    
    # Check Azure Search
    if settings.azure_search_endpoint and settings.azure_search_api_key:
        services["azure_search"] = "configured"
    else:
        services["azure_search"] = "not_configured"
    
    return HealthResponse(
        status="healthy",
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
