"""Owner-scoped private material records shared by every upload and listing path.

A stored material file is only visible through an ownership record created by
the authenticated principal at upload time. Files in the shared storage
directory without such a record are legacy/unowned and are never listed or
served to ordinary users.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from loguru import logger

from app.security.material_resolution import MaterialNotFound, resolve_owned_material
from app.security.ownership import TaskOwnershipRecord, ownership_store

MATERIAL_KIND = "material"
_LISTING_LIMIT = 200


def record_owned_material(
    stored_path: str,
    stored_filename: str,
    safe_filename: str,
    owner_id: str,
    request_id: str,
) -> None:
    """Persist ownership for a file that was just written.

    If the ownership record cannot be created, only the file this request
    just wrote is removed, so no accessible unowned copy is left behind.
    """
    try:
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=stored_filename,
                owner_id=owner_id,
                created_at=datetime.now(timezone.utc),
                kind=MATERIAL_KIND,
                metadata={"filename": safe_filename, "request_id": request_id},
            )
        )
    except Exception:
        _remove_unrecorded_file(stored_path, stored_filename, request_id)
        raise


def _remove_unrecorded_file(stored_path: str, stored_filename: str, request_id: str) -> None:
    if not os.path.isfile(stored_path):
        return
    try:
        os.remove(stored_path)
    except OSError as cleanup_exc:
        logger.error(
            f"failed to clean material file after ownership failure, "
            f"request_id={request_id}, material={stored_filename}: {cleanup_exc}"
        )


def list_owned_materials(owner_id: str, storage_dir: str) -> list[dict]:
    """Return only materials the owner has a valid record for, sorted by name."""
    entries: list[dict] = []
    for record in ownership_store.list_for_owner(owner_id, limit=_LISTING_LIMIT):
        if record.kind != MATERIAL_KIND:
            continue
        try:
            path = resolve_owned_material(
                record.task_id,
                owner_id=owner_id,
                lookup=ownership_store.get,
                storage_dir=storage_dir,
            )
            size = os.path.getsize(path)
        except (MaterialNotFound, OSError):
            continue
        name = (record.metadata or {}).get("filename") or record.task_id
        entries.append({"name": name, "size": size, "file": record.task_id})
    entries.sort(key=lambda item: (item["name"].casefold(), item["name"]))
    return entries
