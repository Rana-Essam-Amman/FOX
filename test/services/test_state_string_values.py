import pytest

from app.models import const
from app.services.state import RedisState
from test.services.test_state import _FakeRedis


class _FencedFakeRedis(_FakeRedis):
    def eval(self, script, numkeys, key, *arguments):
        if isinstance(key, str):
            key = key.encode("utf-8")
        target = self.data.get(key)
        if "EXISTS" in script:
            if target is not None:
                return 0
            target = {}
            for index in range(0, len(arguments), 2):
                if index + 1 >= len(arguments):
                    return 0
                field = str(arguments[index]).encode("utf-8")
                value = str(arguments[index + 1]).encode("utf-8")
                target[field] = value
            self.data[key] = target
            return 1
        if target is None or target.get(b"task_id") != key:
            return 0
        if "next_gen" in script:
            current = target.get(b"generation", b"0")
            try:
                generation = int(current) + 1
            except (TypeError, ValueError):
                return None
            target[b"generation"] = str(generation).encode("utf-8")
            return generation
        if not arguments:
            return 0
        try:
            expected = int(arguments[0])
            stored = int(target.get(b"generation", b"0"))
        except (TypeError, ValueError):
            return 0
        if expected < 1 or stored != expected:
            return 0
        for index in range(1, len(arguments), 2):
            if index + 1 >= len(arguments):
                return 0
            field = str(arguments[index]).encode("utf-8")
            value = str(arguments[index + 1]).encode("utf-8")
            target[field] = value
        return 1


@pytest.mark.parametrize("task_id", ["2026", "None", "False", "[]", "'quoted'"])
def test_redis_preserves_literal_looking_task_ids(task_id):
    state = RedisState.__new__(RedisState)
    state._redis = _FencedFakeRedis([[]])
    state.create_task(task_id, state=const.TASK_STATE_COMPLETE)
    state._redis.batches = [[task_id.encode()]]

    assert state.list_task_ids() == [task_id]
    task = state.get_task(task_id)
    assert task["task_id"] == task_id
    assert state.get_task(task["task_id"]) == task
    assert state.get_all_tasks(page=1, page_size=10) == ([task], 1)


def test_redis_update_preserves_literal_looking_string_values():
    state = RedisState.__new__(RedisState)
    state._redis = _FencedFakeRedis([[]])
    samples = ["2026", "None", "False", "[]", "{'x': 1}", "'quoted'", "line\nnext", "日本語"]
    for index, value in enumerate(samples):
        task_id = f"literal-{index}"
        state.create_task(task_id, state=const.TASK_STATE_COMPLETE)
        generation = state.acquire_generation(task_id)
        assert state.update_task(
            task_id, generation=generation, video_subject=value
        )
        assert state.get_task(task_id)["video_subject"] == value
        assert state._redis.data[task_id.encode()][b"task_id"] == task_id.encode()


def test_redis_patch_preserves_string_and_non_string_types():
    state = RedisState.__new__(RedisState)
    state._redis = _FencedFakeRedis([[]])
    state.create_task("task-literals")
    generation = state.acquire_generation("task-literals")
    for value in ["None", "False", "2026", "[]"]:
        assert state.patch_task("task-literals", generation=generation, error=value)
        assert state.get_task("task-literals")["error"] == value
    assert state.patch_task("task-literals", generation=generation, error=None, finished=True, attempts=3, videos=["final.mp4"])
    task = state.get_task("task-literals")
    assert task["error"] is None
    assert task["finished"] is True
    assert task["attempts"] == 3
    assert task["videos"] == ["final.mp4"]


def test_redis_legacy_serialized_records_remain_readable():
    state = RedisState.__new__(RedisState)
    state._redis = _FakeRedis([[]])
    state._redis.data[b"legacy"] = {b"task_id": b"legacy", b"progress": b"20", b"videos": b"['final.mp4']", b"video_subject": b"A cup of tea"}
    task = state.get_task("legacy")
    assert task["progress"] == 20
    assert task["videos"] == ["final.mp4"]
    assert task["video_subject"] == "A cup of tea"



@pytest.mark.parametrize("invalid_generation", [None, False, True, 0, -1, "1", 1.0, 1.5])
def test_redis_worker_mutations_reject_invalid_generation_tokens(invalid_generation):
    state = RedisState.__new__(RedisState)
    state._redis = _FencedFakeRedis([[]])
    state.create_task("invalid-generation-token")
    valid_generation = state.acquire_generation("invalid-generation-token")
    assert valid_generation == 1

    assert state.update_task(
        "invalid-generation-token",
        generation=invalid_generation,
        progress=99,
    ) is False
    assert state.patch_task(
        "invalid-generation-token",
        generation=invalid_generation,
        error="must not be written",
    ) is False
    stored = state.get_task("invalid-generation-token")
    assert stored["progress"] == 0
    assert "error" not in stored
