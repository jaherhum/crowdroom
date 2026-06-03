"""Service for handling user authentication and registration."""

from uuid import UUID

from backend.core.exceptions import EntityExistsException, InvalidCredentialsException
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.schemas.auth import (
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.schemas.user import UserCreate, UserRead
from backend.services.user_service import UserService


class AuthService:
    """Service for handling user authentication and registration."""

    def __init__(self, user_service: UserService, security_service: SecurityService):
        """Initialize the AuthService with its dependencies.

        Args:
            user_service: UserService for user lookups and management.
            security_service: SecurityService for JWT and password operations.
        """
        self._user_service = user_service
        self._security_service = security_service

    def register_user(self, user_data: RegisterRequest) -> UserRead:
        """Registers a new user in the system.

        Args:
            user_data (RegisterRequest): The schema containing registration details.

        Returns:
            UserRead: The newly created user schema.

        Raises:
            EntityExistsException: If the username or email is already taken.
        """
        if self._user_service.get_by_username(user_data.username):
            raise EntityExistsException("User")
        if self._user_service.get_by_email(str(user_data.email)):
            raise EntityExistsException("User")

        user_to_create = UserCreate(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )
        return self._user_service.create_user(user_to_create)

    def local_login(self, user_data: LocalLoginRequest) -> TokenResponse:
        """Authenticate or auto-register a user by username only.

        Args:
            user_data: The schema containing the username.

        Returns:
            TokenResponse with access token.
        """
        username = user_data.username.strip().lower()
        user = self._user_service.get_by_username(username)

        if not user:
            user_to_create = UserCreate(username=username, email=None, password=None)
            user = self._user_service.create_user(user_to_create)

        token = self._security_service.create_token(
            token_type=TokenType.ACCESS,
            data={"sub": str(user.id)},
        )

        return TokenResponse(access_token=token, token_type="bearer")

    def login_user(self, user_data: LoginRequest) -> TokenResponse:
        """Authenticates a user and returns a token.

        Args:
            user_data (LoginRequest): The schema containing login credentials.

        Returns:
            TokenResponse: The authentication token.

        Raises:
            InvalidCredentialsException: If authentication fails.
        """
        identifier = user_data.identifier.strip().lower()
        user = self._user_service.get_by_identifier(identifier)

        if not user:
            raise InvalidCredentialsException()

        is_valid = self._security_service.verify_password(
            user_data.password.get_secret_value(),
            user.hashed_password,
        )
        if not is_valid:
            raise InvalidCredentialsException()

        token = self._security_service.create_token(
            token_type=TokenType.ACCESS,
            data={"sub": str(user.id)},
        )

        return TokenResponse(access_token=token, token_type="bearer")

    def resolve_user_from_token(self, token: str) -> User | None:
        """Decode a JWT token and return the associated user.

        Args:
            token: Raw JWT access token string.

        Returns:
            The User if token is valid and user exists, None otherwise.
        """
        try:
            payload = self._security_service.decode_token(
                token, expected_type=TokenType.ACCESS
            )
            user_id = payload.get("sub")
            return self._user_service.get_by_id(UUID(user_id))
        except Exception:
            return None
