import ast
import copy
import threading
from abc import ABC, abstractmethod
from contextvars import ContextVar

from redis.exceptions import ResponseError
from itertools import islice

from app.config import config
from app.models import const


_CREATE_TASK_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) ~= 0 then
    return 0
end
for i = 1, #ARGV, 2 do
    redis.call("HSET", KEYS[1], ARGV[i], ARGV[i + 1])
end
return 1
"""


_PATCH_EXISTING_TASK_SCRIPT = """
-- Match discovery/get_task ownership checks inside the same atomic operation.
-- Other services and our queue may share this database or reuse a deleted key.
if redis.call("TYPE", KEYS[1]).ok ~= "hash" then
    return 0
end
if redis.call("HGET", KEYS[1], "task_id") ~= KEYS[1] then
    return 0
end

for index = 1, #ARGV, 2 do
    redis.call("HSET", KEYS[1], ARGV[index], ARGV[index + 1])
end

return 1
"""

_ATOMIC_NO_GEN_RECOVERY_SCRIPT = """
local key = KEYS[1]
if redis.call('TYPE', key).ok ~= 'hash' then
    return 0
end
local tid = redis.call('HGET', key, 'task_id')
if tid ~= ARGV[1] then
    return 0
end
local gen = redis.call('HGET', key, 'generation')
-- No-generation recovery is only for records where the field is truly absent.
-- Empty or zero-valued generations are malformed/invalid, not "never started".
if gen then
    return 0
end
for i = 2, #ARGV, 2 do
    redis.call('HSET', key, ARGV[i], ARGV[i+1])
end
return 1
"""


_DELETE_OWNED_TASK_SCRIPT = """
if redis.call("TYPE", KEYS[1]).ok ~= "hash" then
    return 0
end
if redis.call("HGET", KEYS[1], "task_id") ~= KEYS[1] then
    return 0
end

return redis.call("DEL", KEYS[1])
"""


# Generation bound to the current worker execution.
# Set by the worker start path (Increment 3). RedisState mutation methods
# use this value when no explicit generation is supplied.
current_generation: ContextVar[int | None] = ContextVar("current_generation", default=None)

# Base class for state management
class BaseState(ABC):
    @abstractmethod
    def update_task(self, task_id: str, state: int, progress: int = 0, **kwargs):
        pass

    @abstractmethod
    def get_task(self, task_id: str):
        pass

    @abstractmethod
    def get_all_tasks(self, page: int, page_size: int):
        pass

    @abstractmethod
    def list_task_ids(self, scan_count: int = 100) -> list[str]:
        """获取一次遍历中的任务 ID，供启动恢复等全量操作使用。"""
        pass

    @abstractmethod
    def patch_task(self, task_id: str, **kwargs) -> bool:
        """只更新已有任务的指定字段；任务不存在时返回 False。"""
        pass

    @abstractmethod
    def acquire_generation(self, task_id: str) -> int | None:
        """Atomically acquire the next worker generation for an existing task."""
        pass

    @abstractmethod
    def publish_artifact_reference(
        self,
        task_id: str,
        field: str,
        artifact_reference,
        expected_generation: int | None,
    ) -> bool:
        """Publish an artifact reference only while the caller owns the generation."""
        pass

    @abstractmethod
    def authorized_delete(self, task_id: str) -> bool:
        """Delete a task after the route has verified the caller's ownership."""
        pass


