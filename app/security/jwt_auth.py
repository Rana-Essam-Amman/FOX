"""JWT/OIDC verification boundary for the FOX gateway.

Fails closed when issuer, audience, or JWKS are not configured.
Never trusts user identifiers from request bodies or query parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient
from loguru import logger

from fastapi import Request
from app.models.exception import HttpException
from app.controllers.base import get_task_id


@dataclass(frozen=True)
class AuthenticatedUser:
    sub: str
    email: str | None = None
    claims: dict[str, Any] | None = None


class AuthConfigurationError(RuntimeError):
    """Raised when production auth settings are missing or invalid."""


class JWTVerifier:
    def __init__(
        self,
        issuer: str | None = None,
        audience: str | None = None,
        jwks_url: str | None = None,
        algorithms: list[str] | None = None,
    ) -> None:
        self.issuer = issuer or os.getenv("FOX_OIDC_ISSUER")
        self.audience = audience or os.getenv("FOX_OIDC_AUDIENCE")
        self.jwks_url = jwks_url or os.getenv("FOX_OIDC_JWKS_URL")
        self.algorithms = algorithms or ["RS256", "ES256"]
        self._jwks_client: PyJWKClient | None = None

        if self.jwks_url:
            self._jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)

    def is_configured(self) -> bool:
        return bool(self.issuer and self.audience and self.jwks_url)

    def verify(self, token: str, request_id: str) -> AuthenticatedUser:
        if not self.is_configured():
            logger.error("OIDC authentication is not configured; rejecting request")
            raise HttpException(
                task_id=request_id,
                status_code=503,
                message="authentication service is unavailable",
            )

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError:
            raise HttpException(
                task_id=request_id, status_code=401, message="token expired"
            )
        except jwt.InvalidAudienceError:
            raise HttpException(
                task_id=request_id, status_code=401, message="invalid audience"
            )
        except jwt.InvalidIssuerError:
            raise HttpException(
                task_id=request_id, status_code=401, message="invalid issuer"
            )
        except jwt.PyJWTError as exc:
            logger.warning(f"JWT verification failed: {type(exc).__name__}")
            raise HttpException(
                task_id=request_id, status_code=401, message="invalid token"
            )

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise HttpException(
                task_id=request_id, status_code=401, message="token missing subject"
            )
        # Reject reserved internal namespace so a user JWT cannot claim an
        # internal owner identity.
        if sub.startswith("internal:"):
            raise HttpException(
                task_id=request_id, status_code=401, message="reserved subject namespace"
            )

        return AuthenticatedUser(
            sub=sub,
            email=payload.get("email") if isinstance(payload.get("email"), str) else None,
            claims=payload,
        )


# Singleton configured from environment. Tests can replace this.
jwt_verifier = JWTVerifier()


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency that extracts and verifies a Bearer token."""
    request_id = get_task_id(request)
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HttpException(
            task_id=request_id, status_code=401, message="missing or invalid authorization header"
        )
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HttpException(
            task_id=request_id, status_code=401, message="empty bearer token"
        )
    return jwt_verifier.verify(token, request_id)
