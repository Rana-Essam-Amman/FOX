"""Tests for production terminal-transition helpers. Real Redis."""

import threading

import pytest
import redis

from app.services.fencing import acquire_generation
from app.services.state import RedisState, current_generation
from app.services.lease_guard import lease_lost_event
from app.models import const


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=6, decode_responses=False)
    created = []
    yield client, created
    for key in created:
        client.delete(key)


def _bind_state(state):
    import app.services.state as sm
    orig = sm.state
    sm.state = state
    return orig


def test_complete_if_owner_current_succeeds(redis_client):
    """Current generation can complete via production helper."""
    client, created = redis_client
    task_id = "test-complete-current"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=6)
    state._redis = client
    state.create_task(task_id, state=4, progress=50)
    gen = acquire_generation(client, task_id)
    orig = _bind_state(state)
    token = current_generation.set(gen)
    try:
        from app.services.terminal_guard import complete_if_owner as _complete_if_owner
        assert _complete_if_owner(state, task_id, audio_file="/a.mp3") is True
        stored = state.get_task(task_id)
        assert stored.get("state") == const.TASK_STATE_COMPLETE
        assert stored.get("audio_file") == "/a.mp3"
    finally:
        current_generation.reset(token)
        _bind_state(orig)


def test_complete_if_owner_stale_rejected(redis_client):
    """Stale generation cannot complete; helper returns False."""
    client, created = redis_client
    task_id = "test-complete-stale"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=6)
    state._redis = client
    state.create_task(task_id, state=4)
    g1 = acquire_generation(client, task_id)
    _g2 = acquire_generation(client, task_id)
    orig = _bind_state(state)
    token = current_generation.set(g1)
    try:
        from app.services.terminal_guard import complete_if_owner as _complete_if_owner
        assert _complete_if_owner(state, task_id, subtitle_path="/s.srt") is False
        stored = state.get_task(task_id)
        assert stored.get("state") != const.TASK_STATE_COMPLETE
    finally:
        current_generation.reset(token)
        _bind_state(orig)


def test_complete_if_owner_lease_lost(redis_client):
    """Lease loss prevents complete even for current generation."""
    client, created = redis_client
    task_id = "test-complete-lease"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=6)
    state._redis = client
    state.create_task(task_id, state=4)
    gen = acquire_generation(client, task_id)
    orig = _bind_state(state)
    lost = threading.Event()
    lost.set()
    ltoken = lease_lost_event.set(lost)
    token = current_generation.set(gen)
    try:
        from app.services.terminal_guard import complete_if_owner as _complete_if_owner
        assert _complete_if_owner(state, task_id, materials=["/m.mp4"]) is False
        stored = state.get_task(task_id)
        assert stored.get("progress") != 100
    finally:
        lease_lost_event.reset(ltoken)
        current_generation.reset(token)
        _bind_state(orig)


def test_mark_failed_current_succeeds(redis_client):
    """Current generation can mark FAILED via production helper."""
    client, created = redis_client
    task_id = "test-fail-current"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=6)
    state._redis = client
    state.create_task(task_id, state=4, progress=30)
    gen = acquire_generation(client, task_id)
    orig = _bind_state(state)
    token = current_generation.set(gen)
    try:
        from app.services.terminal_guard import mark_failed_if_owner as _mark_task_failed
        result = _mark_task_failed(state, task_id, "audio", "real error")
        assert result.get("state") == const.TASK_STATE_FAILED
        stored = state.get_task(task_id)
        assert stored.get("state") == const.TASK_STATE_FAILED
    finally:
        current_generation.reset(token)
        _bind_state(orig)


def test_mark_failed_stale_rejected(redis_client):
    """Stale generation cannot mark FAILED; helper reports rejection."""
    client, created = redis_client
    task_id = "test-fail-stale"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=6)
    state._redis = client
    state.create_task(task_id, state=4)
    g1 = acquire_generation(client, task_id)
    _g2 = acquire_generation(client, task_id)
    # Newer sets a state
    token2 = current_generation.set(g2)
    try:
        state.update_task(task_id, state=2, progress=40)
    finally:
        current_generation.reset(token2)
    orig = _bind_state(state)
    token = current_generation.set(g1)
    try:
        from app.services.terminal_guard import mark_failed_if_owner as _mark_task_failed
        result = _mark_task_failed(state, task_id, "audio", "stale error")
        assert result.get("write_rejected") is True or result.get("state") is None
        stored = state.get_task(task_id)
        assert stored.get("state") == 2
    finally:
        current_generation.reset(token)
        _bind_state(orig)
