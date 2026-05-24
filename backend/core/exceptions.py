"""Custom application exceptions."""

from uuid import UUID


class AppException(Exception):
    """Base class for all application-specific exceptions.

    Attributes:
        message (str): The error message.
    """

    def __init__(self, message: str) -> None:
        """Base exception for all application-specific errors.

        Args:
            message: Human-readable error description.
        """
        super().__init__(message)


class EntityNotFoundException(AppException):
    """Exception raised when a requested entity is not found in the database.

    Supports two calling patterns:
        - Full form: EntityNotFoundException("User", user_id)
        - Generic:   EntityNotFoundException() — no entity specified

    Attributes:
        entity_name (str): The name of the entity type.
        entity_id (str | UUID): The unique identifier of the missing entity.
    """

    def __init__(
        self,
        entity_name: str = "",
        entity_id: str | UUID = "",
    ):
        """Initializes the exception with entity name and ID.

        Args:
            entity_name: The entity type (e.g., "User"). Empty for generic 404.
            entity_id: The missing entity's ID. Ignored if entity_name is empty.
        """
        self.entity_name = entity_name
        self.entity_id = entity_id
        if entity_name:
            super().__init__(f"Entity {entity_name} with ID {entity_id} not found")
        else:
            super().__init__("Entity not found")


class EntityExistsException(AppException):
    """Exception raised when a requested entity already exists in the database.

    Supports two calling patterns:
        - Full form: EntityExistsException("User") — entity type specified
        - Generic:   EntityExistsException() — no entity specified

    Attributes:
        entity_name (str): The name of the entity type.
    """

    def __init__(self, entity_name: str = ""):
        """Initializes the exception with an optional entity name.

        Args:
            entity_name: The entity type (e.g., "User"). Empty for generic 409.
        """
        self.entity_name = entity_name
        if entity_name:
            super().__init__(f"Entity {entity_name} already exists")
        else:
            super().__init__("Entity already exists")


class InvalidCredentialsException(AppException):
    """Exception raised when credentials are invalid.

    Attributes:
        message (str): The error message.
    """

    def __init__(self):
        """Initializes the exception."""
        super().__init__("Invalid username/email or password.")


class InvalidPlatformCredentialsException(AppException):
    """Exception raised when streaming platform credentials are rejected.

    Attributes:
        platform (str): The platform that rejected the credentials.
    """

    def __init__(self, platform: str = ""):
        """Initializes the exception.

        Args:
            platform: The platform name (e.g., "Spotify"). Empty for generic.
        """
        self.platform = platform
        if platform:
            super().__init__(f"{platform} rejected the provided credentials")
        else:
            super().__init__("Platform rejected the provided credentials")


class ForbiddenException(AppException):
    """Exception raised when a user lacks permission for an operation.

    Attributes:
        message (str): The error message.
    """

    def __init__(self, message: str = "You do not have permission to perform this action"):
        """Initializes the exception.

        Args:
            message: Human-readable description of the forbidden action.
        """
        super().__init__(message)


class InviteExpiredException(AppException):
    """Exception raised when an invite token is expired or exhausted.

    Attributes:
        message (str): The error message.
    """

    def __init__(self):
        """Initializes the exception."""
        super().__init__("Invite is expired or has reached its maximum uses")
