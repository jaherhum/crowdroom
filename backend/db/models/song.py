from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from backend.db.models.enum import StreamingPlatforms


class Song(SQLModel, table=True):
    """Database model representing a musical track in the catalog.

    This model stores metadata about songs retrieved from external streaming
    platforms. It acts as a persistent cache to avoid redundant metadata
    fetching.

    Attributes:
        id (UUID): Primary key, internal unique identifier.
        external_id (str): Unique identifier from the streaming platform
            (e.g., Spotify Track ID).
        title (str): Title of the song.
        artist (str): Name of the performing artist(s).
        platform (StreamingPlatforms): The source platform of the track.
        duration (float): Length of the track in seconds.
        album_art_url (str, optional): URL to the track's cover art.
        is_explicit (bool, optional): Flag indicating explicit content.
        queue_items (list[QueueItem]): List of queue entries referencing this song.
    """

    __tablename__ = "songs"
    __table_args__ = (
        UniqueConstraint(
            "external_id", "platform", name="uq_song_external_id_platform"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(..., nullable=False)
    title: str = Field(..., nullable=False)
    artist: str = Field(..., nullable=False)
    platform: StreamingPlatforms = Field(
        default=StreamingPlatforms.SPOTIFY, nullable=False
    )
    duration: float = Field(..., nullable=False)
    album_art_url: Optional[str] = Field(default=None, nullable=True)
    is_explicit: Optional[bool] = Field(default=None, nullable=True)

    # Relations
    queue_items: list["QueueItem"] = Relationship(back_populates="song")
