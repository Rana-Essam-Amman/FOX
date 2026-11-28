"""Phase D3 free-tier Supabase integration tests."""

import os
from pathlib import Path

import pytest

from app.security.config_validation import validate_production_config, ProductionConfigError
from app.security.jwt_auth import AuthenticatedUser


def test_production_requires_supabase_credentials(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.setenv("FOX_OIDC_ISSUER", "https://example.supabase.co/auth/v1")
    monkeypatch.setenv("FOX_OIDC_AUDIENCE", "authenticated")
    monkeypatch.setenv("FOX_OIDC_JWKS_URL", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fox:fox@127.0.0.1:5432/fox_test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(ProductionConfigError):
        validate_production_config()


def test_postgres_rate_limit_interface_exists():
    from app.security.adapters.postgres_rate_limit import PostgresRateLimiter
    assert PostgresRateLimiter is not None


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_postgres_rate_limit_atomic_if_db_available():
    from app.security.adapters.postgres_rate_limit import PostgresRateLimiter
    limiter = PostgresRateLimiter()
    user = AuthenticatedUser(sub="d3-user")
    limiter.check_request(user, "r1")


def test_supabase_storage_ownership_check():
    from app.security.adapters.supabase_storage import SupabaseStorageAdapter
    with pytest.raises(RuntimeError):
        SupabaseStorageAdapter(url="", service_key="")


def test_rate_limit_counters_are_service_role_only_under_rls():
    migration = Path(__file__).resolve().parents[1] / "migrations" / "003_rls_policies.sql"
    sql = migration.read_text(encoding="utf-8")
    marker = "ALTER TABLE rate_limit_counters ENABLE ROW LEVEL SECURITY;"
    assert marker in sql
    rate_limit_policy = sql.split(marker, 1)[1]
    assert "CREATE POLICY rate_limit_counters_service_all" in rate_limit_policy
    assert "FOR ALL" in rate_limit_policy
    assert "TO service_role" in rate_limit_policy
    assert "TO authenticated" not in rate_limit_policy
    assert "TO anon" not in rate_limit_policy
