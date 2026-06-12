"""User schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, model_validator


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
        min_length=6,
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
    avatar_path: str | None = Field(
        None, description="Filename of the user's avatar in static/avatars/."
    )


class UserRead(UserBase):
    """Schema for reading User data.

    Attributes:
        id (UUID): The unique identifier of the user.
        username (str): The unique username for the user.
        email (EmailStr | None): The user's email address.
        room_id (UUID | None): The room the user is currently in.
        has_password (bool): Whether the user has a password set.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(
        description="The unique identifier of the user.",
    )
    room_id: UUID | None = Field(
        default=None, description="The room the user is currently in."
    )
    has_password: bool = Field(
        default=False, description="Whether the user has a password set."
    )
    profile_complete: bool = Field(
        default=False,
        description="Whether the user has both email and password set.",
    )
    avatar_url: str | None = Field(
        default=None, description="URL to the user's avatar image."
    )

    @model_validator(mode="before")
    @classmethod
    def compute_derived_fields(cls, data):
        """Derive has_password, profile_complete, and avatar_url from the source."""
        if hasattr(data, "hashed_password"):
            avatar_url = (
                f"/static/avatars/{data.avatar_path}" if data.avatar_path else None
            )
            data = {
                "id": data.id,
                "username": data.username,
                "email": data.email,
                "room_id": data.room_id,
                "has_password": data.hashed_password is not None,
                "profile_complete": (
                    data.hashed_password is not None and data.email is not None
                ),
                "avatar_url": avatar_url,
            }
        elif isinstance(data, dict):
            if "has_password" not in data:
                data["has_password"] = data.get("hashed_password") is not None
            if "profile_complete" not in data:
                data["profile_complete"] = (
                    data.get("hashed_password") is not None
                    and data.get("email") is not None
                )
            if "avatar_url" not in data:
                avatar_path = data.get("avatar_path")
                data["avatar_url"] = (
                    f"/static/avatars/{avatar_path}" if avatar_path else None
                )
        return data
