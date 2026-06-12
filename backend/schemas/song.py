"""Song schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models.enum import StreamingPlatforms


class CreateSong(BaseModel):
    """Schema for creating a new song.

    Attributes:
        external_id (str): The unique identifier from the streaming platform.
        title (str): The full title of the song.
        artist (str): The name of the artist or band.
        platform (StreamingPlatforms): The streaming service the song was fetched from.
        duration (float): The duration of the song in seconds.
        album_art_url (str | None): The URL pointing to the album artwork.
        is_explicit (bool | None): Flag indicating explicit content.
    """

    external_id: str = Field(
        ..., description="The unique identifier from the streaming platform."
    )
    title: str = Field(..., description="The full title of the song.")
    artist: str = Field(..., description="The name of the artist or band.")
    platform: StreamingPlatforms = Field(
        default=StreamingPlatforms.SPOTIFY,
        description="The streaming service the song was fetched from.",
    )
    duration: float = Field(..., description="The duration of the song in seconds.")
    album_art_url: str | None = Field(
        None, description="The URL pointing to the album artwork."
    )
    is_explicit: bool | None = Field(
        None, description="Flag indicating if the content is marked as explicit."
    )


class UpdateSong(BaseModel):
    """Schema for updating an existing song.

    Attributes:
        title (str | None): The full title of the song.
        artist (str | None): The name of the artist or band.
        duration (float | None): The duration of the song in seconds.
        album_art_url (str | None): The URL pointing to the album artwork.
        is_explicit (bool | None): Flag indicating explicit content.
    """

    title: str | None = Field(None, description="The full title of the song.")
    artist: str | None = Field(None, description="The name of the artist or band.")
    duration: float | None = Field(
        None, description="The duration of the song in seconds."
    )
    album_art_url: str | None = Field(
        None, description="The URL pointing to the album artwork."
    )
    is_explicit: bool | None = Field(
        None, description="Flag indicating if the content is marked as explicit."
    )


class ReadSong(BaseModel):
    """Schema for song data returned by the API.

    Attributes:
        id (UUID): The unique internal identifier of the song.
        external_id (str): The unique identifier from the streaming platform.
        title (str): The display title of the song.
        artist (str): The name of the performing artist or group.
        platform (StreamingPlatforms): The streaming service of origin.
        duration (float): The total length of the song in seconds.
        album_art_url (str | None): The URL to the cover art image.
        is_explicit (bool | None): Indicates explicit content.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The unique internal identifier of the song.")
    external_id: str = Field(
        ..., description="The unique identifier from the streaming platform."
    )
    title: str = Field(..., description="The display title of the song.")
    artist: str = Field(..., description="The name of the performing artist.")
    platform: StreamingPlatforms = Field(
        ..., description="The streaming service of origin."
    )
    duration: float = Field(..., description="The total length in seconds.")
    album_art_url: str | None = Field(
        None, description="The URL to the cover art image."
    )
    is_explicit: bool | None = Field(None, description="Indicates explicit content.")
