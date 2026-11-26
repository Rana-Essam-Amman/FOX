"""Phase 1 security tests: ownership policy, reserved namespace, recovery fencing."""

import pytest
import redis

import importlib.util
ns = importlib.util.spec_from_file_location('ns', 'app/security/owner_namespaces.py')
m = importlib.util.module_from_spec(ns); ns.loader.exec_module(m)
user_owner_id, OwnerNamespaceError, POLICY_USER = m.user_owner_id, m.OwnerNamespaceError, m.POLICY_USER
te = importlib.util.spec_from_file_location('te', 'app/security/task_execution.py')
te_m = importlib.util.module_from_spec(te); te.loader.exec_module(te_m)
authorize_task_execution, ExecutionDenied = te_m.authorize_task_execution, te_m.ExecutionDenied
from app.services.fencing import acquire_generation
from app.services.state import RedisState


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
