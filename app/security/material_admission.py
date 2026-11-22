"""Admission-time validation of local material references for video tasks.

Every local reference a client submits is resolved against the authenticated
owner before a task can be queued. For a local source the pipeline reads every
entry as a local file path regardless of its provider label, so every entry is
validated and normalized to provider "local". For other sources the pipeline
never reads video_materials, so the list is dropped instead of interpreted.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models.schema import MaterialInfo
from app.security.material_resolution import OwnershipLookup, resolve_owned_material


class MaterialAdmissionError(ValueError):
    """The request combines material sources in an unsupported way."""


def admit_video_materials(
    *,
    video_source: str | None,
    material_id: str | None,
    materials: Sequence[MaterialInfo] | None,
    owner_id: str,
    storage_dir: str,
    lookup: OwnershipLookup,
) -> tuple[str | None, list[MaterialInfo] | None]:
    """Return the (video_source, video_materials) pair safe to queue.

    Raises MaterialNotFound if any local reference is unknown, foreign-owned,
    unowned, or not a bare stored filename. Admission is all-or-nothing.
    """
    if material_id:
        if materials:
            raise MaterialAdmissionError(
                "material_id cannot be combined with video_materials"
            )
        stored = _admit_reference(material_id, owner_id, storage_dir, lookup)
        return "local", [MaterialInfo(provider="local", url=stored)]
    if video_source != "local":
        return video_source, None
    admitted = [
        MaterialInfo(
            provider="local",
            url=_admit_reference(item.url, owner_id, storage_dir, lookup),
            duration=item.duration,
        )
        for item in materials or []
    ]
    return video_source, admitted


def _admit_reference(
    reference: str,
    owner_id: str,
    storage_dir: str,
    lookup: OwnershipLookup,
) -> str:
    resolve_owned_material(
        reference, owner_id=owner_id, lookup=lookup, storage_dir=storage_dir
    )
    # The reference is a validated bare stored filename; return it unchanged.
    return reference
