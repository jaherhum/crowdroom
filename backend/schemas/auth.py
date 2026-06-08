"""Authentication schemas for the API."""

from pydantic import BaseModel, EmailStr, Field, SecretStr


class RegisterRequest(BaseModel):
    """Request schema for user registration.

    Attributes:
        username (str): The unique username for the user.
        email (Optional[EmailStr]): The user's email address.
            Required if AUTH_MODE is remote.
        password (Optional[SecretStr]): The user's plain text password.
            Required if AUTH_MODE is remote.
    """

    username: str = Field(..., description="The username.")
    email: EmailStr | None = Field(None, description="The email address.")
    password: SecretStr | None = Field(
        None, description="The user plain text password."
    )


class LoginRequest(BaseModel):
    """Request schema for user authentication.

    Attributes:
        identifier (str): The user identifier, which can be either a
            username or an email.
        password (SecretStr): The user's plain text password.
    """

    identifier: str = Field(..., description="The user identifier, username or email.")
    password: SecretStr = Field(..., description="The user plain text password.")


class LocalLoginRequest(BaseModel):
    """Request schema for LOCAL mode authentication.

    Attributes:
        username (str): The username to login or auto-register with.
        password (Optional[SecretStr]): Optional password. Required to create rooms.
    """

    username: str = Field(..., min_length=1, max_length=32, description="The username.")
    password: SecretStr | None = Field(
        None, description="Password. Required for users who want to create rooms."
    )


class SetPasswordRequest(BaseModel):
    """Request schema for setting a password on a passwordless account.

    Attributes:
        password (SecretStr): The new password to set.
    """

    password: SecretStr = Field(
        ..., min_length=6, description="The new password to set."
    )


class CompleteProfileRequest(BaseModel):
    """Request schema for completing a user profile (LOCAL→ONLINE migration).

    Attributes:
        email (EmailStr): The email address to set.
        password (SecretStr): The password to set.
    """

    email: EmailStr = Field(..., description="The email address to set.")
    password: SecretStr = Field(
        ..., min_length=8, description="The password to set."
    )


class TokenResponse(BaseModel):
    """Response schema for successful authentication.

    Attributes:
        access_token (str): The generated JWT access token.
        token_type (str): The type of token, defaults to 'bearer'.
    """

    access_token: str = Field(..., description="The access token.")
    token_type: str = Field(default="bearer", description="The token type.")
