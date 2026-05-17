"""Service layer for managing user-related business logic."""

from uuid import UUID

from backend.core.exceptions import EntityNotFoundException
from backend.core.security import SecurityService
from backend.db.models.user import User
from backend.repositories.user_repo import UserRepository
from backend.schemas.user import UserCreate, UserRead, UserUpdate


class UserService:
    """Service layer for managing user-related business logic.

    This service orchestrates the flow between the API layer and the repository,
    handling data normalization, password hashing, and business rules.

    Attributes:
        _user_repo (UserRepository): The repository for user data persistence.
        _security_service (SecurityService): The service for security operations.
    """

    def __init__(self, user_repo: UserRepository, security_service: SecurityService):
        """Initialize the UserService with its dependencies.

        Args:
            user_repo: Repository for all user data operations.
            security_service: Service for password hashing and JWT operations.
        """
        self._user_repo: UserRepository = user_repo
        self._security_service: SecurityService = security_service

    def get_all_users(self) -> list[UserRead]:
        """Retrieves all users.

        Returns:
            list[UserRead]: A list of user schemas.
        """
        users = self._user_repo.get_all()
        return [UserRead.model_validate(user) for user in users]

    def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieves a user by their unique ID.

        Args:
            user_id (UUID): The unique identifier of the user.

        Returns:
            User | None: The user model if found, otherwise None.
        """
        return self._user_repo.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        """Retrieves a user by their email.

        Args:
            email (str): The email address to search for.

        Returns:
            User | None: The user model if found, otherwise None.
        """
        return self._user_repo.get_by_email(email)

    def get_by_username(self, username: str) -> User | None:
        """Retrieves a user by their username.

        Args:
            username (str): The username to search for.

        Returns:
            User | None: The user model if found, otherwise None.
        """
        return self._user_repo.get_by_username(username)

    def get_by_identifier(self, identifier: str) -> User | None:
        """Retrieves a user by either username or email.

        Args:
            identifier (str): The username or email to search for.

        Returns:
            User | None: The user model if found, otherwise None.
        """
        user = self._user_repo.get_by_identifier(identifier)
        return UserRead.model_validate(user) if user else None

    def create_user(self, user_data: UserCreate) -> UserRead:
        """Creates a new user in the system.

        Args:
            user_data (UserCreate): The schema containing user creation details.

        Returns:
            UserRead: The newly created user schema.
        """
        data = user_data.model_dump()
        plain_password = data.pop("password")
        data["hashed_password"] = self._security_service.generate_password_hash(
            password=plain_password
        )

        if data.get("email"):
            data["email"] = data["email"].lower()
        if data.get("username"):
            data["username"] = data["username"].lower()

        user_model = User(**data)
        new_user = self._user_repo.save(user_model)
        return UserRead.model_validate(new_user)

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> UserRead:
        """Updates an existing user's information.

        Args:
            user_id (UUID): The unique identifier of the user to update.
            user_data (UserUpdate): The schema containing the fields to update.

        Returns:
            UserRead: The updated user schema.

        Raises:
            EntityNotFoundException: If no user is found with the given ID.
        """
        db_user = self._user_repo.get_by_id(user_id)
        if not db_user:
            raise EntityNotFoundException("User", user_id)
        update_dict = user_data.model_dump(exclude_unset=True)

        if "username" in update_dict:
            update_dict["username"] = update_dict["username"].lower()
        if "email" in update_dict:
            update_dict["email"] = update_dict["email"].lower()

        for k, v in update_dict.items():
            setattr(db_user, k, v)

        updated_user = self._user_repo.save(db_user)
        return UserRead.model_validate(updated_user)

    def delete_user(self, user_id: UUID) -> None:
        """Deletes a user from the system.

        Args:
            user_id (UUID): The unique identifier of the user to delete.

        Raises:
            EntityNotFoundException: If no user is found with the given ID.
        """
        db_user = self._user_repo.get_by_id(user_id)
        if not db_user:
            raise EntityNotFoundException("User", user_id)

        self._user_repo.delete(db_user)
