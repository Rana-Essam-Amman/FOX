"""Worker-side authorization of a queued task's ownership.

The worker never trusts the queued payload, task parameters or its own process
identity. It re-reads the durable ownership record by task ID and accepts it
only if the record is internally consistent. Any inconsistency, missing record
or failing lookup denies execution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.security.owner_namespaces import (
    KNOWN_POLICIES,
    POLICY_USER,
    internal_owner_for_policy,
    is_reserved_owner,
)


class ExecutionDenied(Exception):
    """The task's durable ownership does not authorize execution."""


class OwnershipRecordLike(Protocol):
    task_id: str
    owner_id: str
    kind: str
    metadata: dict[str, Any] | None


@dataclass(frozen=True)
class TaskExecutionGrant:
    task_id: str
    owner_id: str
    policy: str


TaskLookup = Callable[[str], OwnershipRecordLike | None]


def authorize_task_execution(
    task_id: object,
    *,
    expected_kind: str,
    lookup: TaskLookup,
) -> TaskExecutionGrant:
    """Return the grant for a task, or raise ExecutionDenied.

    Lookup exceptions are not caught here: an unavailable ownership store must
    surface to the caller, which then fails the task without touching material.
    """
    if not isinstance(task_id, str) or not task_id:
        raise ExecutionDenied("task identifier is malformed")
    record = lookup(task_id)
    if record is None:
        raise ExecutionDenied("task ownership record is missing")
    if record.task_id != task_id:
        raise ExecutionDenied("task ownership record does not match task")
    if record.kind != expected_kind:
        raise ExecutionDenied("task ownership kind does not match execution")
    metadata = record.metadata or {}
    policy = metadata.get("policy")
    if policy not in KNOWN_POLICIES:
        raise ExecutionDenied("task ownership policy is missing or unknown")
    owner_id = record.owner_id
    if not isinstance(owner_id, str) or not owner_id:
        raise ExecutionDenied("task owner is missing")
    if policy == POLICY_USER:
        if is_reserved_owner(owner_id):
            raise ExecutionDenied("user task uses a reserved owner namespace")
    elif owner_id != internal_owner_for_policy(policy):
        raise ExecutionDenied("internal task owner does not match its policy")
    return TaskExecutionGrant(task_id=task_id, owner_id=owner_id, policy=policy)
