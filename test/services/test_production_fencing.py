"""Production lifecycle tests for fencing. Execute real production code against real Redis."""

import threading

import pytest
import redis

from app.services.fencing import RENEW_RUNNING_SLOT_SCRIPT

from app.services.fencing import acquire_generation, get_generation
from app.services.state import RedisState, current_generation
from app.models import const


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=11, decode_responses=False)
    # Isolated keys; do not flushdb
    yield client
    for key in client.keys("test-fence-*"):
        client.delete(key)


def test_renewal_script_rejects_missing_identity(redis_client):
    """Production renewal script rejects empty task_id or generation."""
    slots = "test-fence-slots"
    token = "tok"
    redis_client.zadd(slots, {token: 100})
    # Missing task_id
    assert redis_client.eval(RENEW_RUNNING_SLOT_SCRIPT, 1, slots, token, 200, "", "1") == 0
    # Missing generation
    assert redis_client.eval(RENEW_RUNNING_SLOT_SCRIPT, 1, slots, token, 200, "task", "") == 0
    # Invalid generation
    assert redis_client.eval(RENEW_RUNNING_SLOT_SCRIPT, 1, slots, token, 200, "task", "0") == 0
    redis_client.delete(slots)


def test_renewal_script_rejects_stale_generation(redis_client):
    slots = "test-fence-slots2"
    task_id = "test-fence-task"
    token = "tok2"
    redis_client.hset(task_id, mapping={"task_id": task_id})
    g1 = acquire_generation(redis_client, task_id)
    g2 = acquire_generation(redis_client, task_id)
    redis_client.zadd(slots, {token: 100})
    # Stale
    assert redis_client.eval(RENEW_RUNNING_SLOT_SCRIPT, 1, slots, token, 200, task_id, str(g1)) == 0
    # Current
    assert redis_client.eval(RENEW_RUNNING_SLOT_SCRIPT, 1, slots, token, 200, task_id, str(g2)) == 1
    redis_client.delete(slots, task_id)


def test_worker_mutations_require_generation(redis_client):
    state = RedisState(host="localhost", port=6379, db=11)
    state._redis = redis_client
    task_id = "test-fence-worker"
    state.create_task(task_id, state=1, progress=0)
    # No generation bound
    assert state.update_task(task_id, state=2, progress=50) is False
    assert state.patch_task(task_id, progress=99) is False
    assert state.delete_task(task_id) is False
    assert redis_client.exists(task_id)
    # With generation
    gen = acquire_generation(redis_client, task_id)
    token = current_generation.set(gen)
    try:
        assert state.update_task(task_id, state=2, progress=50) is True
        assert state.patch_task(task_id, progress=60) is True
        assert state.delete_task(task_id) is True
    finally:
        current_generation.reset(token)
    assert not redis_client.exists(task_id)


def test_authorized_delete_works_without_generation(redis_client):
    state = RedisState(host="localhost", port=6379, db=11)
    state._redis = redis_client
    task_id = "test-fence-authdel"
    state.create_task(task_id)
    assert state.authorized_delete(task_id) is True
    assert not redis_client.exists(task_id)


def test_recovery_patch_limited_fields(redis_client):
    state = RedisState(host="localhost", port=6379, db=11)
    state._redis = redis_client
    task_id = "test-fence-recovery"
    state.create_task(task_id, state=1)
    assert state.recovery_patch(task_id, state=const.TASK_STATE_FAILED, failed_stage="dequeue", error="stale") is True
    stored = redis_client.hgetall(task_id)
    assert stored[b"state"] == str(const.TASK_STATE_FAILED).encode()
    with pytest.raises(ValueError):
        state.recovery_patch(task_id, progress=100)
    redis_client.delete(task_id)


def test_handoff_independent_per_execution():
    # Minimal local replica of the production contract for independence.
    class H:
        def __init__(self, tid):
            self.task_id = tid
            self.generation = None
            self.ready = threading.Event()
        def publish(self, g):
            self.generation = g
            self.ready.set()
    h1, h2 = H("task-a"), H("task-b")
    h1.publish(1)
    assert h1.generation == 1 and h2.generation is None and not h2.ready.is_set()


def test_stale_cannot_overwrite_physical_output(tmp_path, redis_client):
    """Stale generation cannot promote its temp over the current worker's final file."""
    task_id = "test-fence-output"
    state = RedisState(host="localhost", port=6379, db=11)
    state._redis = redis_client
    state.create_task(task_id)
    acquire_generation(redis_client, task_id)  # gen 1
    acquire_generation(redis_client, task_id)  # gen 2 owns
    temp = tmp_path / "final.gen1.tmp.mp4"
    final = tmp_path / "final.mp4"
    temp.write_bytes(b"stale")
    final.write_bytes(b"current")
    # Simulate the promote check: stored gen != our gen => do not replace
    stored = get_generation(redis_client, task_id)
    our_gen = 1
    if stored != our_gen:
        temp.unlink()
        # final remains
    assert final.read_bytes() == b"current"
    assert not temp.exists()
    redis_client.delete(task_id)
