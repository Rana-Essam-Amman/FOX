from __future__ import annotations

import io

import pytest

from app.security.adapters.storage import LocalFilesystemStorage, StoredObjectInfo


def test_put_stream_publishes_object_and_head_returns_metadata(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))

    info = storage.put_stream("users/user-1/materials/clip.mp4", io.BytesIO(b"video"), 5)

    assert info == storage.head("users/user-1/materials/clip.mp4")
    assert isinstance(info, StoredObjectInfo)
    assert info.size == 5
    assert (tmp_path / "users/user-1/materials/clip.mp4").read_bytes() == b"video"


def test_put_stream_rejects_size_mismatch_and_removes_staging_file(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))

    with pytest.raises(ValueError, match="expected size"):
        storage.put_stream("material.bin", io.BytesIO(b"short"), 10)

    assert not (tmp_path / "material.bin").exists()
    assert list(tmp_path.glob(".fox-upload-*")) == []


def test_put_stream_does_not_overwrite_an_immutable_key(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))
    storage.put_stream("material.bin", io.BytesIO(b"first"), 5)

    with pytest.raises(FileExistsError):
        storage.put_stream("material.bin", io.BytesIO(b"other"), 5)

    assert (tmp_path / "material.bin").read_bytes() == b"first"


@pytest.mark.parametrize(
    "object_name",
    ["", "/absolute", "../escape", "a/../escape", "a//b", r"a\\b", "a\x00b"],
)
def test_object_paths_reject_traversal_and_ambiguous_names(tmp_path, object_name):
    storage = LocalFilesystemStorage(str(tmp_path))

    with pytest.raises(ValueError, match="invalid object name"):
        storage.put_stream(object_name, io.BytesIO(b"x"), 1)


def test_iter_read_returns_only_the_requested_inclusive_range(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))
    storage.put_stream("material.bin", io.BytesIO(b"0123456789"), 10)

    chunks = list(storage.iter_read("material.bin", start=2, end=6, chunk_size=2))

    assert b"".join(chunks) == b"23456"
    assert all(len(chunk) <= 2 for chunk in chunks)


def test_iter_read_rejects_unsatisfiable_ranges(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))
    storage.put_stream("material.bin", io.BytesIO(b"abc"), 3)

    with pytest.raises(ValueError, match="not satisfiable"):
        list(storage.iter_read("material.bin", start=3))


def test_delete_is_idempotent_and_head_reports_missing_object(tmp_path):
    storage = LocalFilesystemStorage(str(tmp_path))
    storage.put_stream("material.bin", io.BytesIO(b"abc"), 3)

    storage.delete("material.bin")
    storage.delete("material.bin")

    with pytest.raises(FileNotFoundError):
        storage.head("material.bin")
