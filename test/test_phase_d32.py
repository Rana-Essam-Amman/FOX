"""Phase D3.2 forensic runtime integration tests."""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.security.runtime import create_ownership_store, create_rate_limiter, create_storage
from app.security.ownership import InMemoryOwnershipStore
from app.security.config_validation import ProductionConfigError


def test_production_selects_postgres_and_supabase(monkeypatch):
    pytest.importorskip("psycopg2")
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.setenv("FOX_OIDC_ISSUER", "https://example.supabase.co/auth/v1")
    monkeypatch.setenv("FOX_OIDC_AUDIENCE", "authenticated")
    monkeypatch.setenv("FOX_OIDC_JWKS_URL", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fox:fox@127.0.0.1:5432/fox_test")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    store = create_ownership_store()
    limiter = create_rate_limiter()
    storage = create_storage()
    assert type(store).__name__ == "PostgresOwnershipStore"
    assert type(limiter).__name__ == "PostgresRateLimiter"
    assert type(storage).__name__ == "SupabaseStorageAdapter"


def test_development_selects_in_memory(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "development")
    store = create_ownership_store()
    limiter = create_rate_limiter()
    assert isinstance(store, InMemoryOwnershipStore)
    assert type(limiter).__name__ == "InMemoryRateLimiter"


def test_production_missing_config_fails(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ProductionConfigError):
        create_ownership_store()
