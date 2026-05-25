"""Schemas for room invite operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateRoomInvite(BaseModel):
    """Input schema for creating a room invite."""

    max_uses: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of uses. None means unlimited.",
    )
    expires_in_hours: int | None = Field(
        default=None,
        ge=1,
        le=720,
        description="Hours until expiration. None means never expires.",
    )


class ReadRoomInvite(BaseModel):
    """Output schema for a room invite (host view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    room_id: UUID
    token: str
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    created_at: datetime


class InvitePreview(BaseModel):
    """Public preview of a room accessed via invite token."""

    room_id: UUID
    room_name: str
    is_private: bool
    host_user_id: UUID


class InviteJoinResult(BaseModel):
    """Result of successfully joining a room via invite."""

    room_id: UUID
    room_name: str
