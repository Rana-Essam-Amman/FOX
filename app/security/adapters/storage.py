"""Storage adapters.

Local filesystem adapter is for development and single-node deployments.
ObjectStorageAdapter is the interface for future shared storage.
Both enforce ownership before any read or delete.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import ownership_store, TaskOwnershipRecord
from app.utils import utils


class ObjectStorageAdapter:
    """Interface for future production object storage. Not implemented with a paid provider."""

    def put(self, object_name: str, content: bytes, content_type: str) -> None:
        raise NotImplementedError("object storage adapter must be supplied")

    def get(self, object_name: str) -> bytes:
        raise NotImplementedError

    def delete(self, object_name: str) -> None:
        raise NotImplementedError


class LocalFilesystemStorage:
    """Single-node adapter. Not safe for multi-worker without shared disk."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base = Path(base_dir or utils.storage_dir("materials", create=True))
        self.base.mkdir(parents=True, exist_ok=True)

    def put_owned(self, user: AuthenticatedUser, content: bytes, content_type: str, request_id: str) -> str:
        from app.security.storage import validate_upload
        validate_upload(content_type, len(content), request_id)
        material_id = uuid.uuid4().hex
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=material_id,
                owner_id=user.sub,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                kind="material",
                metadata={"content_type": content_type, "size": len(content), "storage": "local"},
            )
        )
        path = self.base / material_id
        if not str(path.resolve()).startswith(str(self.base.resolve())):
            raise HttpException(task_id=request_id, status_code=400, message="invalid object name")
        path.write_bytes(content)
        return material_id

    def get_owned(self, material_id: str, user: AuthenticatedUser, request_id: str) -> Path:
        record = ownership_store.get(material_id)
        if record is None or record.owner_id != user.sub or record.kind != "material":
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        path = self.base / material_id
        if not path.is_file() or not str(path.resolve()).startswith(str(self.base.resolve())):
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        return path
