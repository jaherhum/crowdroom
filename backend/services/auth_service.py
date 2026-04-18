from backend.core.exceptions import EntityExistsException, InvalidCredentialsException
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from backend.schemas.user import UserCreate, UserRead
from backend.services.user_service import UserService


class AuthService:
    def __init__(self, user_service: UserService, security_service: SecurityService):
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

    def login_user(self, user_data: LoginRequest) -> TokenResponse:
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
