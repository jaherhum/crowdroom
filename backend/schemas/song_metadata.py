from pydantic import BaseModel, Field

from backend.db.models import StreamingPlatforms


class ReadSongMetadata(BaseModel):
    title: str = Field(..., description="Title of the song")
    artist: str = Field(..., description="Primary performing artist")
    album: str = Field(default="", description="Album or release name")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    isrc: str | None = Field(None, description="International Standard Recording Code")
    platform: StreamingPlatforms | None = Field(None, description="Source streaming platform")
    album_art_url: str | None = Field(None, description="URL to the track cover art")
    artists: list[str] = Field(default_factory=list, description="All credited artists")
    is_explicit: bool = False
    external_id: str | None = Field(None, description="ID on the source platform (e.g. MBID for MusicBrainz)")