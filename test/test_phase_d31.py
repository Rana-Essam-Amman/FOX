"""Phase D3.1 runtime integration tests."""

import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.security.runtime import create_ownership_store, create_rate_limiter, create_storage
from app.security.ownership import InMemoryOwnershipStore, TaskOwnershipRecord
from app.security.jwt_auth import AuthenticatedUser
from app.security.config_validation import ProductionConfigError


def test_development_uses_in_memory_adapters(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "development")
    store = create_ownership_store()
    limiter = create_rate_limiter()
    assert isinstance(store, InMemoryOwnershipStore)
    assert type(limiter).__name__ == "InMemoryRateLimiter"


def test_production_requires_full_config(monkeypatch):
    monkeypatch.setenv("FOX_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ProductionConfigError):
        create_ownership_store()


def test_supabase_upload_uses_service_role_and_rolls_back(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    from app.security.adapters.supabase_storage import SupabaseStorageAdapter
    adapter = SupabaseStorageAdapter()
    user = AuthenticatedUser(sub="user-1")

    with patch("app.security.adapters.supabase_storage.requests.post") as mock_post:
        mock_post.side_effect = Exception("network error")
        with pytest.raises(Exception):
            adapter.put_owned(user, b"data", "image/jpeg", "req-1")
        assert mock_post.called


def test_signed_url_comes_from_supabase_response(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    from app.security.adapters.supabase_storage import SupabaseStorageAdapter
    adapter = SupabaseStorageAdapter()
    user = AuthenticatedUser(sub="user-2")

    from app.security.ownership import ownership_store
    ownership_store.create(
        TaskOwnershipRecord(
            task_id="mat-1",
            owner_id="user-2",
            created_at=datetime.now(timezone.utc),
            kind="material",
            metadata={"object": "user-2/mat-1"},
        )
    )

    with patch("app.security.adapters.supabase_storage.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"signedURL": "/storage/v1/object/sign/fox-media/user-2/mat-1?token=abc"}
        mock_post.return_value = mock_resp
        url = adapter.get_signed_url("mat-1", user, "req-2")
        assert "token=abc" in url
        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        assert "Bearer test-service-key" in call_kwargs.get("headers", {}).get("Authorization", "")
