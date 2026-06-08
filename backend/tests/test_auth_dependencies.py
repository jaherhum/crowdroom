"""Tests for authentication dependencies."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from backend.api.auth.dependencies import (
    get_current_user,
    get_current_user_unchecked,
)
from backend.core.exceptions import ProfileIncompleteException
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.services.user_service import UserService


def test_get_current_user_unchecked_success():
    """Tests get_current_user_unchecked with a valid token and existing user."""
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    user_id = uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "zelda_lover@example.com"

    mock_user_service.get_by_id.return_value = mock_user
    mock_security_service.decode_token.return_value = {"sub": str(user_id)}

    user = get_current_user_unchecked(
        user_service=mock_user_service,
        security_service=mock_security_service,
        token="valid_token",
    )

    assert user == mock_user
    mock_security_service.decode_token.assert_called_once_with(
        "valid_token", expected_type=TokenType.ACCESS
    )
    mock_user_service.get_by_id.assert_called_once_with(user_id)


def test_get_current_user_unchecked_invalid_token():
    """Tests get_current_user_unchecked when the token is invalid."""
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    mock_security_service.decode_token.side_effect = Exception("Invalid token")

    with pytest.raises(HTTPException) as excinfo:
        get_current_user_unchecked(
            user_service=mock_user_service,
            security_service=mock_security_service,
            token="invalid_token",
        )

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


def test_get_current_user_unchecked_user_not_found():
    """Tests get_current_user_unchecked when user does not exist."""
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    nonexistent_id = uuid4()
    mock_security_service.decode_token.return_value = {"sub": str(nonexistent_id)}
    mock_user_service.get_by_id.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        get_current_user_unchecked(
            user_service=mock_user_service,
            security_service=mock_security_service,
            token="valid_token",
        )

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


@patch("backend.api.auth.dependencies.settings")
def test_get_current_user_online_mode_incomplete_profile(mock_settings):
    """Tests get_current_user raises ProfileIncompleteException in ONLINE mode."""
    mock_settings.AUTH_MODE = "ONLINE"

    mock_user = MagicMock(spec=User)
    mock_user.email = None
    mock_user.hashed_password = None

    with pytest.raises(ProfileIncompleteException) as excinfo:
        get_current_user(current_user=mock_user)

    assert "email" in excinfo.value.missing_fields
    assert "password" in excinfo.value.missing_fields


@patch("backend.api.auth.dependencies.settings")
def test_get_current_user_online_mode_complete_profile(mock_settings):
    """Tests get_current_user passes in ONLINE mode with complete profile."""
    mock_settings.AUTH_MODE = "ONLINE"

    mock_user = MagicMock(spec=User)
    mock_user.email = "test@example.com"
    mock_user.hashed_password = "hashed"

    result = get_current_user(current_user=mock_user)
    assert result == mock_user


@patch("backend.api.auth.dependencies.settings")
def test_get_current_user_local_mode_no_check(mock_settings):
    """Tests get_current_user skips profile check in LOCAL mode."""
    mock_settings.AUTH_MODE = "LOCAL"

    mock_user = MagicMock(spec=User)
    mock_user.email = None
    mock_user.hashed_password = None

    result = get_current_user(current_user=mock_user)
    assert result == mock_user


def test_integration_protected_route():
    """Integration test using TestClient to verify dependency injection in a route."""
    app = FastAPI()

    # Dummy protected route
    @app.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": str(user.id)}

    client = TestClient(app)

    # Mocking the dependencies for the app
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    user_id = uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    mock_user_service.get_by_id.return_value = mock_user
    mock_security_service.decode_token.return_value = {"sub": str(user_id)}

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # 1. Test Success
    response = client.get("/protected", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}

    # 2. Test Unauthorized (Simulating OAuth2PasswordBearer failure)
    app.dependency_overrides = {}  # Reset
    response = client.get("/protected")
    assert response.status_code == 401
