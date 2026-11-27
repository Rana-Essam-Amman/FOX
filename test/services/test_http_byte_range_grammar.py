from unittest.mock import patch

import pytest

from app import asgi
from app.config import config
from app.controllers.v1 import video as controller
from app.models.exception import HttpException
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


@pytest.mark.parametrize('header', ['Bytes=1-3', 'BYTES=-3'])
def test_stream_accepts_case_insensitive_byte_unit(tmp_path, header):
    _task_file(tmp_path, 'clip.mp4').write_bytes(b'0123456789')
    with patch.dict(config.app, {'api_key': ''}), patch.object(controller.utils, 'task_dir', return_value=str(tmp_path)):
        response = authed_client(asgi.get_application()).get('/api/v1/stream/task-1/clip.mp4', headers={'Range': header})
    assert response.status_code == 206
    assert response.content == (b'123' if header == 'Bytes=1-3' else b'789')


@pytest.mark.parametrize('header', ['bytes=+1-3', 'bytes=1_0-', 'bytes=1-+3', 'bytes=-+3', 'bytes= 1-3'])
def test_stream_rejects_non_http_numeric_syntax(tmp_path, header):
    _task_file(tmp_path, 'clip.mp4').write_bytes(b'01234567890123456789')
    with patch.dict(config.app, {'api_key': ''}), patch.object(controller.utils, 'task_dir', return_value=str(tmp_path)):
        response = authed_client(asgi.get_application()).get('/api/v1/stream/task-1/clip.mp4', headers={'Range': header})
    assert response.status_code == 416


def test_byte_positions_require_ascii_digits():
    with pytest.raises(HttpException) as raised:
        controller._parse_byte_range('bytes=١-٣', 10, 'fixture')
    assert raised.value.status_code == 416
