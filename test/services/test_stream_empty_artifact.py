from unittest.mock import patch


from app import asgi
from app.config import config
from app.controllers.v1 import video as controller
import pytest
from app.security import jwt_auth
from test.services._oidc_test_authority import authed_client, shared_authority
from test.services._ownership_isolation import isolate_ownership


@pytest.fixture(autouse=True)
def _oidc_verifier(monkeypatch):
    # Real RS256/JWKS verification and a fresh ownership store for every test.
    monkeypatch.setattr(jwt_auth, "jwt_verifier", shared_authority().verifier())
    isolate_ownership(monkeypatch, owned=[("task-1", "user-a")])


def _task_file(tmp_path, name):
    # Stream paths are "{task_id}/{file}" under the task base directory.
    (tmp_path / "task-1").mkdir(exist_ok=True)
    return tmp_path / "task-1" / name


def _get(tmp_path, headers=None):
    with (
        patch.dict(config.app, {"api_key": ""}),
        patch.object(controller.utils, "task_dir", return_value=str(tmp_path)),
    ):
        return authed_client(asgi.get_application()).get(
            "/api/v1/stream/task-1/empty.srt", headers=headers or {}
        )


def test_stream_returns_empty_body_for_empty_file_without_range(tmp_path):
    # 416 only answers a Range request; a plain GET of an empty artifact is a
    # complete zero-length representation, matching /download.
    _task_file(tmp_path, "empty.srt").write_bytes(b"")

    response = _get(tmp_path)

    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["content-length"] == "0"
    assert "content-range" not in response.headers


def test_stream_still_rejects_range_on_empty_file(tmp_path):
    _task_file(tmp_path, "empty.srt").write_bytes(b"")

    response = _get(tmp_path, {"Range": "bytes=0-"})

    assert response.status_code == 416
