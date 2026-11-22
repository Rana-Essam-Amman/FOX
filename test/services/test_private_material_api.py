"""Endpoint-level ownership tests for private material upload, listing and deletion.

These call the real controller functions with an explicit authenticated user,
the real InMemoryOwnershipStore, the real image validation service, and a real
temporary storage directory. Only the storage root and the store instance are
redirected to the temporary location.
"""

import io
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from PIL import Image

from app.controllers.v1 import video as video_controller
from app.models.exception import HttpException
from app.security import private_materials
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import InMemoryOwnershipStore
from app.utils import utils

USER_A = AuthenticatedUser(sub="user-a")
USER_B = AuthenticatedUser(sub="user-b")


def _png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (255, 0, 0)).save(buffer, "PNG")
    return buffer.getvalue()


def _request(task_id="req-1"):
    return SimpleNamespace(headers={"x-task-id": task_id}, method="POST")


def _upload_file(filename="photo.png"):
    return UploadFile(file=io.BytesIO(_png_bytes()), filename=filename)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "local_videos"
    root.mkdir()
    store = InMemoryOwnershipStore()
    monkeypatch.setattr(utils, "storage_dir", lambda sub_dir="", create=False: str(root))
    monkeypatch.setattr(video_controller, "ownership_store", store)
    monkeypatch.setattr(private_materials, "ownership_store", store)
    return SimpleNamespace(root=root, store=store)


def _listed(env, user):
    response = video_controller.get_video_materials_list(_request(), user=user)
    return response["data"]["files"]


def test_owner_lists_own_upload_and_other_user_does_not(env):
    stored = video_controller.upload_video_material_file(
        _request(), file=_upload_file(), user=USER_A
    )["data"]["file"]

    owned = _listed(env, USER_A)
    assert [(item["name"], item["file"]) for item in owned] == [("photo.png", stored)]
    assert _listed(env, USER_B) == []


def test_unowned_legacy_file_is_never_listed(env):
    (env.root / "legacy.mp4").write_bytes(b"legacy")

    assert _listed(env, USER_A) == []
    assert _listed(env, USER_B) == []
    assert (env.root / "legacy.mp4").read_bytes() == b"legacy"


def test_materials_endpoint_uses_same_ownership_as_legacy_listing(env):
    material_id = video_controller.upload_material(
        _request(), file=_upload_file(), user=USER_A
    )["data"]["material_id"]

    assert [item["file"] for item in _listed(env, USER_A)] == [material_id]
    listed_b = video_controller.list_materials(_request(), user=USER_B)["data"]["materials"]
    assert listed_b == []


def test_failed_ownership_persistence_leaves_no_accessible_upload(env, monkeypatch):
    def fail_create(record):
        raise RuntimeError("ownership store unavailable")

    monkeypatch.setattr(env.store, "create", fail_create)

    with pytest.raises(RuntimeError):
        video_controller.upload_video_material_file(_request(), file=_upload_file(), user=USER_A)

    assert list(env.root.iterdir()) == []
    assert _listed(env, USER_A) == []


def test_other_user_cannot_delete_material_by_exact_id(env):
    stored = video_controller.upload_video_material_file(
        _request(), file=_upload_file(), user=USER_A
    )["data"]["file"]

    with pytest.raises(HttpException) as excinfo:
        video_controller.delete_material(_request(), material_id=stored, user=USER_B)

    assert excinfo.value.status_code == 404
    assert (env.root / stored).is_file()
    assert [item["file"] for item in _listed(env, USER_A)] == [stored]


def test_owner_delete_removes_file_and_listing_entry(env):
    stored = video_controller.upload_video_material_file(
        _request(), file=_upload_file(), user=USER_A
    )["data"]["file"]

    video_controller.delete_material(_request(), material_id=stored, user=USER_A)

    assert not (env.root / stored).exists()
    assert _listed(env, USER_A) == []
