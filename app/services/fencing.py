from typing import Any, Mapping
import os
"""Redis fencing primitives for task ownership.

Generations are stored in the task hash under the field "generation".
Acquisition atomically increments the generation. All subsequent mutations
must supply the expected generation; Redis rejects stale writes atomically.
"""


# Lua: atomically acquire a new generation for a task hash.
# Returns the new generation (integer) or nil if the key is not a hash.
_ACQUIRE_GENERATION_SCRIPT = """
if redis.call("TYPE", KEYS[1]).ok ~= "hash" then
    return nil
end
if redis.call("HGET", KEYS[1], "task_id") ~= KEYS[1] then
    return nil
end
local current = redis.call("HGET", KEYS[1], "generation")
local next_gen = 1
if current then
    local current_number = tonumber(current)
    if not current_number or current_number < 0 or current_number % 1 ~= 0 then
        return nil
    end
    next_gen = current_number + 1
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
if redis.call("HGET", KEYS[1], "task_id") ~= KEYS[1] then
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


def is_valid_generation(value: object) -> bool:
    """Accept only positive integer generation tokens; bool is not an int here."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 1
    )


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
    if not is_valid_generation(expected_generation):
        return False
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

# Production user-task lease renewal script. Imported by redis_manager.
RENEW_RUNNING_SLOT_SCRIPT = """
-- User-task lease renewal. All arguments are required.
-- ARGV[1] = token
-- ARGV[2] = new deadline
-- ARGV[3] = task_id (must be non-empty)
-- ARGV[4] = expected generation (must be non-empty positive integer)
if ARGV[3] == "" or ARGV[4] == "" then
    return 0
end
local expected = tonumber(ARGV[4])
if not expected or expected < 1 then
    return 0
end
if not redis.call("ZSCORE", KEYS[1], ARGV[1]) then
    return 0
end
local gen = redis.call("HGET", ARGV[3], "generation")
if not gen or tonumber(gen) ~= expected then
    return 0
end
redis.call("ZADD", KEYS[1], "XX", ARGV[2], ARGV[1])
return 1
"""



# Publication helpers used by task.py. Pure functions; no heavy imports.


def artifact_path_for_generation(task_id: str, base_name: str, generation: int | None, task_dir: str | None = None) -> str:
    """Return an immutable generation-scoped artifact path under the real task storage.

    Uses app.utils.utils.task_dir when task_dir is not supplied so paths
    resolve under the configured FOX storage directory.
    """
    if task_dir is None:
        from app.utils.utils import task_dir as _task_dir
        task_dir = _task_dir(task_id)
    if is_valid_generation(generation):
        stem, ext = os.path.splitext(base_name)
        gen_name = f"{stem}.gen{generation}{ext}"
        return os.path.join(task_dir, gen_name)
    return os.path.join(task_dir, base_name)


def publish_artifact_reference(
    redis_client,
    task_id: str,
    field: str,
    artifact_path: str,
    expected_generation: int | None,
) -> bool:
    """Atomically publish an artifact reference only if we still own the generation.

    Fail closed on missing/invalid generation or Redis errors.
    """
    if not is_valid_generation(expected_generation):
        return False
    try:
        success = compare_and_write(
            redis_client,
            task_id,
            expected_generation,
            {field: artifact_path},
        )
    except Exception:
        return False
    return bool(success)


def cleanup_generation_artifacts(task_dir: str, generation: int) -> None:
    """Remove only artifacts belonging to the exact generation.

    Matches ".gen{N}." or ".gen{N}" at end of stem so ".gen1" does not
    match ".gen10" or ".gen11".
    """
    if not os.path.isdir(task_dir):
        return
    marker = f".gen{generation}."
    marker_end = f".gen{generation}"
    for name in os.listdir(task_dir):
        stem, ext = os.path.splitext(name)
        if marker in name or stem.endswith(marker_end):
            try:
                os.remove(os.path.join(task_dir, name))
            except OSError:
                pass