# Memory state management
class MemoryState(BaseState):
    def __init__(self):
        self._tasks = {}
        self._lock = threading.RLock()

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        with self._lock:
            total = len(self._tasks)
            tasks = [
                copy.deepcopy(task)
                for task in islice(self._tasks.values(), start, end)
            ]
        return tasks, total

    def list_task_ids(self, scan_count: int = 100) -> list[str]:
        with self._lock:
            return list(self._tasks)

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        with self._lock:
            expected_generation = current_generation.get()
            existing = self._tasks.get(task_id)
            if expected_generation is not None and (
                isinstance(expected_generation, bool)
                or not isinstance(expected_generation, int)
                or expected_generation < 1
                or existing is None
                or existing.get("generation") != expected_generation
            ):
                return False
            self._tasks[task_id] = {
                # Keep fields from earlier pipeline stages, matching Redis
                # HSET updates. A progress-only update must not erase the
                # WebUI subject or diagnostic details already stored.
                **self._tasks.get(task_id, {}),
                "task_id": task_id,
                "state": state,
                "progress": progress,
                **copy.deepcopy(kwargs),
            }
        return True

    def get_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id, None)
            return copy.deepcopy(task) if task is not None else None

    def patch_task(
        self, task_id: str, generation: int | None = None, **kwargs
    ) -> bool:
        # Match RedisState: worker-originated patches must retain generation
        # ownership. The context is copied into cross-post worker threads.
        expected = generation if generation is not None else current_generation.get()
        if (
            isinstance(expected, bool)
            or not isinstance(expected, int)
            or expected < 1
        ):
            return False
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.get("generation") != expected:
                return False
            task.update(copy.deepcopy(kwargs))
            return True

    def create_task(self, task_id: str, state: int = const.TASK_STATE_PROCESSING, progress: int = 0, **kwargs) -> bool:
        """Initial creation for in-memory execution. Always succeeds if called."""
        return self.update_task(task_id, state=state, progress=progress, **kwargs)

    def acquire_generation(self, task_id: str) -> int | None:
        """Atomically increment the generation of an existing in-memory task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            stored = task.get("generation", 0)
            if isinstance(stored, bool):
                return None
            if isinstance(stored, str):
                if not stored.isdigit():
                    return None
                stored = int(stored)
            if not isinstance(stored, int) or stored < 0:
                return None
            generation = stored + 1
            task["generation"] = generation
            return generation

    def publish_artifact_reference(
        self, task_id: str, field: str, artifact_reference, expected_generation: int | None
    ) -> bool:
        """Atomically publish only while the task still has this generation."""
        if (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or expected_generation < 1
        ):
            return False
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.get("generation") != expected_generation:
                return False
            task[field] = copy.deepcopy(artifact_reference)
            return True

    def authorized_delete(self, task_id: str) -> bool:
        """Delete only after the caller has completed route-level authorization."""
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def recovery_patch(self, task_id: str, expected_generation: int | None = None, **kwargs) -> bool:
        """Narrow recovery update for queue dequeue failures.

        Semantics match RedisState / compare_and_write exactly:
        - expected_generation must be None or a positive integer (not bool).
        - If a positive integer, the stored generation must exist, be a valid
          integer, and match exactly.
        - If None, recovery is allowed only when the task has no generation
          (never-started).
        - Zero, negative, boolean, or otherwise invalid generations fail closed.
        - Malformed stored generation values fail closed.
        - Never recreates a deleted task.
        - Only allows state, failed_stage, error.
        """
        allowed = {"state", "failed_stage", "error"}
        if not set(kwargs.keys()).issubset(allowed):
            raise ValueError(f"recovery_patch only allows {allowed}")
        if not kwargs:
            return False
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            stored_gen = task.get("generation")
            if expected_generation is None:
                # Never-started recovery only.
                if stored_gen is not None:
                    return False
            elif isinstance(expected_generation, bool) or not isinstance(expected_generation, int) or expected_generation < 1:
                # Booleans (True/False), non-integers, zero, negative: fail closed.
                return False
            else:
                # Exact match required. Reject booleans, fractions, and malformed
                # values without lossy int() truncation. Redis uses tonumber +
                # numeric equality; we require a true integer representation.
                if stored_gen is None or isinstance(stored_gen, bool):
                    return False
                try:
                    if isinstance(stored_gen, str):
                        # Accept only pure integer strings (no fractional part).
                        if not stored_gen.lstrip("-").isdigit():
                            return False
                        stored_as_int = int(stored_gen)
                    elif isinstance(stored_gen, int):
                        stored_as_int = stored_gen
                    elif isinstance(stored_gen, float):
                        # Reject non-integral floats (1.5); accept only exact
                        # integer-valued floats if we choose Redis parity.
                        # Redis tonumber("1.0") == 1, so we accept only when
                        # the float is exactly integral.
                        if not stored_gen.is_integer():
                            return False
                        stored_as_int = int(stored_gen)
                    else:
                        return False
                    if stored_as_int != expected_generation:
                        return False
                except (TypeError, ValueError):
                    return False
            task.update(copy.deepcopy(kwargs))
            return True

    def delete_task(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)


# Redis state management
class RedisState(BaseState):
    """
    Redis-backed task state.

    Trust boundary: Redis is expected to be private to this application. Task
    values are written by MoneyPrinterTurbo and converted back from strings for
    compatibility with existing state records. Do not expose this Redis database
    to untrusted writers without replacing deserialization with a stricter
    schema-based format.
    """

    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self._redis = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def acquire_generation(self, task_id: str) -> int | None:
        from app.services.fencing import acquire_generation
        return acquire_generation(self._redis, task_id)

    def publish_artifact_reference(
        self, task_id: str, field: str, artifact_reference, expected_generation: int | None
    ) -> bool:
        from app.services.fencing import publish_artifact_reference
        return publish_artifact_reference(
            self._redis, task_id, field, artifact_reference, expected_generation
        )

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        # 每一页都以同一套确定性顺序切片，而不是依赖 SCAN 的返回顺序。
        # 这仍不是并发增删任务时的事务快照；无索引时优先保证静态任务集
        # 的分页正确性，并让 total 统计去重后的任务键。
        task_ids = self.list_task_ids(scan_count=page_size)
        tasks = []
        for task_id in task_ids[start:end]:
            task = self.get_task(task_id)
            if task is not None:
                tasks.append(task)
        return tasks, len(task_ids)

    def list_task_ids(self, scan_count: int = 100) -> list[str]:
        """Return only this application's task hashes from a possibly shared DB."""
        task_keys = set()
        cursor = 0
        while True:
            # Redis 数据库中除了任务 Hash，还可能存在 RedisTaskManager 使用的
            # List 队列。只扫描 Hash 可以避免对队列执行 HGETALL 时触发
            # WRONGTYPE。COUNT 是扫描工作量提示，不保证每批返回的数量。
            cursor, keys = self._redis.scan(
                cursor,
                count=scan_count,
                _type="HASH",
            )
            # Redis db 0 may also contain hashes belonging to other services.
            # Check the task marker in one pipelined round trip per SCAN batch;
            # exposing all HASH keys here can leak their fields through /tasks.
            candidates = [key for key in dict.fromkeys(keys) if key not in task_keys]
            if candidates:
                with self._redis.pipeline(transaction=False) as pipeline:
                    for key in candidates:
                        pipeline.hget(key, "task_id")
                    # A key can change type after SCAN. Isolate that row instead
                    # of letting one WRONGTYPE abort the whole task listing.
                    embedded_ids = pipeline.execute(raise_on_error=False)
                for key, embedded_id in zip(candidates, embedded_ids):
                    if isinstance(embedded_id, ResponseError):
                        if str(embedded_id).startswith("WRONGTYPE"):
                            continue
                        raise embedded_id
                    if embedded_id == key:
                        task_keys.add(key)
            if cursor == 0:
                break
        # 按任务键排序不依赖 Hash 扫描顺序；不额外维护索引，也不改变旧任务。
        return [key.decode("utf-8") for key in sorted(task_keys)]

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        generation: int | None = None,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

        expected = generation if generation is not None else current_generation.get()
        if expected is None or expected < 1:
            # Worker mutations require a valid generation. No unfenced fallback.
            return False
        from app.services.fencing import compare_and_write
        success = compare_and_write(
            self._redis,
            task_id,
            expected,
            {field: self._serialize_field(field, value) for field, value in fields.items()},
        )
        return bool(success)

    def create_task(self, task_id: str, state: int = const.TASK_STATE_PROCESSING, progress: int = 0, **kwargs) -> bool:
        """Explicit initial creation. Not for worker mutations.

        Creates the task hash if it does not exist. Does not check generation.
        Callers must be outside the worker trust boundary (API route after auth).
        """
        progress = int(progress)
        if progress > 100:
            progress = 100
        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }
        mapping = {
            field: self._serialize_field(field, value)
            for field, value in fields.items()
        }
        args = []
        for field, value in mapping.items():
            args.extend((field, value))
        return bool(self._redis.eval(
            _CREATE_TASK_SCRIPT, 1, task_id, *args
        ))

    def authorized_delete(self, task_id: str) -> bool:
        """Explicit deletion after route-level ownership authorization.

        Does not check generation. Caller must have already verified the
        requesting user owns the task.
        """
        result = self._redis.eval(_DELETE_OWNED_TASK_SCRIPT, 1, task_id)
        return bool(result)

    def recovery_patch(self, task_id: str, expected_generation: int | None = None, **kwargs) -> bool:
        """Narrow recovery update for queue dequeue failures.

        If expected_generation is provided, the write is generation-fenced.
        If expected_generation is None, the write is allowed only when the task
        has no generation yet (never started). A task that already has a
        generation is left untouched so a stale queue item cannot overwrite a
        newer attempt. Never recreates a deleted task.
        """
        allowed = {"state", "failed_stage", "error"}
        if not set(kwargs.keys()).issubset(allowed):
            raise ValueError(f"recovery_patch only allows {allowed}")
        if not kwargs:
            return False
        from app.services.fencing import compare_and_write
        try:
            if expected_generation is None:
                # Atomic recovery is permitted only for never-started records.
                # The Lua script requires the generation field to be absent.
                args = [task_id]
                for k, v in kwargs.items():
                    args.append(k)
                    args.append(self._serialize_field(k, v))
                return bool(self._redis.eval(
                    _ATOMIC_NO_GEN_RECOVERY_SCRIPT, 1, task_id, *args
                ))
            # An explicitly supplied generation must be a positive integer.
            # Do not let 0/False/negative values fall through to no-gen recovery.
            if (
                isinstance(expected_generation, bool)
                or not isinstance(expected_generation, int)
                or expected_generation < 1
            ):
                return False
            return bool(compare_and_write(
                self._redis, task_id, expected_generation, kwargs
            ))
        except Exception:
            return False


    def get_task(self, task_id: str):
        try:
            task_data = self._redis.hgetall(task_id)
        except ResponseError as exc:
            # Arbitrary task IDs can name the application's List queue or
            # another service's non-hash key. Those are not task records.
            if str(exc).startswith("WRONGTYPE"):
                return None
            raise
        # An API caller may ask for any Redis key by name. Require the same
        # marker as list_task_ids before returning a hash's contents.
        if not task_data or task_data.get(b"task_id") != task_id.encode("utf-8"):
            return None

        task = {
            key.decode("utf-8"): (
                value.decode("utf-8")
                if key == b"task_id"
                else self._convert_to_original_type(value)
            )
            for key, value in task_data.items()
        }
        return task

    def patch_task(self, task_id: str, generation: int | None = None, **kwargs) -> bool:
        if not kwargs:
            return False
        expected = generation if generation is not None else current_generation.get()
        if expected is None or expected < 1:
            return False
        from app.services.fencing import compare_and_write
        fields = {
            field: self._serialize_field(field, value)
            for field, value in kwargs.items()
        }
        return compare_and_write(self._redis, task_id, expected, fields)

    def delete_task(self, task_id: str, generation: int | None = None) -> bool:
        """Worker-originated delete. Requires valid generation. Returns actual result."""
        expected = generation if generation is not None else current_generation.get()
        from app.services.fencing import is_valid_generation
        if not is_valid_generation(expected):
            return False
        script = """
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
        return redis.call("DEL", KEYS[1])
        """
        result = self._redis.eval(script, 1, task_id, str(expected))
        return bool(result)

    @staticmethod
    def _serialize_field(field, value):
        # Quote strings so literal_eval cannot turn a subject like "2026" or
        # an error like "None" into an integer/None. Keep the ownership marker
        # raw: task discovery compares its bytes directly against the Redis key.
        if isinstance(value, str) and field != "task_id":
            return repr(value)
        return str(value)

    @staticmethod
    def _convert_to_original_type(value):
        """
        Convert values written by this application back to common Python types.

        This compatibility parser assumes Redis is inside the application's
        trust boundary. If Redis can be written by untrusted clients, task state
        should move to a strict JSON/schema parser instead of open-ended literal
        conversion.
        """
        value_str = value.decode("utf-8")

        try:
            # try to convert byte string array to list
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            pass

        if value_str.isdigit():
            return int(value_str)
        # Add more conversions here if needed
        return value_str


# Global state
_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)

state = (
    RedisState(
        host=_redis_host, port=_redis_port, db=_redis_db, password=_redis_password
    )
    if _enable_redis
    else MemoryState()
)
