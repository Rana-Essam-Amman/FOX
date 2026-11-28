"""Storage adapters.

Object storage is deliberately independent of ownership metadata. Callers must
authorize an object through the ownership store before reading or deleting it.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator, Protocol

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import ownership_store, TaskOwnershipRecord
from app.utils import utils


@dataclass(frozen=True)
class StoredObjectInfo:
    """Provider-neutral metadata needed to serve or validate a stored object."""

    size: int
    last_modified_ns: int


class ObjectStorageAdapter(Protocol):
    """Streaming object operations; ownership checks remain outside this adapter."""

    def put_stream(
        self, object_name: str, source: BinaryIO, expected_size: int | None = None
    ) -> StoredObjectInfo: ...

    def head(self, object_name: str) -> StoredObjectInfo: ...

    def iter_read(
        self,
        object_name: str,
        start: int = 0,
        end: int | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]: ...

    def delete(self, object_name: str) -> None: ...


class LocalFilesystemStorage:
    """Single-node object adapter. Not shared across hosts without shared disk."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base = Path(base_dir or utils.storage_dir("materials", create=True))
        self.base.mkdir(parents=True, exist_ok=True)
        self._base_resolved = self.base.resolve()

    def _object_path(self, object_name: str) -> Path:
        if (
            not isinstance(object_name, str)
            or not object_name
            or "\\" in object_name
            or "\x00" in object_name
            or object_name.startswith("/")
        ):
            raise ValueError("invalid object name")
        parts = object_name.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("invalid object name")
        path = self.base.joinpath(*parts)
        if not path.resolve().is_relative_to(self._base_resolved):
            raise ValueError("invalid object name")
        return path

    def put_stream(
        self, object_name: str, source: BinaryIO, expected_size: int | None = None
    ) -> StoredObjectInfo:
        if expected_size is not None and expected_size < 0:
            raise ValueError("expected_size must be non-negative")
        target = self._object_path(object_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".fox-upload-", dir=target.parent
        )
        total = 0
        try:
            with os.fdopen(descriptor, "wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise TypeError("object source must be binary")
                    total += len(chunk)
                    if expected_size is not None and total > expected_size:
                        raise ValueError("object exceeds expected size")
                    output.write(chunk)
                if expected_size is not None and total != expected_size:
                    raise ValueError("object size does not match expected size")
                output.flush()
                os.fsync(output.fileno())
            # Same-directory hard-link publication is atomic and refuses to
            # overwrite an immutable object key that already exists.
            os.link(temporary_name, target)
            return self.head(object_name)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

    def head(self, object_name: str) -> StoredObjectInfo:
        stat_result = self._object_path(object_name).stat()
        if not self._object_path(object_name).is_file():
            raise FileNotFoundError(object_name)
        return StoredObjectInfo(
            size=stat_result.st_size,
            last_modified_ns=stat_result.st_mtime_ns,
        )

    def iter_read(
        self,
        object_name: str,
        start: int = 0,
        end: int | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        if start < 0 or chunk_size <= 0 or (end is not None and end < start):
            raise ValueError("invalid object byte range")
        path = self._object_path(object_name)
        size = path.stat().st_size
        if start >= size:
            raise ValueError("object byte range is not satisfiable")
        final_byte = size - 1 if end is None else min(end, size - 1)
        remaining = final_byte - start + 1

        def read_chunks() -> Iterator[bytes]:
            with path.open("rb") as source:
                source.seek(start)
                bytes_left = remaining
                while bytes_left:
                    chunk = source.read(min(chunk_size, bytes_left))
                    if not chunk:
                        break
                    bytes_left -= len(chunk)
                    yield chunk

        return read_chunks()

    def delete(self, object_name: str) -> None:
        self._object_path(object_name).unlink(missing_ok=True)

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
        path = self._object_path(material_id)
        path.write_bytes(content)
        return material_id

    def get_owned(self, material_id: str, user: AuthenticatedUser, request_id: str) -> Path:
        record = ownership_store.get(material_id)
        if record is None or record.owner_id != user.sub or record.kind != "material":
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        path = self._object_path(material_id)
        if not path.is_file():
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        return path
