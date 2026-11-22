"""Task admission ownership tests against the real create_task controller.

Uploads, ownership records and the resolver are real. Only the queue, the
task-state store and the rate limiter are replaced, so each test can assert
whether a request was admitted to the queue at all.
"""

import io
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from PIL import Image

from app.controllers.v1 import video as video_controller
from app.models.exception import HttpException
from app.models.schema import MaterialInfo, TaskVideoRequest
from app.security import private_materials
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import InMemoryOwnershipStore
from app.security.rate_limit import rate_limiter
from app.utils import utils

USER_A = AuthenticatedUser(sub="user-a")
USER_B = AuthenticatedUser(sub="user-b")


def _png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (255, 0, 0)).save(buffer, "PNG")
    return buffer.getvalue()


def _request():
    return SimpleNamespace(headers={"x-task-id": "req-admit"}, method="POST")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "local_videos"
    root.mkdir()
    store = InMemoryOwnershipStore()
    queue = MagicMock()
    monkeypatch.setattr(utils, "storage_dir", lambda sub_dir="", create=False: str(root))
    monkeypatch.setattr(video_controller, "ownership_store", store)
    monkeypatch.setattr(private_materials, "ownership_store", store)
    monkeypatch.setattr(video_controller, "task_manager", queue)
    monkeypatch.setattr(video_controller.sm, "state", MagicMock())
    monkeypatch.setattr(rate_limiter, "check_request", lambda *a, **k: None)
    monkeypatch.setattr(rate_limiter, "check_generation", lambda *a, **k: None)
    return SimpleNamespace(root=root, store=store, queue=queue)


def _upload(user):
    upload = UploadFile(file=io.BytesIO(_png_bytes()), filename="photo.png")
    return video_controller.upload_video_material_file(_request(), file=upload, user=user)["data"]["file"]


def _submit(body, user):
    return video_controller.create_task(_request(), body, "video", user=user)


def _admitted_params(env):
    assert env.queue.add_task.call_count == 1
    return env.queue.add_task.call_args.kwargs["params"]


def _assert_rejected(env, body, user, status=404):
    with pytest.raises(HttpException) as excinfo:
        _submit(body, user)
    assert excinfo.value.status_code == status
    env.queue.add_task.assert_not_called()


def test_owner_admits_own_material_id(env):
    stored = _upload(USER_A)

    _submit(TaskVideoRequest(video_subject="s", material_id=stored), USER_A)

    params = _admitted_params(env)
    assert params.video_source == "local"
    assert [(m.provider, m.url) for m in params.video_materials] == [("local", stored)]


def test_other_user_cannot_admit_material_id(env):
    stored = _upload(USER_A)

    _assert_rejected(env, TaskVideoRequest(video_subject="s", material_id=stored), USER_B)


def test_other_user_cannot_admit_owner_file_under_remote_provider_label(env):
    stored = _upload(USER_A)
    body = TaskVideoRequest(
        video_subject="s",
        video_source="local",
        video_materials=[MaterialInfo(provider="pexels", url=stored)],
    )

    _assert_rejected(env, body, USER_B)


def test_mixed_owned_and_foreign_references_are_rejected_as_a_whole(env):
    own = _upload(USER_B)
    foreign = _upload(USER_A)
    body = TaskVideoRequest(
        video_subject="s",
        video_source="local",
        video_materials=[
            MaterialInfo(provider="local", url=own),
            MaterialInfo(provider="local", url=foreign),
        ],
    )

    _assert_rejected(env, body, USER_B)


@pytest.mark.parametrize("make_reference", [
    lambda root, stored: str(root / stored),
    lambda root, stored: "../" + stored,
    lambda root, stored: stored.upper(),
])
def test_absolute_traversal_and_malformed_references_are_rejected(env, make_reference):
    stored = _upload(USER_A)
    body = TaskVideoRequest(
        video_subject="s",
        video_source="local",
        video_materials=[MaterialInfo(provider="local", url=make_reference(env.root, stored))],
    )

    _assert_rejected(env, body, USER_A)


def test_unowned_legacy_file_reference_is_rejected(env):
    legacy_name = f"{uuid.uuid4().hex}.mp4"
    (env.root / legacy_name).write_bytes(b"legacy")
    body = TaskVideoRequest(
        video_subject="s",
        video_source="local",
        video_materials=[MaterialInfo(provider="local", url=legacy_name)],
    )

    _assert_rejected(env, body, USER_A)


def test_material_id_cannot_be_combined_with_video_materials(env):
    own = _upload(USER_A)
    body = TaskVideoRequest(
        video_subject="s",
        material_id=own,
        video_materials=[MaterialInfo(provider="local", url=own)],
    )

    _assert_rejected(env, body, USER_A, status=400)


def test_remote_source_drops_video_materials_without_admitting_them(env):
    foreign = _upload(USER_A)
    body = TaskVideoRequest(
        video_subject="s",
        video_source="pexels",
        video_materials=[MaterialInfo(provider="local", url=foreign)],
    )

    _submit(body, USER_B)

    assert _admitted_params(env).video_materials is None
