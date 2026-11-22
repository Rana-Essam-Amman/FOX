"""Ownership-aware storage for uploads and generated results.

Client-supplied filenames are never trusted. Object names are generated
server-side. Access always requires the authenticated owner.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import ownership_store, TaskOwnershipRecord
from app.utils import utils


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # Supabase Free tier maximum


def safe_object_name(prefix: str, extension: str) -> str:
    clean_ext = extension.lower().lstrip(".")
    if not clean_ext or "/" in clean_ext or "\\" in clean_ext:
        clean_ext = "bin"
    return f"{prefix}/{uuid.uuid4().hex}.{clean_ext}"


def validate_upload(content_type: str | None, size: int, request_id: str) -> None:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message="unsupported content type",
        )
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message="invalid or oversized upload",
        )


def store_owned_material(
    user: AuthenticatedUser,
    content: bytes,
    content_type: str,
    request_id: str,
) -> str:
    """Store an upload and return a materialId owned by the user."""
    validate_upload(content_type, len(content), request_id)
    material_id = uuid.uuid4().hex
    ownership_store.create(
        TaskOwnershipRecord(
            task_id=material_id,
            owner_id=user.sub,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            kind="material",
            metadata={"content_type": content_type, "size": len(content)},
        )
    )
    materials_dir = Path(utils.storage_dir("materials", create=True))
    path = materials_dir / material_id
    path.write_bytes(content)
    return material_id


def retrieve_owned_material(material_id: str, user: AuthenticatedUser, request_id: str) -> Path:
    record = ownership_store.get(material_id)
    if record is None or record.owner_id != user.sub or record.kind != "material":
        raise HttpException(task_id=request_id, status_code=404, message="material not found")
    path = Path(utils.storage_dir("materials")) / material_id
    if not path.is_file():
        raise HttpException(task_id=request_id, status_code=404, message="material not found")
    return path
