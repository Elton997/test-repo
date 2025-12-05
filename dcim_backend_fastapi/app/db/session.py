"""
Database session management with lazy initialization.
The engine and session factory are created on first use, not at import time.
This significantly speeds up FastAPI startup.
"""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Global variables for lazy initialization
_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    """Get database URL from environment (called lazily)."""
    url = os.getenv("DB_URL")
    if not url:
        raise ValueError("DB_URL not set in environment variables!")
    return url


def get_engine():
    """
    Lazy engine creation - database connection only happens on first query,
    not during FastAPI startup.
    """
    global _engine
    if _engine is None:
        database_url = _get_database_url()
        is_dev = os.getenv("APP_ENV", "dev").lower() == "dev"
        
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            echo=False,  # Disable SQL logging for performance (set to True to debug)
        )
    return _engine


def get_session_factory():
    """Lazy session factory creation."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


# Backward-compatible SessionLocal class
class SessionLocal:
    """
    Drop-in replacement for sessionmaker() that supports lazy initialization.
    Usage: session = SessionLocal() works as before.
    """
    def __new__(cls) -> Session:
        factory = get_session_factory()
        return factory()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Use: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
