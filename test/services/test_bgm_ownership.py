"""Regression: user-uploaded BGM is owner-scoped.

User A must not see, list, or have a selectable reference to User B's
uploaded background music. Built-in presets remain visible to both.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from app.security.ownership import TaskOwnershipRecord
from app.security.private_bgm import BGM_KIND, list_owned_bgm, record_owned_bgm
from test.services._ownership_isolation import isolate_ownership


class _User:
    def __init__(self, sub: str):
        self.sub = sub


def test_owned_bgm_is_not_visible_to_another_user(tmp_path, monkeypatch):
    store = isolate_ownership(monkeypatch)
    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    owned_name = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.mp3"
    foreign_name = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.mp3"
    (upload_dir / owned_name).write_bytes(b"owner-audio")
    (upload_dir / foreign_name).write_bytes(b"foreign-audio")

    now = datetime.now(UTC)
    store.create(
        TaskOwnershipRecord(
            task_id=owned_name,
            owner_id="user-a",
            created_at=now,
            kind=BGM_KIND,
            metadata={"filename": "mine.mp3"},
        )
    )
    store.create(
        TaskOwnershipRecord(
            task_id=foreign_name,
            owner_id="user-b",
            created_at=now,
            kind=BGM_KIND,
            metadata={"filename": "theirs.mp3"},
        )
    )

    visible = list_owned_bgm("user-a", str(upload_dir))
    files = {item["file"] for item in visible}
    assert owned_name in files
    assert foreign_name not in files
    assert all(item["name"] != "theirs.mp3" for item in visible)


def test_record_owned_bgm_removes_file_if_ownership_persistence_fails(
    tmp_path, monkeypatch
):
    isolate_ownership(monkeypatch)
    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    stored_name = "cccccccccccccccccccccccccccccccc.mp3"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(b"audio")

    import app.security.private_bgm as private_bgm

    class _FailingStore:
        def create(self, record):
            raise RuntimeError("ownership store unavailable")

    monkeypatch.setattr(private_bgm, "ownership_store", _FailingStore())

    try:
        record_owned_bgm(
            str(stored_path), stored_name, "upload.mp3", "user-a", "req-1"
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("ownership failure must propagate")

    assert not stored_path.exists()


def test_list_owned_bgm_skips_unowned_files_in_shared_directory(tmp_path, monkeypatch):
    isolate_ownership(monkeypatch)
    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    (upload_dir / "legacy.mp3").write_bytes(b"legacy")
    visible = list_owned_bgm("user-a", str(upload_dir))
    assert visible == []
    assert os.path.isfile(upload_dir / "legacy.mp3")


def test_video_task_cannot_select_another_users_bgm(tmp_path, monkeypatch):
    store = isolate_ownership(monkeypatch)
    import app.services.video as video
    import app.services.bgm as bgm_service

    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    foreign_name = "dddddddddddddddddddddddddddddddd.mp3"
    (upload_dir / foreign_name).write_bytes(b"foreign-audio")
    now = datetime.now(UTC)
    store.create(
        TaskOwnershipRecord(
            task_id="video-task-a",
            owner_id="user-a",
            created_at=now,
            kind="video",
            metadata={},
        )
    )
    store.create(
        TaskOwnershipRecord(
            task_id=foreign_name,
            owner_id="user-b",
            created_at=now,
            kind=BGM_KIND,
            metadata={"filename": "theirs.mp3"},
        )
    )
    monkeypatch.setattr(bgm_service, "uploaded_bgm_dir", lambda: str(upload_dir))
    monkeypatch.setattr(
        bgm_service,
        "resolve_builtin_bgm_file",
        lambda filename: (_ for _ in ()).throw(ValueError("not a preset")),
    )

    assert video.get_bgm_file(
        bgm_type="custom", bgm_file=foreign_name, task_id="video-task-a"
    ) == ""


def test_video_task_can_select_its_own_bgm_and_builtin_preset(
    tmp_path, monkeypatch
):
    store = isolate_ownership(monkeypatch)
    import app.services.video as video
    import app.services.bgm as bgm_service

    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    owned_name = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee.mp3"
    owned_path = upload_dir / owned_name
    owned_path.write_bytes(b"owner-audio")
    now = datetime.now(UTC)
    store.create(
        TaskOwnershipRecord(
            task_id="video-task-a",
            owner_id="user-a",
            created_at=now,
            kind="video",
            metadata={},
        )
    )
    store.create(
        TaskOwnershipRecord(
            task_id=owned_name,
            owner_id="user-a",
            created_at=now,
            kind=BGM_KIND,
            metadata={"filename": "mine.mp3"},
        )
    )
    monkeypatch.setattr(bgm_service, "uploaded_bgm_dir", lambda: str(upload_dir))
    monkeypatch.setattr(
        bgm_service,
        "resolve_builtin_bgm_file",
        lambda filename: "/presets/" + filename,
    )

    assert video.get_bgm_file(
        bgm_type="custom", bgm_file=owned_name, task_id="video-task-a"
    ) == str(owned_path)
    assert video.get_bgm_file(
        bgm_type="custom", bgm_file="preset.mp3", task_id="video-task-a"
    ) == "/presets/preset.mp3"


def test_random_bgm_uses_only_builtin_and_current_owner_uploads(
    tmp_path, monkeypatch
):
    store = isolate_ownership(monkeypatch)
    import app.services.video as video
    import app.services.bgm as bgm_service

    upload_dir = tmp_path / "bgm"
    upload_dir.mkdir()
    owned_name = "ffffffffffffffffffffffffffffffff.mp3"
    foreign_name = "11111111111111111111111111111111.mp3"
    owned_path = upload_dir / owned_name
    foreign_path = upload_dir / foreign_name
    owned_path.write_bytes(b"owner-audio")
    foreign_path.write_bytes(b"foreign-audio")
    now = datetime.now(UTC)
    store.create(
        TaskOwnershipRecord(
            task_id="video-task-a",
            owner_id="user-a",
            created_at=now,
            kind="video",
            metadata={},
        )
    )
    for filename, owner in ((owned_name, "user-a"), (foreign_name, "user-b")):
        store.create(
            TaskOwnershipRecord(
                task_id=filename,
                owner_id=owner,
                created_at=now,
                kind=BGM_KIND,
                metadata={"filename": filename},
            )
        )
    monkeypatch.setattr(bgm_service, "uploaded_bgm_dir", lambda: str(upload_dir))
    monkeypatch.setattr(
        bgm_service, "list_builtin_bgm_files", lambda: ["/presets/default.mp3"]
    )
    selected_from = []

    def choose(files):
        selected_from.extend(files)
        return files[0]

    monkeypatch.setattr(video.random, "choice", choose)

    assert video.get_bgm_file(
        bgm_type="random", task_id="video-task-a"
    ) == "/presets/default.mp3"
    assert set(selected_from) == {"/presets/default.mp3", str(owned_path)}
    assert str(foreign_path) not in selected_from
