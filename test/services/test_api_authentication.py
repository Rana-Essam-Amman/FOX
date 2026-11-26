import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import asgi
from app.config import config
from test.services._oidc_test_authority import install_oidc_for


class TestAPIAuthenticationHTTP(unittest.TestCase):
    """Real ASGI entry point: JWT identity is always required; api_key is an extra shared-key gate."""

    def setUp(self):
        self.original_app_config = dict(config.app)
        self.authority = install_oidc_for(self)
        self.client = TestClient(asgi.app)
        self.bearer = {"Authorization": f"Bearer {self.authority.token('user-a')}"}

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)

    def test_empty_key_still_requires_verified_identity(self):
        """An empty api_key disables only the shared-key check; JWT identity is still mandatory."""
        config.app["api_key"] = ""

        anonymous = self.client.get("/api/v1/tasks")
        identified = self.client.get("/api/v1/tasks", headers=self.bearer)

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(identified.status_code, 200)

    def test_configured_key_requires_both_identity_and_matching_key(self):
        config.app["api_key"] = "video-secret"
        key = {"x-api-key": "video-secret"}

        identity_only = self.client.get("/api/v1/tasks", headers=self.bearer)
        wrong_key = self.client.get("/api/v1/tasks", headers={**self.bearer, "x-api-key": "wrong"})
        key_only = self.client.get("/api/v1/tasks", headers=key)
        accepted = self.client.get("/api/v1/tasks", headers={**self.bearer, **key})

        self.assertEqual(identity_only.status_code, 401)
        self.assertEqual(wrong_key.status_code, 401)
        self.assertEqual(key_only.status_code, 401)
        self.assertEqual(accepted.status_code, 200)

    def test_forged_and_misscoped_tokens_are_rejected(self):
        config.app["api_key"] = ""
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cases = {
            "forged signature": self.authority.token("user-a", key=other_key),
            "wrong issuer": self.authority.token("user-a", issuer="https://evil.example"),
            "wrong audience": self.authority.token("user-a", audience="other-api"),
            "expired": self.authority.token("user-a", expires_in=-60),
        }
        for label, token in cases.items():
            with self.subTest(label=label):
                response = self.client.get(
                    "/api/v1/tasks", headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(response.status_code, 401)

    def test_llm_routes_authenticate_before_request_validation(self):
        """LLM routes must authenticate before any request reaches a paid model call."""
        config.app["api_key"] = "llm-secret"

        # The model call is isolated and counted; only the authorized request may reach it.
        with patch(
            "app.controllers.v1.llm.llm.generate_script",
            return_value="mocked script",
        ) as generate_script:
            missing = self.client.post("/api/v1/scripts", json={})
            accepted = self.client.post(
                "/api/v1/scripts",
                json={},
                headers={**self.bearer, "x-api-key": "llm-secret"},
            )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
        generate_script.assert_called_once()
