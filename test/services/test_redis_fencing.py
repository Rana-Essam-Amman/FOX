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


def test_idempotent_generation_acquisition_recovers_lost_reply(redis_client):
    task_id = f"task-lost-reply-{uuid.uuid4().hex}"
    redis_client.hset(task_id, mapping={"task_id": task_id, "state": "1"})

    class LoseFirstReply:
        def __init__(self, client):
            self.client = client
            self.calls = 0

        def hget(self, *args):
            return self.client.hget(*args)

        def eval(self, *args):
            self.calls += 1
            result = self.client.eval(*args)
            if self.calls == 1:
                raise redis.exceptions.TimeoutError("simulated lost Redis reply")
            return result

    wrapped = LoseFirstReply(redis_client)
    generation = acquire_generation(
        wrapped, task_id, request_id=f"request-{uuid.uuid4().hex}"
    )

    assert generation == 1
    assert wrapped.calls == 2
    assert get_generation(redis_client, task_id) == 1


def test_ambiguous_retry_cannot_take_over_a_competing_generation(redis_client):
    task_id = f"task-competing-{uuid.uuid4().hex}"
    redis_client.hset(task_id, mapping={"task_id": task_id, "state": "1"})

    class CompetingAcquisitionAfterLostReply:
        def __init__(self, client):
            self.client = client
            self.calls = 0

        def hget(self, *args):
            return self.client.hget(*args)

        def eval(self, *args):
            self.calls += 1
            result = self.client.eval(*args)
            if self.calls == 1:
                assert acquire_generation(
                    self.client, task_id, request_id="competing-worker"
                ) == 2
                raise redis.exceptions.TimeoutError("simulated lost Redis reply")
            return result

    wrapped = CompetingAcquisitionAfterLostReply(redis_client)
    result = acquire_generation(
        wrapped, task_id, request_id="original-worker"
    )

    assert result is None
    assert wrapped.calls == 2
    assert get_generation(redis_client, task_id) == 2


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
