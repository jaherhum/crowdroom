"""Platform connection schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models.enum import StreamingPlatforms


class CreatePlatformConnection(BaseModel):
    """Schema for connecting a new streaming platform.

    Attributes:
        platform: The streaming service to connect.
        credentials: Platform-specific credentials as key-value pairs.
    """

    platform: StreamingPlatforms = Field(
        ..., description="The streaming service to connect."
    )
    credentials: dict[str, str] = Field(
        ..., description="Platform-specific credentials (e.g., client_id, client_secret)."
    )


class ReadPlatformConnection(BaseModel):
    """Schema for platform connection data returned by the API.

    Attributes:
        id: The unique internal identifier.
        user_id: The user who owns this connection.
        platform: The connected streaming service.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The unique internal identifier.")
    user_id: UUID = Field(..., description="The user who owns this connection.")
    platform: StreamingPlatforms = Field(
        ..., description="The connected streaming service."
    )


class UpdatePlatformConnection(BaseModel):
    """Schema for updating platform credentials.

    Attributes:
        credentials: New platform-specific credentials.
    """

    credentials: dict[str, str] = Field(
        ..., description="Updated platform-specific credentials."
    )
