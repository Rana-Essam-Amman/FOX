"""Regression tests for the JWT authentication dependency annotation."""
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.models.exception import HttpException
from app.security.jwt_auth import AuthenticatedUser, require_authenticated_user


class TestJWTDependencyAnnotation(unittest.TestCase):
    def setUp(self):
        app = FastAPI()

        @app.exception_handler(HttpException)
        def _handle(request, exc: HttpException):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.message},
            )

        @app.get("/protected")
        def protected(user: AuthenticatedUser = Depends(require_authenticated_user)):
            return {"sub": user.sub}

        self.client = TestClient(app)

    def test_missing_bearer_returns_401_not_422(self):
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("query.request", response.text)
        self.assertNotIn("Field required", response.text)

    def test_invalid_token_returns_401(self):
        from app.models.exception import HttpException
        with patch(
            "app.security.jwt_auth.jwt_verifier.verify",
            side_effect=HttpException(
                task_id="t", status_code=401, message="invalid token"
            ),
        ):
            response = self.client.get(
                "/protected",
                headers={"Authorization": "Bearer not-a-valid-token"},
            )
        self.assertEqual(response.status_code, 401)

    def test_valid_token_reaches_handler_with_subject(self):
        user = AuthenticatedUser(sub="user-42", email="u@example.com")
        with patch(
            "app.security.jwt_auth.jwt_verifier.verify",
            return_value=user,
        ):
            response = self.client.get(
                "/protected",
                headers={"Authorization": "Bearer valid-token"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sub"], "user-42")
