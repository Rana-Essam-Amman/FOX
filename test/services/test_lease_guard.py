"""Tests for the production lease-loss guard. Real Redis, production code."""

import threading

import pytest
import redis

from app.services.lease_guard import (
    lease_lost_event,
    lease_lost,
    check_lease_or_abort,
)
from app.services.fencing import (
    acquire_generation,
    publish_artifact_reference,
    cleanup_generation_artifacts,
)
from app.services.state import RedisState, current_generation


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=8, decode_responses=False)
    created = []
    yield client, created
    for key in created:
        client.delete(key)


def test_production_lease_lost_aborts(tmp_path, redis_client):
    """Setting the production handoff's lease_lost event causes abort.

    The worker does not publish and does not mark a newer generation FAILED.
    Cleanup removes only the stale generation's artifacts.
    """
    client, created = redis_client
    task_id = "test-lease-abort"
    created.append(task_id)
    state = RedisState(host="localhost", port=6379, db=8)
    state._redis = client
    state.create_task(task_id, state=1, progress=50)

    # Newer generation owns
    g1 = acquire_generation(client, task_id)
    g2 = acquire_generation(client, task_id)
    assert g2 > g1

    # Stale worker's artifacts
    (tmp_path / "final.gen1.mp4").write_text("stale")
    (tmp_path / "final.gen2.mp4").write_text("current")

    # Bind the production lease_lost event
    lost = threading.Event()
    lost.set()
    token = lease_lost_event.set(lost)
    gen_token = current_generation.set(g1)
    try:
        # Production guard returns True (abort)
        assert check_lease_or_abort(
            task_id,
            "publish",
            cleanup=cleanup_generation_artifacts,
            task_dir=lambda t: str(tmp_path),
            current_generation=g1,
        ) is True

        # Stale gen1 artifact cleaned; gen2 preserved
        assert not (tmp_path / "final.gen1.mp4").exists()
        assert (tmp_path / "final.gen2.mp4").exists()

        # Stale worker cannot publish
        assert publish_artifact_reference(client, task_id, "videos", ["/stale"], g1) is False

        # Newer generation's state is not marked FAILED
        stored = state.get_task(task_id)
        assert stored.get("state") != 3  # not FAILED
    finally:
        lease_lost_event.reset(token)
        current_generation.reset(gen_token)


def test_lease_not_lost_continues(redis_client):
    """When lease is not lost, guard returns False (continue)."""
    lost = threading.Event()  # not set
    token = lease_lost_event.set(lost)
    try:
        assert lease_lost() is False
        assert check_lease_or_abort("t", "stage") is False
    finally:
        lease_lost_event.reset(token)


def test_no_event_continues():
    """No lease event bound means not lost."""
    assert lease_lost() is False
    assert check_lease_or_abort("t", "stage") is False
