"""Custom application exceptions."""

from uuid import UUID


class AppException(Exception):
    """Base class for all application-specific exceptions.

    Attributes:
        message (str): The error message.
    """

    pass


class EntityNotFoundException(AppException):
    """Exception raised when a requested entity is not found in the database.

    Attributes:
        entity_name (str): The name of the entity type (e.g., 'User').
        entity_id (str | UUID): The unique identifier of the missing entity.
    """

    def __init__(self, entity_name: str, entity_id: str | UUID):
        """Initializes the exception with entity name and ID.

        Args:
            entity_name (str): The name of the entity type.
            entity_id (str | UUID): The unique identifier of the missing entity.
        """
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_name} with ID {entity_id} not found")


class EntityExistsException(AppException):
    """Exception raised when a requested entity already exists in the database.

    Attributes:
        entity_name (str): The name of the entity type (e.g., 'User').
    """

    def __init__(self, entity_name: str):
        """Initializes the exception with entity name.

        Args:
            entity_name (str): The name of the entity type.
        """
        self.entity_name = entity_name
        super().__init__(f"Entity {entity_name} already exists")


class EntityDoesNotExistException(AppException):
    """Exception raised when a requested entity does not exist in the database.

    Attributes:
        entity_name (str): The name of the entity type (e.g., 'User').
    """

    def __init__(self, entity_name: str):
        """Initializes the exception with entity name.

        Args:
            entity_name (str): The name of the entity type.
        """
        self.entity_name = entity_name
        super().__init__(f"Entity {entity_name} does not exist")


class InvalidCredentialsException(AppException):
    """Exception raised when credentials are invalid.

    Attributes:
        message (str): The error message.
    """

    def __init__(self):
        """Initializes the exception."""
        super().__init__("Invalid username/email or password.")
