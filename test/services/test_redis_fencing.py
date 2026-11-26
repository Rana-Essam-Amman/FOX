"""Real Redis tests for fencing primitives."""

import uuid

import pytest
import redis

from app.services.fencing import acquire_generation, compare_and_write, get_generation


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=False)
    # no flushdb
    yield client
    # no flushdb


def test_acquire_generation_ordering(redis_client):
    task_id = f"task-order-{uuid.uuid4().hex[:8]}"
    redis_client.hset(task_id, mapping={"task_id": task_id, "state": "1"})
    g1 = acquire_generation(redis_client, task_id)
    g2 = acquire_generation(redis_client, task_id)
    g3 = acquire_generation(redis_client, task_id)
    assert g1 == 1
    assert g2 == 2
    assert g3 == 3
    assert get_generation(redis_client, task_id) == 3


def test_stale_generation_rejected(redis_client):
    task_id = "task-stale"
    redis_client.hset(task_id, mapping={"task_id": task_id, "state": "1"})
    gen = acquire_generation(redis_client, task_id)
    # Newer acquisition
    newer = acquire_generation(redis_client, task_id)
    assert newer == gen + 1
    # Stale write must fail
    success = compare_and_write(
        redis_client, task_id, gen, {"progress": "50", "state": "2"}
    )
    assert success is False
    # Current generation write succeeds
    success = compare_and_write(
        redis_client, task_id, newer, {"progress": "50", "state": "2"}
    )
    assert success is True
    stored = redis_client.hgetall(task_id)
    assert stored[b"progress"] == b"50"
    assert stored[b"generation"] == str(newer).encode()


def test_concurrent_acquisition(redis_client):
    import threading

    task_id = f"task-concurrent-{uuid.uuid4().hex[:8]}"
    redis_client.hset(task_id, mapping={"task_id": task_id})
    results = []
    lock = threading.Lock()

    def worker():
        g = acquire_generation(redis_client, task_id)
        with lock:
            results.append(g)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 10
    assert sorted(results) == list(range(1, 11))
    assert get_generation(redis_client, task_id) == 10


def test_compare_and_write_rejects_missing_or_wrong_type(redis_client):
    # Non-existent key
    assert compare_and_write(redis_client, "missing", 1, {"a": "b"}) is False
    # Wrong type
    redis_client.set("not-hash", "value")
    assert compare_and_write(redis_client, "not-hash", 1, {"a": "b"}) is False
    # Hash without generation
    redis_client.hset("no-gen", "task_id", "no-gen")
    assert compare_and_write(redis_client, "no-gen", 1, {"progress": "1"}) is False


def test_acquire_on_missing_key_returns_none(redis_client):
    assert acquire_generation(redis_client, "does-not-exist") is None
