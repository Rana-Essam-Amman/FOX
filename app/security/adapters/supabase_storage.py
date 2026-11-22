"""Supabase Storage adapter with real HTTP operations.

Uploads to the private fox-media bucket using the service-role key.
Generates signed URLs via the Supabase signing endpoint.
Ownership is recorded first and rolled back on upload failure.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import requests

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import ownership_store, TaskOwnershipRecord
from app.security.storage import validate_upload, MAX_UPLOAD_BYTES


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
        validate_upload(content_type, len(content), request_id)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HttpException(
                task_id=request_id,
                status_code=400,
                message=f"file exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
            )
        material_id = uuid.uuid4().hex
        object_name = f"{user.sub}/{material_id}"
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=material_id,
                owner_id=user.sub,
                created_at=datetime.now(timezone.utc),
                kind="material",
                metadata={
                    "content_type": content_type,
                    "size": len(content),
                    "bucket": self.bucket,
                    "object": object_name,
                },
            )
        )
        try:
            resp = requests.post(
                f"{self.url}/storage/v1/object/{self.bucket}/{object_name}",
                headers={
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
                data=content,
                timeout=30,
            )
            resp.raise_for_status()
        except Exception:
            ownership_store.delete(material_id, user.sub)
            raise HttpException(
                task_id=request_id,
                status_code=502,
                message="storage upload failed",
            )
        return material_id

    def get_signed_url(
        self,
        material_id: str,
        user: AuthenticatedUser,
        request_id: str,
        expires_in: int = 60,
    ) -> str:
        record = ownership_store.get(material_id)
        if record is None or record.owner_id != user.sub or record.kind != "material":
            raise HttpException(task_id=request_id, status_code=404, message="material not found")
        object_name = record.metadata.get("object", material_id)
        try:
            resp = requests.post(
                f"{self.url}/storage/v1/object/sign/{self.bucket}/{object_name}",
                headers={
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                },
                json={"expiresIn": expires_in},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            signed = data.get("signedURL") or data.get("signedUrl")
            if not signed:
                raise ValueError("missing signedURL in response")
            return signed if signed.startswith("http") else f"{self.url}{signed}"
        except Exception as exc:
            raise HttpException(
                task_id=request_id,
                status_code=502,
                message="signed URL generation failed",
            ) from exc
