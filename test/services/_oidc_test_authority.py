"""Real OIDC verification for HTTP tests.

Tokens are RS256-signed with a generated key and verified by the production
``JWTVerifier``. Its keys come from a real JWKS endpoint on loopback, and
signature, issuer, audience and expiry are all checked. The only substitution is
the process verifier singleton, which ``app.security.jwt_auth`` documents as the
replacement point for tests.
"""

from __future__ import annotations

import functools
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.security import jwt_auth

ISSUER = "https://oidc.fox.test/realm"
AUDIENCE = "fox-api"


class OidcTestAuthority:
    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._kid = uuid.uuid4().hex
        public_jwk = json.loads(RSAAlgorithm.to_jwk(self._private_key.public_key()))
        public_jwk.update({"kid": self._kid, "use": "sig", "alg": "RS256"})
        body = json.dumps({"keys": [public_jwk]}).encode("utf-8")

        class _JwksHandler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - http.server API
                if self.path != "/jwks.json":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _JwksHandler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.jwks_url = f"http://127.0.0.1:{self._server.server_address[1]}/jwks.json"

    def token(
        self,
        sub: str,
        *,
        expires_in: int = 600,
        audience: str = AUDIENCE,
        issuer: str = ISSUER,
        key=None,
    ) -> str:
        now = int(time.time())
        claims = {
            "sub": sub,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + expires_in,
        }
        return jwt.encode(
            claims, key or self._private_key, algorithm="RS256", headers={"kid": self._kid}
        )

    def verifier(self) -> jwt_auth.JWTVerifier:
        return jwt_auth.JWTVerifier(issuer=ISSUER, audience=AUDIENCE, jwks_url=self.jwks_url)


@functools.lru_cache(maxsize=1)
def shared_authority() -> OidcTestAuthority:
    return OidcTestAuthority()


def install_oidc_for(testcase) -> OidcTestAuthority:
    """Point the production verifier at the test authority for one test case."""
    authority = shared_authority()
    patcher = patch.object(jwt_auth, "jwt_verifier", authority.verifier())
    patcher.start()
    testcase.addCleanup(patcher.stop)
    return authority


def authed_client(app, *, sub: str = "user-a", **kwargs) -> TestClient:
    """TestClient whose every request carries a valid RS256 bearer token for ``sub``."""
    token = shared_authority().token(sub)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"}, **kwargs)
