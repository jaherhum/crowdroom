"""Tests for AuthService logic."""

from unittest.mock import MagicMock
from uuid import uuid4

from backend.core.exceptions import EntityExistsException, InvalidCredentialsException
from backend.core.security import SecurityService
from backend.schemas.auth import LoginRequest, RegisterRequest
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService
from backend.services.user_service import UserService


def test_auth_service_logic():
    """Unit tests for AuthService logic."""
    # Mocking dependencies
    mock_user_service = MagicMock(spec=UserService)
    mock_security_service = MagicMock(spec=SecurityService)
    auth_service = AuthService(mock_user_service, mock_security_service)

    # 1. Test register_user - Success
    user_data = RegisterRequest(
        username="testuser", email="test@example.com", password="secretpassword"
    )
    mock_user_service.get_by_username.return_value = None
    mock_user_service.get_by_email.return_value = None

    mock_user_read = MagicMock(spec=UserRead)
    mock_user_service.create_user.return_value = mock_user_read

    result = auth_service.register_user(user_data)

    assert result == mock_user_read
    mock_user_service.create_user.assert_called_once()
    print("Test register_user (success) passed.")

    # 2. Test register_user - User exists
    mock_user_service.get_by_username.return_value = MagicMock()
    try:
        auth_service.register_user(user_data)
        assert False, "Should have raised EntityExistsException"
    except EntityExistsException:
        print("Test register_user (user exists) passed.")

    # 3. Test login_user - Success
    login_data = LoginRequest(identifier="testuser", password="secretpassword")
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.hashed_password = "hashed_val"
    mock_user_service.get_by_identifier.return_value = mock_user
    mock_security_service.verify_password.return_value = True
    mock_security_service.create_token.return_value = "mock_token"

    token_response = auth_service.login_user(login_data)

    assert token_response.access_token == "mock_token"
    print("Test login_user (success) passed.")

    # 4. Test login_user - Invalid Credentials
    mock_security_service.verify_password.return_value = False
    try:
        auth_service.login_user(login_data)
        assert False, "Should have raised InvalidCredentialsException"
    except InvalidCredentialsException:
        print("Test login_user (invalid password) passed.")


if __name__ == "__main__":
    try:
        test_auth_service_logic()
        print("\nAll AuthService tests passed successfully.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
