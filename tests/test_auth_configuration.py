"""Tests for authentication configuration, safety boundaries, and mock authorization precedence."""

import pytest

from app.api.dependencies import (
    DevMockAuthenticationVerifier,
    ProductionAuthenticationVerifier,
    get_auth_settings,
    get_auth_verifier,
)
from app.core.config import clear_settings_cache


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch):
    """Ensure settings cache and auth-related environment variables are reset before each test."""
    clear_settings_cache()
    # Clear any active auth overrides
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("AUTH_PROVIDER", raising=False)
    monkeypatch.delenv("ENABLE_DEV_MOCK_AUTH", raising=False)
    yield
    clear_settings_cache()


def test_default_auth_configuration(monkeypatch):
    """Default configuration must fail closed with ProductionAuthenticationVerifier."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_PROVIDER", "production")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "false")

    verifier = get_auth_verifier()
    assert isinstance(verifier, ProductionAuthenticationVerifier)
    assert verifier.verify_token("any-token") is None


def test_explicit_development_mock_enablement(monkeypatch):
    """Explicit mock auth opt-in in development returns DevMockAuthenticationVerifier."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

    verifier = get_auth_verifier()
    assert isinstance(verifier, DevMockAuthenticationVerifier)
    # Recognized mock tokens must verify successfully
    principal = verifier.verify_token("dev-reviewer-token")
    assert principal is not None
    assert principal.reviewer_id == "REV-DEV-01"
    assert principal.role == "REVIEWER"


def test_disabled_mock_auth_in_development(monkeypatch):
    """When ENABLE_DEV_MOCK_AUTH is false in development, verifier fails closed."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_PROVIDER", "production")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "false")

    verifier = get_auth_verifier()
    assert isinstance(verifier, ProductionAuthenticationVerifier)
    assert verifier.verify_token("dev-reviewer-token") is None


def test_contradictory_settings_rejected(monkeypatch):
    """AUTH_PROVIDER=mock with ENABLE_DEV_MOCK_AUTH=False must be rejected clearly with ValueError."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "false")

    with pytest.raises(ValueError, match="Contradictory authentication configuration"):
        get_auth_verifier()


def test_production_rejects_mock_auth_via_enable_flag(monkeypatch):
    """APP_ENV=production must hard-reject ENABLE_DEV_MOCK_AUTH=True with RuntimeError."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "true")

    with pytest.raises(RuntimeError, match="cannot be activated in a production environment"):
        get_auth_verifier()


def test_production_rejects_mock_auth_via_provider(monkeypatch):
    """APP_ENV=production must hard-reject AUTH_PROVIDER=mock with RuntimeError."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PROVIDER", "mock")

    with pytest.raises(RuntimeError, match="cannot be activated in a production environment"):
        get_auth_verifier()


def test_production_default_fails_closed(monkeypatch):
    """APP_ENV=production with default settings returns ProductionAuthenticationVerifier."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_PROVIDER", "production")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "false")

    verifier = get_auth_verifier()
    assert isinstance(verifier, ProductionAuthenticationVerifier)
    assert verifier.verify_token("any-token") is None


def test_get_auth_settings_respects_settings_model(monkeypatch):
    """Verify get_auth_settings resolves unified settings correctly."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("AUTH_PROVIDER", "production")
    monkeypatch.setenv("ENABLE_DEV_MOCK_AUTH", "false")

    app_env, provider, mock_enabled = get_auth_settings()
    assert app_env == "staging"
    assert provider == "production"
    assert mock_enabled is False
