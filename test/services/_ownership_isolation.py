"""Per-test ownership isolation for HTTP tests.

Every test gets a fresh in-memory ownership store. Only the (task_id, owner)
pairs a test lists are seeded, as real ownership records. The production
``require_task_owner`` path then decides access, so a negative test (another
user, or an unowned task) gets the production 404.
"""

from datetime import UTC, datetime

import app.controllers.v1.video as video_controller
import app.security as security_package
import app.security.ownership as ownership_module
from app.security import private_materials
from app.security.ownership import InMemoryOwnershipStore, TaskOwnershipRecord

_PATCHED_NAMESPACES = (
    ownership_module,
    security_package,
    video_controller,
    private_materials,
)


def isolate_ownership(monkeypatch, owned=()) -> InMemoryOwnershipStore:
    store = InMemoryOwnershipStore()
    for task_id, owner in owned:
        store.create(
            TaskOwnershipRecord(
                task_id=task_id,
                owner_id=owner,
                created_at=datetime.now(UTC),
                kind="video",
                metadata={},
            )
        )
    for namespace in _PATCHED_NAMESPACES:
        monkeypatch.setattr(namespace, "ownership_store", store)
    return store
