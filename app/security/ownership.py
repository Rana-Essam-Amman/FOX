"""Persistent task ownership records.

Ownership is immutable after creation. Task IDs alone never grant access.
The production adapter must use durable storage that survives process restart
and is shared across workers. The in-memory adapter is for tests only.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.runtime import create_ownership_store


@dataclass(frozen=True)
class TaskOwnershipRecord:
    task_id: str
    owner_id: str
    created_at: datetime
    kind: str
    metadata: dict[str, Any]


class TaskOwnershipStore(ABC):
    @abstractmethod
    def create(self, record: TaskOwnershipRecord) -> None:
        """Create an ownership record. Must fail if task_id already exists."""

    @abstractmethod
    def get(self, task_id: str) -> TaskOwnershipRecord | None:
        ...

    @abstractmethod
    def list_for_owner(self, owner_id: str, limit: int = 100) -> list[TaskOwnershipRecord]:
        ...

    @abstractmethod
    def delete(self, task_id: str, owner_id: str) -> bool:
        """Delete only if the caller is the owner. Returns True on success."""


class InMemoryOwnershipStore(TaskOwnershipStore):
    """Test-only adapter. Not safe for multi-worker production."""

    def __init__(self) -> None:
        self._records: dict[str, TaskOwnershipRecord] = {}
        self._lock = threading.RLock()

    def create(self, record: TaskOwnershipRecord) -> None:
        with self._lock:
            if record.task_id in self._records:
                raise ValueError(f"task {record.task_id} already owned")
            self._records[record.task_id] = record

    def get(self, task_id: str) -> TaskOwnershipRecord | None:
        with self._lock:
            return self._records.get(task_id)

    def list_for_owner(self, owner_id: str, limit: int = 100) -> list[TaskOwnershipRecord]:
        with self._lock:
            owned = [r for r in self._records.values() if r.owner_id == owner_id]
            owned.sort(key=lambda r: r.created_at, reverse=True)
            return owned[:limit]

    def delete(self, task_id: str, owner_id: str) -> bool:
        with self._lock:
            record = self._records.get(task_id)
            if record is None or record.owner_id != owner_id:
                return False
            del self._records[task_id]
            return True


ownership_store: TaskOwnershipStore = create_ownership_store()

# These are the only task kinds admitted by the authenticated task endpoints.
# Material records share the same ownership table but are not task resources.
TASK_OWNERSHIP_KINDS = frozenset({"video", "subtitle", "audio"})


def require_task_owner(task_id: str, user: AuthenticatedUser) -> TaskOwnershipRecord:
    record = ownership_store.get(task_id)
    if record is None:
        raise HttpException(
            task_id=task_id, status_code=404, message="task not found"
        )
    if record.owner_id != user.sub or record.kind not in TASK_OWNERSHIP_KINDS:
        raise HttpException(
            task_id=task_id, status_code=404, message="task not found"
        )
    return record
