"""Authoritative resolution of client-supplied local material references.

A client may name a material only by the server-issued stored filename that
the ownership store recorded for the authenticated principal. Absolute paths,
relative paths, separators and traversal sequences are never accepted from a
client. Every failure raises the same MaterialNotFound error so callers cannot
distinguish "missing" from "owned by someone else".
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Protocol, TypeGuard

from app.utils.file_security import resolve_path_within_directory

# Stored names are issued by save_material_upload as uuid4().hex + extension.
_STORED_NAME_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")


class MaterialNotFound(Exception):
    """Raised for any reference that is not an owned, stored material."""


class OwnershipRecordLike(Protocol):
    owner_id: str
    kind: str


OwnershipLookup = Callable[[str], OwnershipRecordLike | None]


def is_stored_material_name(name: object) -> TypeGuard[str]:
    return isinstance(name, str) and _STORED_NAME_RE.fullmatch(name) is not None


def resolve_owned_material(
    reference: object,
    *,
    owner_id: str,
    lookup: OwnershipLookup,
    storage_dir: str,
) -> str:
    """Return the absolute path of a stored material owned by owner_id.

    Raises MaterialNotFound for malformed references, unknown ids, records
    owned by another principal, non-material records, escaping paths and
    missing files alike.
    """
    if not owner_id or not is_stored_material_name(reference):
        raise MaterialNotFound("material not found")
    record = lookup(reference)
    if record is None or record.kind != "material" or record.owner_id != owner_id:
        raise MaterialNotFound("material not found")
    try:
        path = resolve_path_within_directory(storage_dir, os.path.basename(reference))
    except ValueError as exc:
        raise MaterialNotFound("material not found") from exc
    return path
