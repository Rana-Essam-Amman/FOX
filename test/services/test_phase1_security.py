"""Phase 1 security tests: ownership policy, reserved namespace, recovery fencing."""

from app.services.fencing import acquire_generation
from app.services.state import RedisState

import pytest
import redis

import importlib.util
import sys

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

ns = _load('app.security.owner_namespaces', 'app/security/owner_namespaces.py')
user_owner_id, OwnerNamespaceError, POLICY_USER = ns.user_owner_id, ns.OwnerNamespaceError, ns.POLICY_USER
te = _load('app.security.task_execution', 'app/security/task_execution.py')
authorize_task_execution, ExecutionDenied = te.authorize_task_execution, te.ExecutionDenied


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=5, decode_responses=False)
    created = []
    yield client, created
    for key in created:
        client.delete(key)


def test_user_owner_rejects_internal_prefix():
    with pytest.raises(OwnerNamespaceError):
        user_owner_id("internal:attacker")
    with pytest.raises(OwnerNamespaceError):
        user_owner_id("")
    assert user_owner_id("user-123") == "user-123"


def test_authorize_requires_policy():
    class Rec:
        task_id = "t1"
        owner_id = "user-1"
        kind = "video"
        metadata = {"request_id": "r1"}  # missing policy
    with pytest.raises(ExecutionDenied):
        authorize_task_execution("t1", expected_kind="video", lookup=lambda t: Rec())


def test_authorize_accepts_user_policy():
    class Rec:
        task_id = "t1"
        owner_id = "user-1"
        kind = "video"
        metadata = {"policy": POLICY_USER}
    grant = authorize_task_execution("t1", expected_kind="video", lookup=lambda t: Rec())
    assert grant.owner_id == "user-1"
    assert grant.policy == POLICY_USER


def test_recovery_rejects_invalid_or_zero_generation(redis_client):
    client, created = redis_client
    state = RedisState(host="localhost", port=6379, db=5)
    state._redis = client

    never_started = "test-recovery-invalid-explicit-generation"
    created.append(never_started)
    state.create_task(never_started)
    for invalid in (0, -1, False, True):
        assert state.recovery_patch(
            never_started, expected_generation=invalid, state=-1
        ) is False
    assert state.get_task(never_started)["state"] != -1

    malformed = "test-recovery-stored-zero-generation"
    created.append(malformed)
    state.create_task(malformed, generation=0)
    assert state.recovery_patch(
        malformed, expected_generation=None, state=-1
    ) is False
    assert state.get_task(malformed)["state"] != -1


def test_recovery_requires_generation(redis_client):
    client, created = redis_client
    task_id = "test-recovery"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=5)
    state._redis = client
    state.create_task(task_id)
    # No generation: fail closed
    assert state.recovery_patch(task_id, state=-1, error="stale") is False
    # With wrong generation: fail closed
    g = acquire_generation(client, task_id)
    assert state.recovery_patch(task_id, expected_generation=g + 99, state=-1) is False
    # With correct generation: succeeds
    assert state.recovery_patch(task_id, expected_generation=g, state=-1, error="real") is True
    stored = state.get_task(task_id)
    assert stored.get("state") == -1
