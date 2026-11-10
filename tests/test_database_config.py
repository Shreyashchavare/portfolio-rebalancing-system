"""Tests for database configuration and session management.

Tests cover:
1. Environment configuration loading and explicit validation errors when missing.
2. SQLAlchemy engine creation, reuse, and connection pool preservation.
3. Session factory creation, reuse, and engine binding.
4. Conventional SessionLocal sessionmaker.
5. FastAPI get_db dependency lifecycle (yielding, closing, overriding).
6. Application import isolation (no PostgreSQL connection on import).
"""

import importlib
from typing import Generator
from unittest.mock import MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, clear_settings_cache, get_settings
from app.database.session import (
    DatabaseConfigurationError,
    SessionLocal,
    create_db_engine,
    create_session_factory,
    get_db,
    get_engine,
    get_session_factory,
    reset_db_state,
)


@pytest.fixture(autouse=True)
def clean_db_and_settings_state():
    """Ensure settings cache and database singleton states are reset before and after each test."""
    clear_settings_cache()
    reset_db_state()
    yield
    clear_settings_cache()
    reset_db_state()


# ==============================================================================
# Configuration Tests
# ==============================================================================


def test_database_url_loaded_from_env(monkeypatch):
    """Verify DATABASE_URL is loaded from environment configuration."""
    test_url = "postgresql://test_user:test_pass@localhost:5432/portfolio_test_db"
    monkeypatch.setenv("DATABASE_URL", test_url)
    clear_settings_cache()

    settings = Settings()
    assert str(settings.DATABASE_URL) == test_url
    assert str(settings.database_url) == test_url

    # Verify cached get_settings() also returns the configured URL
    cached_settings = get_settings()
    assert str(cached_settings.DATABASE_URL) == test_url


def test_missing_database_url_handled_clearly(monkeypatch):
    """Verify that missing required database configuration raises a clear validation error."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("database_url", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_SERVER", raising=False)
    clear_settings_cache()

    with pytest.raises(ValidationError):
        # Settings must strictly require DATABASE_URL
        Settings(_env_file=None)


def test_missing_database_url_raises_configuration_error_in_session(monkeypatch):
    """Verify that attempting to create an engine without DATABASE_URL raises a clear error.

    Ensures there is NO silent fallback to SQLite in-memory when configuration is omitted.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("database_url", raising=False)
    clear_settings_cache()
    reset_db_state()

    with pytest.raises((DatabaseConfigurationError, ValueError)):
        get_engine()


def test_no_database_connection_attempted_on_app_import(monkeypatch):
    """Verify that importing the application attempts no real database connection."""
    # Point DATABASE_URL to an unreachable address
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://invalid_user:invalid_pass@127.0.0.1:59999/nonexistent_db",
    )
    clear_settings_cache()
    reset_db_state()

    import app.main

    reloaded_main = importlib.reload(app.main)
    assert hasattr(reloaded_main, "app")

    import app.database.session as db_session

    importlib.reload(db_session)

    # Health check endpoint must remain accessible without requiring DB connectivity
    client = TestClient(reloaded_main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ==============================================================================
# Engine and Session Factory Tests
# ==============================================================================


def test_engine_creation_with_supplied_url():
    """Verify an engine can be created using an explicitly supplied database URL."""
    test_url = "sqlite:///:memory:"
    engine = get_engine(test_url)
    try:
        assert isinstance(engine, Engine)
        assert engine.url.drivername == "sqlite"

        # Verify query execution on explicit SQLite in-memory engine
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1
    finally:
        engine.dispose()


def test_engine_reused_across_calls(monkeypatch):
    """Verify the default SQLAlchemy engine is reused rather than recreated on every request."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    clear_settings_cache()
    reset_db_state()

    engine_first = get_engine()
    engine_second = get_engine()

    assert engine_first is engine_second, (
        "get_engine() must reuse the singleton engine instance across calls"
    )
    assert engine_first.pool is engine_second.pool, (
        "Reused engine must preserve the connection pool"
    )


def test_session_factory_configured_and_reused_with_engine(monkeypatch):
    """Verify that the session factory is reused and bound to the expected engine."""
    # 1. Custom engine binding
    custom_engine = create_engine("sqlite:///:memory:")
    try:
        custom_factory = get_session_factory(custom_engine)
        assert isinstance(custom_factory, sessionmaker)
        assert custom_factory.kw.get("bind") is custom_engine

        session = custom_factory()
        try:
            assert isinstance(session, Session)
            assert session.get_bind() is custom_engine
        finally:
            session.close()
    finally:
        custom_engine.dispose()

    # 2. Default engine reuse
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    clear_settings_cache()
    reset_db_state()

    default_factory_first = get_session_factory()
    default_factory_second = get_session_factory()
    assert default_factory_first is default_factory_second, (
        "get_session_factory() must reuse the global session factory instance"
    )
    assert default_factory_first.kw.get("bind") is get_engine()


def test_sessionlocal_is_conventional_sessionmaker(monkeypatch):
    """Verify SessionLocal behaves as a conventional sessionmaker bound to the engine."""
    assert isinstance(SessionLocal, sessionmaker)

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    clear_settings_cache()
    reset_db_state()

    session = SessionLocal()
    try:
        assert isinstance(session, Session)
        assert session.is_active is True
        assert session.get_bind() is get_engine()
    finally:
        session.close()


def test_session_create_and_close():
    """Verify that sessions can be created and closed cleanly."""
    engine = create_engine("sqlite:///:memory:")
    try:
        factory = get_session_factory(engine)
        session = factory()
        assert isinstance(session, Session)
        assert session.is_active is True

        # Close session and confirm resource handling
        session.close()
    finally:
        engine.dispose()


# ==============================================================================
# FastAPI Dependency Tests
# ==============================================================================


def test_database_session_dependency_yields_session(monkeypatch):
    """Verify that the FastAPI database session dependency yields an active Session."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    clear_settings_cache()
    reset_db_state()

    gen = get_db()
    try:
        session = next(gen)
        assert isinstance(session, Session)
        assert session.is_active is True
    finally:
        try:
            gen.close()
        except Exception:
            pass


def test_database_session_closed_after_dependency_use(monkeypatch):
    """Verify that the database session is closed after dependency use."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    clear_settings_cache()
    reset_db_state()

    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)

    closed = False
    original_close = session.close

    def tracking_close():
        nonlocal closed
        closed = True
        return original_close()

    session.close = tracking_close

    # Exhaust generator to simulate request termination
    with pytest.raises(StopIteration):
        next(gen)

    assert closed is True, "get_db generator must close the session upon completion"


def test_database_session_dependency_can_be_overridden():
    """Verify that the get_db dependency can be overridden in FastAPI during tests."""
    test_app = FastAPI()

    @test_app.get("/test-db-override")
    def sample_endpoint(db: Session = Depends(get_db)):
        return {"session_repr": str(db)}

    mock_marker = "overridden_test_session"

    def mock_get_db():
        yield mock_marker

    test_app.dependency_overrides[get_db] = mock_get_db
    client = TestClient(test_app)

    try:
        response = client.get("/test-db-override")
        assert response.status_code == 200
        assert response.json() == {"session_repr": mock_marker}
    finally:
        test_app.dependency_overrides.clear()
