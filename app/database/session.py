"""Database engine and session management for SQLAlchemy 2.x.

Features:
- Lazy database connectivity (no eager PostgreSQL connections at import time).
- Singleton SQLAlchemy engine reuse across application requests.
- Conventional SessionLocal sessionmaker.
- Explicit configuration validation: missing DATABASE_URL raises DatabaseConfigurationError.
- FastAPI generator dependency (get_db) with guaranteed session cleanup.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(ValueError):
    """Raised when required database configuration is missing or invalid."""

    pass


# Global singleton engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class _SessionLocalFactory(sessionmaker):
    """Conventional sessionmaker with lazy engine binding."""

    def __call__(self, **local_kw) -> Session:
        if self.kw.get("bind") is None:
            self.configure(bind=get_engine())
        return super().__call__(**local_kw)


SessionLocal = _SessionLocalFactory(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL URL scheme for SQLAlchemy 2.x."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _resolve_database_url() -> str:
    """Resolve DATABASE_URL from Settings or environment.

    Raises:
        DatabaseConfigurationError: If DATABASE_URL is not configured.
    """
    url: str | None = None
    try:
        from app.core.config import get_settings

        url = get_settings().DATABASE_URL
    except Exception:
        url = os.getenv("DATABASE_URL")

    if not url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured. Set the DATABASE_URL environment variable."
        )
    return url


def get_engine(database_url: str | None = None, **kwargs) -> Engine:
    """Get or create the SQLAlchemy 2.x Engine.

    When called with database_url=None, returns the shared global engine instance,
    creating it on first use.
    When an explicit database_url is supplied, creates and returns an engine for that URL.

    Raises:
        DatabaseConfigurationError: If database_url is not supplied and cannot be resolved.
    """
    global _engine
    if database_url is not None:
        target_url = _normalize_database_url(database_url)
        return create_engine(target_url, **kwargs)

    if _engine is None:
        target_url = _normalize_database_url(_resolve_database_url())
        _engine = create_engine(target_url, **kwargs)
    return _engine


# Alias for create_db_engine
create_db_engine = get_engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Get or create the SQLAlchemy sessionmaker configured with the engine.

    Reuses the global session factory when using the default engine.
    If a specific engine is provided, returns a session factory bound to that engine.
    """
    global _session_factory
    if engine is not None:
        return sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    if _session_factory is None:
        _session_factory = SessionLocal
        if _session_factory.kw.get("bind") is None:
            _session_factory.configure(bind=get_engine())

    return _session_factory


# Alias for create_session_factory
create_session_factory = get_session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated database session per request.

    Guarantees session closure in a finally block after the request finishes.
    Supports FastAPI dependency overrides during testing.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def reset_db_state() -> None:
    """Reset cached engine and session factory state (primarily for test cleanup)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    if SessionLocal.kw.get("bind") is not None:
        SessionLocal.configure(bind=None)
