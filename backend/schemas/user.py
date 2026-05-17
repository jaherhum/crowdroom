"""User schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class UserBase(BaseModel):
    """Base schema for User attributes.

    Attributes:
        username (str | None): The unique username for the user.
        email (EmailStr | None): The user's email address.
    """

    username: str | None = Field(
        default=None, max_length=32, description="The unique username for the user."
    )
    email: EmailStr | None = Field(
        default=None, description="The user's email address."
    )


class UserCreate(UserBase):
    """Schema for creating a new User.

    Attributes:
        username (str | None): The unique username for the user.
        email (EmailStr | None): The user's email address.
        password (SecretStr | None): Plain text password to be hashed before storage.
    """

    password: SecretStr | None = Field(
        default=None,
        min_length=8,
        max_length=255,
        description="Plain text password. Will be hashed before storage.",
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing User. All fields are optional.

    Attributes:
        username (str | None): The new username for the user.
        email (EmailStr | None): The new email address.
        password (SecretStr | None): The new plain text password to be hashed.
    """

    username: str | None = Field(
        None,
        max_length=32,
        description="The new username for the user.",
    )
    email: EmailStr | None = Field(None, description="The new email address.")
    password: SecretStr | None = Field(
        None,
        min_length=8,
        max_length=255,
        description="The new plain text password. Will be hashed before storage.",
    )


class UserRead(UserBase):
    """Schema for reading User data.

    Attributes:
        id (UUID): The unique identifier of the user.
        username (str): The unique username for the user.
        email (EmailStr | None): The user's email address.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(
        description="The unique identifier of the user.",
    )
