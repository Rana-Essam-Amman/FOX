"""Redis fencing primitives for task ownership.

Generations are stored in the task hash under the field "generation".
Acquisition atomically increments the generation. All subsequent mutations
must supply the expected generation; Redis rejects stale writes atomically.
"""

from typing import Any, Mapping

# Lua: atomically acquire a new generation for a task hash.
# Returns the new generation (integer) or nil if the key is not a hash.
_ACQUIRE_GENERATION_SCRIPT = """
if redis.call("TYPE", KEYS[1]).ok ~= "hash" then
    return nil
end
local current = redis.call("HGET", KEYS[1], "generation")
local next_gen = 1
if current then
    next_gen = tonumber(current) + 1
end
redis.call("HSET", KEYS[1], "generation", next_gen)
return next_gen
"""

# Lua: compare-and-write. Succeeds only if stored generation matches expected.
# ARGV[1] = expected generation (string)
# ARGV[2..] = field, value pairs to set.
# Returns 1 on success, 0 on mismatch or wrong type.
_COMPARE_AND_WRITE_SCRIPT = """
if redis.call("TYPE", KEYS[1]).ok ~= "hash" then
    return 0
end
local current = redis.call("HGET", KEYS[1], "generation")
if not current or tonumber(current) ~= tonumber(ARGV[1]) then
    return 0
end
for i = 2, #ARGV, 2 do
    redis.call("HSET", KEYS[1], ARGV[i], ARGV[i + 1])
end
return 1
"""


def acquire_generation(redis_client, task_id: str) -> int | None:
    """Atomically increment and return the new generation for task_id.

    Returns None if the key does not exist or is not a hash.
    """
    result = redis_client.eval(_ACQUIRE_GENERATION_SCRIPT, 1, task_id)
    if result is None:
        return None
    return int(result)


def compare_and_write(
    redis_client,
    task_id: str,
    expected_generation: int,
    fields: Mapping[str, Any],
) -> bool:
    """Atomically write fields only if the current generation matches expected.

    Returns True if the write succeeded, False if the generation was stale
    or the key is not a task hash.
    """
    if not fields:
        # Still check generation for a no-op confirmation.
        args = [str(expected_generation)]
    else:
        args = [str(expected_generation)]
        for key, value in fields.items():
            args.append(key)
            args.append(str(value))
    result = redis_client.eval(
        _COMPARE_AND_WRITE_SCRIPT,
        1,
        task_id,
        *args,
    )
    return bool(result)


def get_generation(redis_client, task_id: str) -> int | None:
    """Read the current generation. Returns None if absent or wrong type."""
    try:
        value = redis_client.hget(task_id, "generation")
    except Exception:
        return None
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
