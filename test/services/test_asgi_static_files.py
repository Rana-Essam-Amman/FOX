import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import asgi
from app.config import config
from app.utils import utils


class TestTaskStaticFilesRemoved(unittest.TestCase):
    """Private task artifacts must not be exposed via unauthenticated StaticFiles.

    The previous /tasks StaticFiles mount has been removed. Artifacts are
    served only through authenticated, ownership-checked /api/v1/download
    and /api/v1/stream endpoints.
    """

    def setUp(self):
        self.original_app_config = dict(config.app)
        config.app["api_key"] = ""
        self.client = TestClient(asgi.app)

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_task_directory_is_not_publicly_mounted(self):
        with tempfile.TemporaryDirectory(
            prefix="static-task-", dir=utils.task_dir()
        ) as task_directory:
            task_path = Path(task_directory)
            artifact = task_path / "artifact.txt"
            artifact.write_text("task artifact", encoding="utf-8")

            response = self.client.get(f"/tasks/{task_path.name}/{artifact.name}")

        # Mount removed; unauthenticated static access must fail.
        self.assertIn(response.status_code, (404, 403))

    def test_public_static_root_still_available(self):
        # Public assets under / remain available; only private task dirs are protected.
        response = self.client.get("/")
        # May be 200 (index) or 404 if no index; either is acceptable as long as the app starts.
        self.assertLess(response.status_code, 500)
