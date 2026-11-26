"""Tests for terminal-state fencing. Production lease guard + real Redis state."""

import threading

import pytest
import redis

from app.services.lease_guard import lease_lost_event, check_lease_or_abort
from app.services.fencing import acquire_generation
from app.services.state import RedisState, current_generation
from app.models import const


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=7, decode_responses=False)
    created = []
    yield client, created
    for key in created:
        client.delete(key)


def test_lease_loss_blocks_complete(redis_client):
    """Lease loss prevents marking COMPLETE."""
    client, created = redis_client
    task_id = "test-term-complete"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=7)
    state._redis = client
    state.create_task(task_id, state=1, progress=50)
    g1 = acquire_generation(client, task_id)
    _g2 = acquire_generation(client, task_id)

    lost = threading.Event()
    lost.set()
    token = lease_lost_event.set(lost)
    gen_token = current_generation.set(g1)
    try:
        # Production guard returns True (abort)
        assert check_lease_or_abort(task_id, "complete") is True
        # Stale cannot write COMPLETE
        assert state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100) is False
        stored = state.get_task(task_id)
        assert stored.get("progress") != 100  # not completed
    finally:
        lease_lost_event.reset(token)
        current_generation.reset(gen_token)


def test_lease_loss_blocks_failed(redis_client):
    """Lease loss prevents marking FAILED; newer generation state preserved."""
    client, created = redis_client
    task_id = "test-term-failed"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=7)
    state._redis = client
    state.create_task(task_id, state=1, progress=30)
    g1 = acquire_generation(client, task_id)
    _g2 = acquire_generation(client, task_id)

    # Newer generation sets a state
    token2 = current_generation.set(_g2)
    try:
        state.update_task(task_id, state=2, progress=40)
    finally:
        current_generation.reset(token2)

    lost = threading.Event()
    lost.set()
    token = lease_lost_event.set(lost)
    gen_token = current_generation.set(g1)
    try:
        assert check_lease_or_abort(task_id, "mark-failed:pipeline") is True
        # Stale cannot write FAILED
        assert state.update_task(task_id, state=const.TASK_STATE_FAILED, progress=30, error="stale") is False
        stored = state.get_task(task_id)
        assert stored.get("state") == 2  # newer state preserved
        assert stored.get("error") != "stale"
    finally:
        lease_lost_event.reset(token)
        current_generation.reset(gen_token)


def test_current_owner_can_fail(redis_client):
    """Current generation can still mark FAILED when lease is not lost."""
    client, created = redis_client
    task_id = "test-term-owner-fail"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=7)
    state._redis = client
    state.create_task(task_id, state=1)
    gen = acquire_generation(client, task_id)
    token = current_generation.set(gen)
    try:
        assert check_lease_or_abort(task_id, "mark-failed") is False
        assert state.update_task(task_id, state=const.TASK_STATE_FAILED, progress=20, error="real") is True
        stored = state.get_task(task_id)
        assert stored.get("state") == const.TASK_STATE_FAILED
    finally:
        current_generation.reset(token)
