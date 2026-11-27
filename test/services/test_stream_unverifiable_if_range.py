from unittest.mock import patch

import pytest

from app import asgi
from app.config import config
from app.controllers.v1 import video as controller
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


@pytest.mark.parametrize('validator', ['"older-video-revision"', 'Tue, 01 Jan 2019 00:00:00 GMT'])
def test_stream_returns_complete_video_for_unverifiable_if_range(tmp_path, validator):
    payload = b'complete current video fixture'
    _task_file(tmp_path, 'clip.mp4').write_bytes(payload)
    with patch.dict(config.app, {'api_key': ''}), patch.object(controller.utils, 'task_dir', return_value=str(tmp_path)):
        response = authed_client(asgi.get_application()).get('/api/v1/stream/task-1/clip.mp4', headers={
            'Range': 'bytes=9-', 'If-Range': validator,
        })
    assert response.status_code == 200
    assert response.content == payload
    assert 'content-range' not in response.headers
    assert response.headers['content-length'] == str(len(payload))


def test_stream_keeps_unconditional_partial_request(tmp_path):
    _task_file(tmp_path, 'clip.mp4').write_bytes(b'0123456789')
    with patch.dict(config.app, {'api_key': ''}), patch.object(controller.utils, 'task_dir', return_value=str(tmp_path)):
        response = authed_client(asgi.get_application()).get('/api/v1/stream/task-1/clip.mp4', headers={'Range': 'bytes=3-'})
    assert response.status_code == 206
    assert response.content == b'3456789'
