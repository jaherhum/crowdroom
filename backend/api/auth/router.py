from fastapi import APIRouter, Depends, status

from backend.api.auth.dependencies import get_auth_service
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(register_request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)) -> UserRead:
    """Registers a new user.

    Args:
        register_request (RegisterRequest): The registration details.
        auth_service (AuthService): The authentication service.

    Returns:
        UserRead: The newly created user.
    """
    return auth_service.register_user(register_request)


@router.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    """Authenticates a user and returns a JWT token.

    Args:
        login_request (LoginRequest): The login credentials.
        auth_service (AuthService): The authentication service.

    Returns:
        TokenResponse: The authentication token.
    """
    return auth_service.login_user(login_request)
