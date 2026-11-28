import json
from functools import partial
from unittest.mock import MagicMock, patch

import pytest

from app.controllers.manager.redis_manager import RedisTaskManager
from app.models import const
from app.models.schema import VideoParams


def make_manager():
    client = MagicMock()
    with patch("app.controllers.manager.redis_manager.redis.Redis.from_url", return_value=client):
        manager = RedisTaskManager(1, "redis://test.invalid")
    return manager, client


def payload(task_id, **kwargs):
    return {"func": "start", "args": [], "kwargs": {"task_id": task_id, "params": VideoParams(video_subject="Tea").model_dump(warnings=False), **kwargs}}


@pytest.mark.parametrize("defect", ["retired_keyword", "missing_params", "duplicate_task_id"])
def test_signature_drift_marks_stale_task_failed_and_drains_queue(defect):
    manager, client = make_manager()
    stale = payload("stale")
    if defect == "retired_keyword":
        stale["kwargs"]["retired_option"] = True
    elif defect == "missing_params":
        del stale["kwargs"]["params"]
    else:
        stale["args"] = ["another-task"]
    client.lpop.side_effect = [json.dumps(stale), json.dumps(payload("valid"))]
    with patch("app.controllers.manager.redis_manager.sm.state") as state:
        task = manager.dequeue()
    assert task["kwargs"]["task_id"] == "valid"
    state.recovery_patch.assert_called_once()
    assert state.recovery_patch.call_args.args == ("stale",)
    assert state.recovery_patch.call_args.kwargs["state"] == const.TASK_STATE_FAILED
    assert state.recovery_patch.call_args.kwargs["failed_stage"] == "dequeue"


def test_signature_validation_accepts_supported_partial_callables():
    manager, client = make_manager()
    def accepts_request(task_id, params, stop_at="video"):
        pass
    bound = partial(accepts_request, stop_at="audio")
    client.lpop.return_value = json.dumps(payload("valid"))
    with patch.dict("app.controllers.manager.redis_manager.FUNC_MAP", {"start": bound}):
        task = manager.dequeue()
    assert task["func"] is bound
    assert isinstance(task["kwargs"]["params"], VideoParams)

def test_generation_acquisition_failure_marks_api_task_failed():
    from app.services import task as tm

    manager, client = make_manager()

    def fail_before_pipeline(task_id, _generation_handoff):
        raise tm.GenerationAcquisitionError("Redis unavailable")

    with (
        patch("app.controllers.manager.redis_manager.sm.state") as state,
        patch(
            "app.security.task_execution.authorize_task_execution",
            return_value=None,
        ),
        patch.object(manager, "_renew_slot_until_done"),
    ):
        manager._run_reserved_task(
            "reserved-slot",
            fail_before_pipeline,
            task_id="generation-unavailable",
        )

    state.recovery_patch.assert_called_once_with(
        "generation-unavailable",
        expected_generation=None,
        state=const.TASK_STATE_FAILED,
        failed_stage="generation_acquisition",
        error="GenerationAcquisitionError: Redis unavailable",
    )
    client.zrem.assert_called_once_with(manager.running_slots_key, "reserved-slot")
