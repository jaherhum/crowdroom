"""Service for handling user authentication and registration."""

from uuid import UUID

from backend.core.exceptions import (
    EntityExistsException,
    InvalidCredentialsException,
    PasswordRequiredException,
)
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.schemas.auth import (
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.schemas.user import UserCreate
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

    def register_user(self, user_data: RegisterRequest) -> TokenResponse:
        """Registers a new user and returns an access token.

        Args:
            user_data (RegisterRequest): The schema containing registration details.

        Returns:
            TokenResponse: Access token for immediate login.

        Raises:
            EntityExistsException: If the username or email is already taken.
        """
        if self._user_service.get_by_username(user_data.username):
            raise EntityExistsException("Username already taken")
        if user_data.email and self._user_service.get_by_email(str(user_data.email)):
            raise EntityExistsException("Email already in use")

        user_to_create = UserCreate(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )
        created_user = self._user_service.create_user(user_to_create)

        token = self._security_service.create_token(
            token_type=TokenType.ACCESS,
            data={"sub": str(created_user.id)},
        )
        return TokenResponse(access_token=token, token_type="bearer")

    def local_login(self, user_data: LocalLoginRequest) -> TokenResponse:
        """Authenticate or auto-register a user in LOCAL mode.

        If a password is provided and the user doesn't exist, creates a
        password-protected account. If the user exists with a password,
        verifies it. Passwordless users can login without a password.

        Args:
            user_data: The schema containing username and optional password.

        Returns:
            TokenResponse with access token.

        Raises:
            InvalidCredentialsException: If password verification fails.
        """
        username = user_data.username.strip().lower()
        plain_password = (
            user_data.password.get_secret_value() if user_data.password else None
        )
        user = self._user_service.get_by_username(username)

        if not user:
            user_to_create = UserCreate(
                username=username, email=None, password=plain_password
            )
            user = self._user_service.create_user(user_to_create)
        elif user.hashed_password:
            if not plain_password:
                raise PasswordRequiredException()
            if not self._security_service.verify_password(
                plain_password, user.hashed_password
            ):
                raise InvalidCredentialsException()

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

    def set_password(self, user_id: UUID, plain_password: str) -> None:
        """Set a password on a user account that doesn't have one.

        Args:
            user_id: The user's ID.
            plain_password: The plain-text password to hash and store.
        """
        hashed = self._security_service.generate_password_hash(plain_password)
        self._user_service.update_user_password(user_id, hashed)

    def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change a user's password after verifying the current one.

        Args:
            user: The authenticated user.
            current_password: The current password for verification.
            new_password: The new password to set.

        Raises:
            InvalidCredentialsException: If current password is incorrect.
        """
        if not user.hashed_password:
            raise InvalidCredentialsException()

        is_valid = self._security_service.verify_password(
            current_password, user.hashed_password
        )
        if not is_valid:
            raise InvalidCredentialsException()

        hashed = self._security_service.generate_password_hash(new_password)
        self._user_service.update_user_password(user.id, hashed)

    def complete_profile(self, user: User, email: str, plain_password: str) -> None:
        """Set email and password on an incomplete profile.

        Only updates fields that are currently missing. Skips if already set.

        Args:
            user: The authenticated user to complete.
            email: The email to set (if user has no email).
            plain_password: The plain-text password to hash and set (if no password).

        Raises:
            EntityExistsException: If the email is already taken by another user.
        """
        normalized_email = email.strip().lower()

        if not user.email:
            existing = self._user_service.get_by_email(normalized_email)
            if existing and existing.id != user.id:
                raise EntityExistsException("Email already in use")
            from backend.schemas.user import UserUpdate

            self._user_service.update_user(user.id, UserUpdate(email=normalized_email))

        if not user.hashed_password:
            self.set_password(user.id, plain_password)

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
