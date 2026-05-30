"""Platform connection schemas for the API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models.enum import ConnectionType, StreamingPlatforms


class CreatePlatformConnection(BaseModel):
    """Schema for connecting a new streaming platform.

    Attributes:
        platform: The streaming service to connect.
        credentials: Platform-specific credentials as key-value pairs.
    """

    platform: StreamingPlatforms = Field(
        ..., description="The streaming service to connect."
    )
    connection_type: ConnectionType | None = Field(ConnectionType.CLIENT_CREDENTIALS)
    credentials: dict[str, str] | None = Field(
        None,
        description="Platform-specific credentials (e.g., client_id, client_secret).",
    )


class ReadPlatformConnection(BaseModel):
    """Schema for platform connection data returned by the API.

    Attributes:
        id: The unique internal identifier.
        user_id: The user who owns this connection.
        platform: The connected streaming service.
        connection_type: The authentication flow used.
        token_expires_at: When the OAuth access token expires.
        scopes: Space-separated granted OAuth scopes.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The unique internal identifier.")
    user_id: UUID = Field(..., description="The user who owns this connection.")
    platform: StreamingPlatforms = Field(
        ..., description="The connected streaming service."
    )
    connection_type: ConnectionType = Field(
        ..., description="The authentication flow used."
    )
    token_expires_at: datetime | None = Field(
        None, description="When the OAuth access token expires."
    )
    scopes: str | None = Field(
        None, description="Space-separated granted OAuth scopes."
    )


class UpdatePlatformConnection(BaseModel):
    """Schema for updating platform credentials.

    Attributes:
        credentials: New platform-specific credentials.
    """

    credentials: dict[str, str] = Field(
        ..., description="Updated platform-specific credentials."
    )


class StoreOAuthTokens(BaseModel):
    """Schema for storing OAuth tokens from authorization code flow.

    Attributes:
        access_token: The OAuth access token.
        refresh_token: The OAuth refresh token.
        expires_at: UTC datetime when the access token expires.
        scopes: Space-separated granted OAuth scopes.
    """

    access_token: str = Field(..., description="The OAuth access token.")
    refresh_token: str = Field(..., description="The OAuth refresh token.")
    expires_at: datetime = Field(
        ..., description="UTC datetime when the access token expires."
    )
    scopes: str = Field(..., description="Space-separated granted OAuth scopes.")
