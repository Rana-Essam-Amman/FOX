"""Owner-scoped private background-music records.

User-uploaded BGM is stored in a shared directory for single-host
compatibility, but it is only visible through an ownership record created
by the authenticated principal at upload time. Built-in preset songs live
in the resource directory and are not ownership records. Files in the
upload directory without an ownership record are legacy/unowned and are
never listed to ordinary users.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from loguru import logger

from app.security.ownership import TaskOwnershipRecord, ownership_store
from app.utils import file_security

BGM_KIND = "bgm"
_LISTING_LIMIT = 200


def record_owned_bgm(
    stored_path: str,
    stored_filename: str,
    original_filename: str,
    owner_id: str,
    request_id: str,
) -> None:
    """Persist ownership for a BGM file that was just written.

    If the ownership record cannot be created, only the file this request
    just wrote is removed, so no accessible unowned copy is left behind.
    """
    try:
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=stored_filename,
                owner_id=owner_id,
                created_at=datetime.now(timezone.utc),
                kind=BGM_KIND,
                metadata={"filename": original_filename, "request_id": request_id},
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
            f"failed to clean background music after ownership failure, "
            f"request_id={request_id}, file={stored_filename}: {cleanup_exc}"
        )


def list_owned_bgm(owner_id: str, storage_dir: str) -> list[dict]:
    """Return only BGM the owner has a valid record for, sorted by name.

    Display name comes from ownership metadata; the selectable file key is
    the immutable stored filename. Missing or out-of-directory files are
    skipped rather than leaked.
    """
    entries: list[dict] = []
    for record in ownership_store.list_for_owner(owner_id, limit=_LISTING_LIMIT):
        if record.kind != BGM_KIND:
            continue
        try:
            path = file_security.resolve_path_within_directory(
                storage_dir, record.task_id
            )
            if not os.path.isfile(path):
                continue
            size = os.path.getsize(path)
        except (ValueError, OSError):
            continue
        name = (record.metadata or {}).get("filename") or record.task_id
        entries.append({"name": name, "size": size, "file": record.task_id})
    entries.sort(key=lambda item: (item["name"].casefold(), item["name"]))
    return entries


def get_video_task_owner(task_id: str | None) -> str | None:
    """Return the authenticated owner recorded for a video task.

    Workers receive a task identifier, not a caller-supplied owner ID. Resolve
    the principal from the immutable ownership record created before enqueue.
    """
    if not task_id:
        return None
    record = ownership_store.get(task_id)
    if record is None or record.kind != "video":
        return None
    return record.owner_id


def resolve_owned_bgm(
    owner_id: str | None, filename: str, storage_dir: str
) -> str | None:
    """Resolve an uploaded BGM only when its immutable record belongs to owner."""
    if (
        not owner_id
        or not filename
        or not isinstance(filename, str)
        or filename != os.path.basename(filename)
    ):
        return None
    record = ownership_store.get(filename)
    if record is None or record.kind != BGM_KIND or record.owner_id != owner_id:
        return None
    try:
        resolved_path = file_security.resolve_path_within_directory(
            storage_dir, filename
        )
    except (ValueError, OSError):
        return None
    return resolved_path if os.path.isfile(resolved_path) else None
