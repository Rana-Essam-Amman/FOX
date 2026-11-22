"""Phase D2 integration and configuration tests."""

import os
import pytest
from datetime import datetime, timezone
from app.security.config_validation import validate_production_config, ProductionConfigError
from app.security.ownership import InMemoryOwnershipStore, TaskOwnershipRecord
from app.security.jwt_auth import AuthenticatedUser


def test_production_startup_fails_without_required_config(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("FOX_OIDC_ISSUER", raising=False)
    with pytest.raises(ProductionConfigError):
        validate_production_config()


def test_development_does_not_require_infrastructure(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "development")
    validate_production_config()


def test_in_memory_ownership_is_isolated():
    store = InMemoryOwnershipStore()
    store.create(
        TaskOwnershipRecord(
            task_id="t1", owner_id="user-a",
            created_at=datetime.now(timezone.utc), kind="video", metadata={},
        )
    )
    assert store.get("t1").owner_id == "user-a"
    assert store.delete("t1", "user-b") is False
    assert store.delete("t1", "user-a") is True


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_postgres_ownership_roundtrip():
    from app.security.adapters.postgres_ownership import PostgresOwnershipStore
    store = PostgresOwnershipStore()
    rec = TaskOwnershipRecord(
        task_id="pg-test-1", owner_id="user-pg",
        created_at=datetime.now(timezone.utc), kind="video", metadata={"note": "integration"},
    )
    store.create(rec)
    assert store.get("pg-test-1").owner_id == "user-pg"
    store.delete("pg-test-1", "user-pg")


@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="REDIS_URL not set")
def test_redis_rate_limit_atomic():
    from app.security.adapters.redis_rate_limit import RedisRateLimiter
    limiter = RedisRateLimiter()
    user = AuthenticatedUser(sub="redis-user")
    limiter.check_request(user, "r1")
