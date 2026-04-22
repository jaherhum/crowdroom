from typing import Optional
from uuid import UUID

from db.models.enum import StreamingPlatforms
from pydantic import BaseModel, Field

# This class is not intended to use, may be removed in the future.
# class CreateSong(BaseModel):
#     title: str
#     artist: str
#     platform: StreamingPlatforms
#     duration: float
#     album_art_url: str
#     is_explicit: bool

class ReadSong(BaseModel):
    """Schema for the song data returned by the API.

    Provides a complete representation of a song as it exists in the system,
    including its metadata and origin platform.

    Attributes:
        id (UUID): The unique internal identifier of the song.
        external_id (str): The unique identifier from the original streaming platform.
        title (str): The display title of the song.
        artist (str): The name of the performing artist or group.
        platform (StreamingPlatforms): The streaming service where the song originated.
        duration (float): The total length of the song in seconds.
        album_art_url (Optional[str]): The URL to the song's cover art image.
        is_explicit (Optional[bool]): Indicates if the song contains explicit content.
    """
    id: UUID = Field(..., description="The unique internal identifier of the song.")
    external_id: str = Field(..., description="The unique identifier provided by the external streaming platform.")
    title: str = Field(..., description="The full title of the song.")
    artist: str = Field(..., description="The name of the artist or band.")
    platform: StreamingPlatforms = Field(..., description="The streaming service the song was fetched from.")
    duration: float = Field(..., description="The duration of the song in seconds.")
    album_art_url: Optional[str] = Field(None, description="The URL pointing to the album artwork.")
    is_explicit: Optional[bool] = Field(None, description="Flag indicating if the content is marked as explicit.")
