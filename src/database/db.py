"""
MEB RAG Sistemi - Veritabanı Bağlantısı
Database Engine, Session Management, and Initialization
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from config.settings import get_settings
from src.database.models import Base


# Get settings
settings = get_settings()

# Create engine based on database URL
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Check connection health before use
    # SQLite specific settings
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Create all database tables.
    Call this once at application startup.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Veritabanı tabloları oluşturuldu!")


def drop_db() -> None:
    """
    Drop all database tables.
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️ Tüm tablolar silindi!")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI endpoints.
    
    Usage:
        @app.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """
    Get a new database session.
    Remember to close it when done!
    
    Usage:
        db = get_session()
        try:
            # ... use db
        finally:
            db.close()
    """
    return SessionLocal()
