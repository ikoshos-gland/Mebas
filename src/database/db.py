"""
MEB RAG Sistemi - Veritabanı Bağlantısı
Database Engine, Session Management, and Initialization
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Optional

from config.settings import get_settings
from src.database.models import Base


def _create_engine(database_url: str, debug: bool = False):
    """Create a SQLAlchemy engine with the given URL."""
    return create_engine(
        database_url,
        echo=debug,
        pool_pre_ping=True,  # Check connection health before use
        # SQLite specific settings
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )


# Get settings
settings = get_settings()

# Create engine based on database URL
engine = _create_engine(settings.database_url, settings.debug)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def reinitialize_engine(database_url: Optional[str] = None) -> None:
    """
    Reinitialize the database engine with a new URL.
    Useful for testing with different databases.

    Args:
        database_url: New database URL. If None, uses settings.
    """
    global engine, SessionLocal

    if database_url is None:
        # Clear settings cache and reload
        get_settings.cache_clear()
        new_settings = get_settings()
        database_url = new_settings.database_url
        debug = new_settings.debug
    else:
        debug = False

    engine = _create_engine(database_url, debug)
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
