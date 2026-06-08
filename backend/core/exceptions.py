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

    def __init__(self, message: str = "Invalid username/email or password."):
        """Initializes the exception.

        Args:
            message: Human-readable error description.
        """
        super().__init__(message)


class PasswordRequiredException(AppException):
    """Exception raised when a password-protected user tries to login without one.

    Attributes:
        message (str): The error message.
    """

    def __init__(self):
        """Initializes the exception."""
        super().__init__("This account has a password. Please enter it to log in.")


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

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
    ):
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

class UserAlreadyInRoomException(AppException):
    """Exception raised when a user tries to join a room while already in another.

    Attributes:
        current_room_id (str | UUID): The room the user is currently in.
    """

    def __init__(self, current_room_id: str | UUID = ""):
        """Initializes the exception with the current room ID.

        Args:
            current_room_id: The ID of the room the user is already in.
        """
        self.current_room_id = current_room_id
        if not current_room_id:
            super().__init__("User is already in a room. Leave current room first.")
        else:
            super().__init__(
                f"User is already in room {current_room_id}. Leave current room first."
            )

class OAuthStateException(AppException):
    """Exception raised when an OAuth state parameter is invalid or expired."""

    def __init__(self, reason: str = ""):
        """Initializes the exception.

        Args:
            reason: Specific reason for the failure. Empty for generic message.
        """
        if not reason:
            super().__init__("OAuth state validation failed.")
        else:
            super().__init__(f"OAuth state validation failed: {reason}")

class ProfileIncompleteException(AppException):
    """Exception raised when an ONLINE-mode user lacks email or password.

    Attributes:
        missing_fields (list[str]): Fields the user still needs to provide.
    """

    def __init__(self, missing_fields: list[str]):
        """Initializes the exception.

        Args:
            missing_fields: List of field names that are not yet set.
        """
        self.missing_fields = missing_fields
        super().__init__(
            "Profile incomplete. Please set your email and password."
        )


class SpotifyUpstreamException(AppException):
    """Exception raised when Spotify API returns an error response.

    Attributes:
        upstream_status_code: The HTTP status code Spotify returned.
    """

    def __init__(self, status_code: int, detail: str = ""):
        """Initializes the exception.

        Args:
            status_code: HTTP status code from Spotify's response.
            detail: Human-readable error detail. Auto-generated if empty.
        """
        self.upstream_status_code = status_code
        if not detail:
            super().__init__(f"Spotify returned HTTP {status_code}")
        else:
            super().__init__(detail)
