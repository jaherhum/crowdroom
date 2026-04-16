from uuid import UUID

from sqlmodel import Session

from core.exceptions import EntityNotFoundException
from core.security import SecurityService
from db.models.user import User
from repositories.user_repo import UserRepository
from schemas.user import UserCreate, UserUpdate


class UserService:
    """Service layer for managing user-related business logic.

    This service orchestrates the flow between the API layer and the repository,
    handling data normalization, password hashing, and business rules.

    Attributes:
        _user_repo (UserRepository): The repository for user data persistence.
        _security_service (SecurityService): The service for security operations.
    """

    def __init__(self, user_repo: UserRepository, security_service: SecurityService):
        self._user_repo: UserRepository = user_repo
        self._security_service: SecurityService = security_service

    def create_user(self, user_data: UserCreate) -> User:
        """Creates a new user in the system.

        Args:
            user_data (UserCreate): The schema containing user creation details.

        Returns:
            User: The newly created user model.
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
        return self._user_repo.save(user_model)

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Updates an existing user's information.

        Args:
            user_id (UUID): The unique identifier of the user to update.
            user_data (UserUpdate): The schema containing the fields to update.

        Returns:
            User: The updated user model.

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

        return self._user_repo.save(db_user)

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
