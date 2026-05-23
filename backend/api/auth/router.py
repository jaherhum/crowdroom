"""Authentication routes for the API."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth.dependencies import get_auth_service
from backend.core.config import settings
from backend.schemas.auth import (
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    register_request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Registers a new user (ONLINE mode only).

    Args:
        register_request (RegisterRequest): The registration details.
        auth_service (AuthService): The authentication service.

    Returns:
        UserRead: The newly created user.

    Raises:
        HTTPException: 404 if AUTH_MODE is LOCAL.
    """
    if settings.AUTH_MODE != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in LOCAL mode",
        )
    return auth_service.register_user(register_request)


@router.post("/login", response_model=TokenResponse)
def login(
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticates a user and returns a JWT token (ONLINE mode only).

    Args:
        login_request (LoginRequest): The login credentials.
        auth_service (AuthService): The authentication service.

    Returns:
        TokenResponse: The authentication token.

    Raises:
        HTTPException: 404 if AUTH_MODE is LOCAL.
    """
    if settings.AUTH_MODE != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in LOCAL mode",
        )
    return auth_service.login_user(login_request)


@router.post("/local-login", response_model=TokenResponse)
def local_login(
    login_request: LocalLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with username only (LOCAL mode).

    Finds existing user or auto-creates one. No password required.
    Disabled when AUTH_MODE=ONLINE.

    Args:
        login_request: The username to login with.
        auth_service: The authentication service.

    Returns:
        TokenResponse: The authentication token.

    Raises:
        HTTPException: 404 if AUTH_MODE is not LOCAL.
    """
    if settings.AUTH_MODE != "LOCAL":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in ONLINE mode",
        )
    return auth_service.local_login(login_request)
