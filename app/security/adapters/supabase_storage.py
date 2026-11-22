"""Supabase Storage adapter interface.

Uses the Supabase Storage REST API with a service-role key held only on the server.
Private buckets. Ownership is recorded in task_ownership. No public access by default.
Compatible with the free tier (1 GB storage, 50 MB max upload).
"""

from __future__ import annotations

import os
import uuid

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import ownership_store, TaskOwnershipRecord


class SupabaseStorageAdapter:
    def __init__(
        self,
        url: str | None = None,
        service_key: str | None = None,
        bucket: str = "fox-media",
    ) -> None:
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.bucket = bucket
        if not self.url or not self.service_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    def put_owned(
        self,
        user: AuthenticatedUser,
        content: bytes,
        content_type: str,
        request_id: str,
    ) -> str:
        from app.security.storage import validate_upload
        validate_upload(content_type, len(content), request_id)
        if len(content) > 50 * 1024 * 1024:
            raise HttpException(task_id=request_id, status_code=400, message="file exceeds 50 MB free-tier limit")
        material_id = uuid.uuid4().hex
        object_name = f"{user.sub}/{material_id}"
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=material_id,
                owner_id=user.sub,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                kind="material",
                metadata={"content_type": content_type, "size": len(content), "bucket": self.bucket, "object": object_name},
            )
        )
        return material_id

    def get_signed_url(self, material_id: str, user: AuthenticatedUser, request_id: str, expires_in: int = 60) -> str:
        record = ownership_store.get(material_id)
        if record is None or record.owner_id != user.sub or record.kind != "material":
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        return f"{self.url}/storage/v1/object/sign/{self.bucket}/{record.metadata.get('object', material_id)}?expires={expires_in}"
