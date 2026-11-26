"""Recovery fencing tests. Real Redis."""

import pytest
import redis

from app.services.fencing import acquire_generation
from app.services.state import RedisState


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=4, decode_responses=False)
    created = []
    yield client, created
    for key in created:
        client.delete(key)


def test_recovery_no_generation_marks_failed(redis_client):
    """Never-started task (no generation) can be marked FAILED by recovery."""
    client, created = redis_client
    task_id = "test-rec-none"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    state.create_task(task_id, state=4)  # PROCESSING
    assert state.recovery_patch(task_id, state=-1, error="malformed") is True
    stored = state.get_task(task_id)
    assert stored.get("state") == -1


def test_recovery_with_generation_rejects_without_expected(redis_client):
    """Task with a generation is not mutated by recovery without expected_generation."""
    client, created = redis_client
    task_id = "test-rec-has-gen"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    state.create_task(task_id, state=4)
    acquire_generation(client, task_id)
    assert state.recovery_patch(task_id, state=-1, error="stale") is False
    stored = state.get_task(task_id)
    assert stored.get("state") == 4  # unchanged


def test_recovery_wrong_generation_rejected(redis_client):
    """Wrong expected_generation is rejected."""
    client, created = redis_client
    task_id = "test-rec-wrong"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    state.create_task(task_id)
    g = acquire_generation(client, task_id)
    assert state.recovery_patch(task_id, expected_generation=g + 5, state=-1) is False


def test_recovery_correct_generation_succeeds(redis_client):
    """Correct expected_generation succeeds."""
    client, created = redis_client
    task_id = "test-rec-correct"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    state.create_task(task_id, state=4)
    g = acquire_generation(client, task_id)
    assert state.recovery_patch(task_id, expected_generation=g, state=-1, error="real") is True
    stored = state.get_task(task_id)
    assert stored.get("state") == -1


def test_recovery_deleted_task_returns_false(redis_client):
    """Deleted task cannot be recovered."""
    client, created = redis_client
    task_id = "test-rec-deleted"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    # Never created
    assert state.recovery_patch(task_id, state=-1) is False

def test_recovery_atomic_rejects_if_generation_acquired(redis_client):
    """Atomic script rejects no-gen recovery if generation exists at script time."""
    client, created = redis_client
    task_id = "test-rec-atomic"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=4)
    state._redis = client
    state.create_task(task_id, state=4)
    # Acquire generation first
    acquire_generation(client, task_id)
    # No-gen recovery must fail atomically
    assert state.recovery_patch(task_id, state=-1, error="stale") is False
    stored = state.get_task(task_id)
    assert stored.get("state") == 4
    assert stored.get("generation") is not None
