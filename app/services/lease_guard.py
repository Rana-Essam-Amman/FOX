"""Dependency-light lease-loss guard.

Used by task.py and tests. No heavy imports.
"""

import contextvars
from typing import Callable

lease_lost_event: contextvars.ContextVar = contextvars.ContextVar("lease_lost_event", default=None)


def lease_lost() -> bool:
    """Return True if the current execution's lease has been lost."""
    lost = lease_lost_event.get()
    return lost is not None and lost.is_set()


def check_lease_or_abort(
    task_id: str,
    stage: str,
    cleanup: Callable[[str, int], None] | None = None,
    task_dir: Callable[[str], str] | None = None,
    current_generation: int | None = None,
) -> bool:
    """Cooperative lease check. Returns True if the worker should abort.

    Does not mark the task FAILED. Optionally cleans up only the current
    generation's private artifacts via the supplied cleanup callable.
    """
    if not lease_lost():
        return False
    if cleanup is not None and task_dir is not None and current_generation is not None:
        cleanup(task_dir(task_id), current_generation)
    return True
