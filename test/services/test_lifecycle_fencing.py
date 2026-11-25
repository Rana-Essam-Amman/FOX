"""Lifecycle and race tests: stale workers cannot publish terminal state."""

import pytest
import redis

from app.services.state import RedisState, current_generation
from app.services.fencing import acquire_generation
from app.models import const


@pytest.fixture
def redis_state():
    client = redis.Redis(host="localhost", port=6379, db=12, decode_responses=False)
    client.flushdb()
    state = RedisState(host="localhost", port=6379, db=12)
    state._redis = client
    yield state, client
    client.flushdb()


def test_stale_worker_cannot_publish_complete_or_failed(redis_state):
    state, client = redis_state
    task_id = "lifecycle"
    client.hset(task_id, mapping={"task_id": task_id, "state": "1", "progress": "50"})
    gen_old = acquire_generation(client, task_id)
    gen_new = acquire_generation(client, task_id)

    # Stale tries to mark complete
    token = current_generation.set(gen_old)
    try:
        assert state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100) is False
        assert state.update_task(task_id, state=const.TASK_STATE_FAILED, progress=50, error="stale") is False
        assert state.patch_task(task_id, videos=["/out/stale.mp4"]) is False
    finally:
        current_generation.reset(token)

    stored = client.hgetall(task_id)
    assert stored[b"state"] == b"1"
    assert b"videos" not in stored

    # Newer worker can publish
    token = current_generation.set(gen_new)
    try:
        assert state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100, videos=["/out/good.mp4"]) is True
    finally:
        current_generation.reset(token)
    stored = client.hgetall(task_id)
    assert stored[b"state"] == str(const.TASK_STATE_COMPLETE).encode()
    assert b"videos" in stored


def test_newer_generation_supersedes_and_owns_terminal_state(redis_state):
    state, client = redis_state
    task_id = "supersede"
    client.hset(task_id, mapping={"task_id": task_id, "state": "1"})
    g1 = acquire_generation(client, task_id)
    g2 = acquire_generation(client, task_id)
    # g1 cannot finish
    token = current_generation.set(g1)
    try:
        assert state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100) is False
    finally:
        current_generation.reset(token)
    # g2 finishes
    token = current_generation.set(g2)
    try:
        assert state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100) is True
    finally:
        current_generation.reset(token)
    assert client.hget(task_id, "generation") == str(g2).encode()
    assert client.hget(task_id, "state") == str(const.TASK_STATE_COMPLETE).encode()
