"""User schemas for the API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class UserBase(BaseModel):
    """Base schema for User attributes.

    Attributes:
        username (Optional[str]): The unique username for the user.
        email (Optional[EmailStr]): The user's email address.
    """

    username: Optional[str] = Field(
        default=None, max_length=32, description="The unique username for the user."
    )
    email: Optional[EmailStr] = Field(
        default=None, description="The user's email address."
    )


class UserCreate(UserBase):
    """Schema for creating a new User.

    Attributes:
        username (Optional[str]): The unique username for the user.
        email (Optional[EmailStr]): The user's email address.
        password (Optional[SecretStr]): Plain text password to be hashed before storage.
    """

    password: Optional[SecretStr] = Field(
        default=None,
        min_length=8,
        max_length=255,
        description="Plain text password. Will be hashed before storage.",
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing User. All fields are optional.

    Attributes:
        username (Optional[str]): The new username for the user.
        email (Optional[EmailStr]): The new email address.
        password (Optional[SecretStr]): The new plain text password to be hashed.
    """

    username: Optional[str] = Field(
        None,
        max_length=32,
        description="The new username for the user.",
    )
    email: Optional[EmailStr] = Field(None, description="The new email address.")
    password: Optional[SecretStr] = Field(
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
        email (Optional[EmailStr]): The user's email address.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(
        description="The unique identifier of the user.",
    )
