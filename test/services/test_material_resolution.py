import os
import uuid
from dataclasses import dataclass

import pytest

from app.security.material_resolution import (
    MaterialNotFound,
    is_stored_material_name,
    resolve_owned_material,
)


@dataclass
class _Record:
    owner_id: str
    kind: str = "material"


class _Store(dict):
    def lookup(self, task_id):
        return self.get(task_id)


def _stored_name(ext=".mp4"):
    return f"{uuid.uuid4().hex}{ext}"


@pytest.fixture()
def material_dir(tmp_path):
    root = tmp_path / "local_videos"
    root.mkdir()
    return str(root)


@pytest.fixture()
def owned(material_dir):
    """User A owns one stored file; the file is on disk."""
    name = _stored_name()
    with open(os.path.join(material_dir, name), "wb") as fh:
        fh.write(b"x")
    store = _Store({name: _Record(owner_id="user-a")})
    return name, store


def _resolve(reference, owner_id, store, material_dir):
    return resolve_owned_material(
        reference, owner_id=owner_id, lookup=store.lookup, storage_dir=material_dir
    )


def test_owner_can_resolve_own_material(owned, material_dir):
    name, store = owned
    path = _resolve(name, "user-a", store, material_dir)
    assert os.path.basename(path) == name


def test_other_user_cannot_resolve_material_id(owned, material_dir):
    name, store = owned
    with pytest.raises(MaterialNotFound):
        _resolve(name, "user-b", store, material_dir)


def test_unknown_id_is_rejected(owned, material_dir):
    _, store = owned
    with pytest.raises(MaterialNotFound):
        _resolve(_stored_name(), "user-a", store, material_dir)


def test_non_material_record_is_rejected(owned, material_dir):
    name, store = owned
    store[name] = _Record(owner_id="user-a", kind="task")
    with pytest.raises(MaterialNotFound):
        _resolve(name, "user-a", store, material_dir)


def test_absolute_path_to_other_users_file_is_rejected(owned, material_dir):
    name, store = owned
    absolute = os.path.join(material_dir, name)
    with pytest.raises(MaterialNotFound):
        _resolve(absolute, "user-b", store, material_dir)
    with pytest.raises(MaterialNotFound):
        _resolve(absolute, "user-a", store, material_dir)


@pytest.mark.parametrize(
    "reference",
    ["../etc/passwd", "..", "sub/" + "a" * 32 + ".mp4", "a" * 32 + ".mp4/..", "", None, 42],
)
def test_traversal_and_malformed_references_are_rejected(owned, material_dir, reference):
    _, store = owned
    with pytest.raises(MaterialNotFound):
        _resolve(reference, "user-a", store, material_dir)


def test_missing_file_for_owned_record_is_rejected(material_dir):
    name = _stored_name()
    store = _Store({name: _Record(owner_id="user-a")})
    with pytest.raises(MaterialNotFound):
        _resolve(name, "user-a", store, material_dir)


def test_symlink_escaping_storage_root_is_rejected(tmp_path, material_dir):
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"secret")
    name = _stored_name()
    os.symlink(str(outside), os.path.join(material_dir, name))
    store = _Store({name: _Record(owner_id="user-a")})
    with pytest.raises(MaterialNotFound):
        _resolve(name, "user-a", store, material_dir)


def test_empty_owner_never_matches(owned, material_dir):
    name, store = owned
    store[name] = _Record(owner_id="")
    with pytest.raises(MaterialNotFound):
        _resolve(name, "", store, material_dir)


def test_stored_name_pattern():
    assert is_stored_material_name(_stored_name())
    assert not is_stored_material_name("../" + _stored_name())
    assert not is_stored_material_name(_stored_name().upper())
