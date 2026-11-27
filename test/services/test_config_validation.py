import pytest

from app.config import config
from app.security.config_validation import (
    ProductionConfigError,
    validate_production_config,
)


def _set_required_production_environment(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.setenv("FOX_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("FOX_OIDC_AUDIENCE", "fox-api")
    monkeypatch.setenv("FOX_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fox:secret@localhost/fox")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-only")


def test_production_refuses_process_local_task_state(monkeypatch):
    _set_required_production_environment(monkeypatch)
    monkeypatch.setitem(config.app, "enable_redis", False)

    with pytest.raises(ProductionConfigError, match="app.enable_redis=true"):
        validate_production_config()


def test_production_accepts_shared_redis_task_state(monkeypatch):
    _set_required_production_environment(monkeypatch)
    monkeypatch.setitem(config.app, "enable_redis", True)

    validate_production_config()


def test_nonproduction_does_not_require_redis(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "development")
    monkeypatch.setitem(config.app, "enable_redis", False)

    validate_production_config()
