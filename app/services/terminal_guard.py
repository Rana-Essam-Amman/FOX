"""Dependency-light terminal-state transition helpers.

Used by task.py and tests. No heavy imports.
"""

from app.services.lease_guard import check_lease_or_abort


def complete_if_owner(state, task_id: str, **kwargs) -> bool:
    """Mark COMPLETE only if we still own the lease and generation.

    Returns True only if the state backend confirms the write succeeded.
    """
    if check_lease_or_abort(task_id, "complete"):
        return False
    result = state.update_task(task_id, state=1, progress=100, **kwargs)  # 1 = COMPLETE
    return bool(result)


def mark_failed_if_owner(state, task_id: str, stage: str, error: str, **kwargs) -> dict:
    """Mark FAILED only if we still own the lease and generation.

    Returns the task dict on success, or a rejection marker on failure.
    """
    if check_lease_or_abort(task_id, f"mark-failed:{stage}"):
        return {"task_id": task_id, "state": None, "lease_lost": True}
    fields = {"state": -1, "failed_stage": stage, "error": error, **kwargs}  # -1 = FAILED
    try:
        ok = bool(state.update_task(task_id, **fields))
        if not ok:
            ok = bool(state.patch_task(task_id, **fields))
        if not ok:
            return {"task_id": task_id, "state": None, "write_rejected": True}
    except Exception:
        return {"task_id": task_id, "state": None, "write_rejected": True}
    return state.get_task(task_id) or fields
