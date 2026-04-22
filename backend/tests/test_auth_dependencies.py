from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from backend.api.auth.dependencies import get_current_user
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.services.user_service import UserService


def test_get_current_user_success():
    """Tests get_current_user with a valid token and existing user.
    """
    # Setup mocks
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    user_id = uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "zelda_lover@example.com"

    mock_user_service.get_by_identifier.return_value = mock_user
    mock_security_service.decode_token.return_value = {"sub": "zelda_lover@example.com"}

    # Call the dependency directly
    user = get_current_user(
        user_service=mock_user_service,
        security_service=mock_security_service,
        token="valid_token",
    )

    assert user == mock_user
    mock_security_service.decode_token.assert_called_once_with(
        "valid_token", expected_type=TokenType.ACCESS
    )
    mock_user_service.get_by_identifier.assert_called_once_with("zelda_lover@example.com")


def test_get_current_user_invalid_token():
    """Tests get_current_user when the token is invalid (decode_token raises error).
    """
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    mock_security_service.decode_token.side_effect = Exception("Invalid token")

    with pytest.raises(HTTPException) as excinfo:
        get_current_user(
            user_service=mock_user_service,
            security_service=mock_security_service,
            token="invalid_token",
        )

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


def test_get_current_user_user_not_found():
    """Tests get_current_user when the token is valid but the user does not exist.
    """
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)

    mock_security_service.decode_token.return_value = {"sub": "zelda_hater@example.com"}
    mock_user_service.get_by_identifier.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        get_current_user(
            user_service=mock_user_service,
            security_service=mock_security_service,
            token="valid_token",
        )

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


def test_integration_protected_route():
    """Integration test using TestClient to verify dependency injection in a route.
    """
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

    mock_user_service.get_by_identifier.return_value = mock_user
    mock_security_service.decode_token.return_value = {"sub": "zelda_lover@example.com"}

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # 1. Test Success
    response = client.get("/protected", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}

    # 2. Test Unauthorized (Simulating OAuth2PasswordBearer failure by not providing header)
    app.dependency_overrides = {}  # Reset
    response = client.get("/protected")
    assert response.status_code == 401
