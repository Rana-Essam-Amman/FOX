"""Real Redis integration tests for fenced RedisState mutations."""

import pytest
import redis

from app.services.state import RedisState, current_generation
from app.services.fencing import acquire_generation


@pytest.fixture
def redis_state():
    client = redis.Redis(host="localhost", port=6379, db=14, decode_responses=False)
    client.flushdb()
    state = RedisState(host="localhost", port=6379, db=14)
    # Force the internal client to the test DB
    state._redis = client
    yield state, client
    client.flushdb()


def test_stale_generation_cannot_update_task(redis_state):
    state, client = redis_state
    task_id = "fence-update"
    client.hset(task_id, mapping={"task_id": task_id, "state": "1", "progress": "0"})
    gen1 = acquire_generation(client, task_id)
    gen2 = acquire_generation(client, task_id)

    # Bind stale generation
    token = current_generation.set(gen1)
    try:
        result = state.update_task(task_id, state=2, progress=40)
        assert result is False
    finally:
        current_generation.reset(token)

    # Stored state unchanged
    stored = client.hgetall(task_id)
    assert stored[b"state"] == b"1"
    assert stored[b"generation"] == str(gen2).encode()

    # Newer generation succeeds
    token = current_generation.set(gen2)
    try:
        result = state.update_task(task_id, state=2, progress=40)
        assert result is True
    finally:
        current_generation.reset(token)
    stored = client.hgetall(task_id)
    assert stored[b"state"] == b"2"
    assert stored[b"progress"] == b"40"


def test_stale_generation_cannot_patch_or_delete(redis_state):
    state, client = redis_state
    task_id = "fence-patch"
    client.hset(task_id, mapping={"task_id": task_id, "state": "1"})
    gen1 = acquire_generation(client, task_id)
    gen2 = acquire_generation(client, task_id)

    token = current_generation.set(gen1)
    try:
        assert state.patch_task(task_id, progress=99) is False
        assert state.delete_task(task_id) is False
    finally:
        current_generation.reset(token)

    assert client.exists(task_id)
    stored = client.hgetall(task_id)
    assert b"progress" not in stored or stored.get(b"progress") != b"99"

    token = current_generation.set(gen2)
    try:
        assert state.patch_task(task_id, progress=50) is True
        assert state.delete_task(task_id) is True
    finally:
        current_generation.reset(token)
    assert not client.exists(task_id)


def test_explicit_generation_overrides_context(redis_state):
    state, client = redis_state
    task_id = "explicit"
    client.hset(task_id, mapping={"task_id": task_id})
    gen = acquire_generation(client, task_id)
    # Context has wrong value, but explicit arg is used
    token = current_generation.set(999)
    try:
        result = state.update_task(task_id, state=3, progress=10, generation=gen)
        assert result is True
    finally:
        current_generation.reset(token)
