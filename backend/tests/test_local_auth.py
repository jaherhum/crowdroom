"""Tests for LOCAL auth mode (local-login endpoint and mode guards)."""

# ruff: noqa: D101, D102
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.schemas.auth import LocalLoginRequest
from backend.services.auth_service import AuthService
from backend.services.user_service import UserService


class TestAuthServiceLocalLogin:
    @pytest.fixture
    def mock_user_service(self):
        return MagicMock(spec=UserService)

    @pytest.fixture
    def mock_security_service(self):
        return MagicMock(spec=SecurityService)

    @pytest.fixture
    def auth_service(self, mock_user_service, mock_security_service):
        return AuthService(mock_user_service, mock_security_service)

    def test_local_login_existing_user(
        self, auth_service, mock_user_service, mock_security_service
    ):
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.hashed_password = None
        mock_user_service.get_by_username.return_value = mock_user
        mock_security_service.create_token.return_value = "mock_token"

        request = LocalLoginRequest(username="existinguser")
        result = auth_service.local_login(request)

        assert result.access_token == "mock_token"
        mock_user_service.get_by_username.assert_called_once_with("existinguser")
        mock_user_service.create_user.assert_not_called()
        mock_security_service.create_token.assert_called_once_with(
            token_type=TokenType.ACCESS,
            data={"sub": str(user_id)},
        )

    def test_local_login_creates_new_user(
        self, auth_service, mock_user_service, mock_security_service
    ):
        mock_user_service.get_by_username.return_value = None
        new_user = MagicMock()
        new_user.id = uuid4()
        mock_user_service.create_user.return_value = new_user
        mock_security_service.create_token.return_value = "new_token"

        request = LocalLoginRequest(username="newuser")
        result = auth_service.local_login(request)

        assert result.access_token == "new_token"
        mock_user_service.get_by_username.assert_called_once_with("newuser")
        mock_user_service.create_user.assert_called_once()

    def test_local_login_normalizes_username(
        self, auth_service, mock_user_service, mock_security_service
    ):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.hashed_password = None
        mock_user_service.get_by_username.return_value = mock_user
        mock_security_service.create_token.return_value = "tok"

        request = LocalLoginRequest(username="  MyUser  ")
        auth_service.local_login(request)

        mock_user_service.get_by_username.assert_called_once_with("myuser")


class TestAuthRouterModeGuards:
    @pytest.fixture
    def client_local(self):
        from fastapi.testclient import TestClient

        with patch("backend.api.auth.router.settings") as mock_settings:
            mock_settings.AUTH_MODE = "LOCAL"
            from fastapi import FastAPI

            from backend.api.auth.router import router

            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            yield TestClient(app)

    @pytest.fixture
    def client_online(self):
        from fastapi.testclient import TestClient

        with patch("backend.api.auth.router.settings") as mock_settings:
            mock_settings.AUTH_MODE = "ONLINE"
            from fastapi import FastAPI

            from backend.api.auth.router import router

            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            yield TestClient(app)

    def test_local_login_disabled_in_online_mode(self, client_online):
        response = client_online.post(
            "/api/v1/auth/local-login", json={"username": "test"}
        )
        assert response.status_code == 404
        assert "ONLINE" in response.json()["detail"]

    def test_register_disabled_in_local_mode(self, client_local):
        response = client_local.post(
            "/api/v1/auth/register",
            json={
                "username": "test",
                "email": "t@t.com",
                "password": "secret123",
            },
        )
        assert response.status_code == 404
        assert "LOCAL" in response.json()["detail"]

    def test_login_disabled_in_local_mode(self, client_local):
        response = client_local.post(
            "/api/v1/auth/login",
            json={"identifier": "test", "password": "secret123"},
        )
        assert response.status_code == 404
        assert "LOCAL" in response.json()["detail"]


class TestAuthCookie:
    @pytest.fixture
    def client_local(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.auth.dependencies import get_auth_service
        from backend.api.auth.router import router
        from backend.schemas.auth import TokenResponse

        with patch("backend.api.auth.router.settings") as mock_settings:
            mock_settings.AUTH_MODE = "LOCAL"
            mock_settings.AUTH_COOKIE_NAME = "access_token"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.COOKIE_SECURE = False
            mock_settings.COOKIE_SAMESITE = "lax"

            app = FastAPI()
            app.include_router(router, prefix="/api/v1")

            mock_auth_service = MagicMock(spec=AuthService)
            mock_auth_service.local_login.return_value = TokenResponse(
                access_token="cookie_token_value"
            )
            app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
            yield TestClient(app)

    def test_local_login_sets_httponly_cookie(self, client_local):
        response = client_local.post(
            "/api/v1/auth/local-login", json={"username": "alice"}
        )
        assert response.status_code == 200
        assert response.json()["access_token"] == "cookie_token_value"

        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=cookie_token_value" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie

    def test_logout_clears_cookie(self, client_local):
        response = client_local.post("/api/v1/auth/logout")
        assert response.status_code == 204
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
