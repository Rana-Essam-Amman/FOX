"""Real Redis tests for fenced lease heartbeat renewal."""

import pytest
import redis

# Inline copy of the fenced renewal script to avoid heavy import chain in unit tests.
_RENEW_RUNNING_SLOT_SCRIPT = """
if not redis.call("ZSCORE", KEYS[1], ARGV[1]) then
    return 0
end
if ARGV[3] ~= "" and ARGV[4] ~= "" then
    local gen = redis.call("HGET", ARGV[3], "generation")
    if not gen or tonumber(gen) ~= tonumber(ARGV[4]) then
        return 0
    end
end
redis.call("ZADD", KEYS[1], "XX", ARGV[2], ARGV[1])
return 1
"""
from app.services.fencing import acquire_generation


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=13, decode_responses=False)
    client.flushdb()
    yield client
    client.flushdb()


def test_stale_generation_cannot_renew_lease(redis_client):
    slots_key = "running:slots"
    token = "worker-token"
    task_id = "task-hb"
    redis_client.hset(task_id, mapping={"task_id": task_id})
    gen1 = acquire_generation(redis_client, task_id)
    # Reserve slot
    redis_client.zadd(slots_key, {token: 1_000_000})

    # Newer worker acquires
    gen2 = acquire_generation(redis_client, task_id)
    assert gen2 > gen1

    # Stale renewal must fail
    result = redis_client.eval(
        _RENEW_RUNNING_SLOT_SCRIPT,
        1,
        slots_key,
        token,
        2_000_000,
        task_id,
        str(gen1),
    )
    assert result == 0
    # Slot still present but not renewed by stale
    assert redis_client.zscore(slots_key, token) == 1_000_000

    # Current generation can renew
    result = redis_client.eval(
        _RENEW_RUNNING_SLOT_SCRIPT,
        1,
        slots_key,
        token,
        2_000_000,
        task_id,
        str(gen2),
    )
    assert result == 1
    assert redis_client.zscore(slots_key, token) == 2_000_000


def test_renewal_without_generation_still_works(redis_client):
    slots_key = "running:slots"
    token = "plain-token"
    redis_client.zadd(slots_key, {token: 100})
    result = redis_client.eval(
        _RENEW_RUNNING_SLOT_SCRIPT,
        1,
        slots_key,
        token,
        200,
        "",
        "",
    )
    assert result == 1
    assert redis_client.zscore(slots_key, token) == 200
