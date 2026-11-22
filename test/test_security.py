"""Security isolation and authentication tests for the Phase D gateway."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest

from app.security.jwt_auth import JWTVerifier, AuthenticatedUser
from app.security.ownership import InMemoryOwnershipStore, TaskOwnershipRecord, require_task_owner
from app.security.rate_limit import InMemoryRateLimiter


@pytest.fixture(autouse=True)
def isolated_stores():
    # Tests construct their own stores; global is not required.
    yield


def _make_token(sub: str, issuer: str = "https://idp.test", audience: str = "fox-api", exp_delta: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "exp": int((now + timedelta(seconds=exp_delta)).timestamp()),
        "iat": int(now.timestamp()),
    }
    # Use a static test key. Production uses JWKS.
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_missing_auth_rejected():
    # Full app wiring is exercised in CI; this unit confirms the dependency rejects bare requests.
    from app.security.jwt_auth import require_authenticated_user
    class FakeRequest:
        headers = {}
    with pytest.raises(Exception):
        require_authenticated_user(FakeRequest())


def test_invalid_token_rejected():
    from app.security.jwt_auth import require_authenticated_user
    class FakeRequest:
        headers = {"authorization": "Bearer not-a-jwt"}
    with pytest.raises(Exception):
        require_authenticated_user(FakeRequest())


def test_cross_user_isolation():
    store = InMemoryOwnershipStore()
    store.create(
        TaskOwnershipRecord(
            task_id="task-owned-by-a",
            owner_id="user-a",
            created_at=datetime.now(timezone.utc),
            kind="video",
            metadata={},
        )
    )
    user_b = AuthenticatedUser(sub="user-b")
    # Patch the module-level store used by require_task_owner for this test.
    with patch("app.security.ownership.ownership_store", store):
        with pytest.raises(Exception) as exc:
            require_task_owner("task-owned-by-a", user_b)
        assert "not found" in str(exc.value).lower() or getattr(exc.value, "status_code", None) == 404


def test_unconfigured_auth_fails_closed():
    verifier = JWTVerifier(issuer=None, audience=None, jwks_url=None)
    assert not verifier.is_configured()
    with pytest.raises(Exception):
        verifier.verify("any", "req-1")


def test_rate_limit_enforced():
    limiter = InMemoryRateLimiter()
    user = AuthenticatedUser(sub="rate-user")
    for _ in range(60):
        limiter.check_request(user, "r1")
    with pytest.raises(Exception):
        limiter.check_request(user, "r2")
