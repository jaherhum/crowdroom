"""Search functionality routes for the API."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from backend.api.auth.dependencies import get_current_user
from backend.api.search.dependencies import get_music_service, get_song_service
from backend.core.exceptions import EntityNotFoundException
from backend.db.models.user import User
from backend.schemas.song import CreateSong
from backend.schemas.song_metadata import ReadSongMetadata
from backend.services.music_service import MusicService
from backend.services.song_service import SongService

router = APIRouter(prefix="/search", tags=["search"])

def _persist_song(metadata: ReadSongMetadata, song_service: SongService) -> None:
    if metadata.external_id is None or metadata.platform is None:
        return

    song_data = CreateSong(
        external_id=metadata.external_id,
        title=metadata.title,
        artist=metadata.artist,
        platform=metadata.platform,
        duration=metadata.duration_ms / 1000 if metadata.duration_ms else 0.0,
        album_art_url=metadata.album_art_url,
        is_explicit=metadata.is_explicit,
    )
    song_service.get_or_create_song(song_data)

@router.get(
    "/",
    response_model=list[ReadSongMetadata],
    status_code=status.HTTP_200_OK,
)
async def search_tracks(
    room_id: UUID,
    q: str = Query(..., min_length=1, max_length=255),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
    song_service: SongService = Depends(get_song_service),
) -> list[ReadSongMetadata]:
    """Search tracks on the room's streaming platform.

    Args:
        room_id: Room whose platform connection to use.
        q: Search query string.
        current_user: Authenticated user from JWT.
        music_service: Service for platform search.
        song_service: Service for song persistence.

    Returns:
        List of matching track metadata.

    Raises:
        HTTPException: 404 if room or platform connection not found.
    """
    try:
        results = await music_service.search(room_id, q)
    except EntityNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e

    for metadata in results:
        _persist_song(metadata, song_service)

    return results

@router.get(
    "/{external_id}",
    response_model=ReadSongMetadata,
    status_code=status.HTTP_200_OK,
)
async def get_track_metadata(
    external_id: str,
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
    song_service: SongService = Depends(get_song_service),
) -> ReadSongMetadata:
    """Retrieve metadata for a track by its external platform ID.

    Args:
        external_id: Platform-specific track identifier.
        room_id: Room whose platform connection to use.
        current_user: Authenticated user from JWT.
        music_service: Service for platform metadata lookup.
        song_service: Service for song persistence.

    Returns:
        Track metadata from the streaming platform.

    Raises:
        HTTPException: 404 if room/connection not found or track not found.
    """
    try:
        metadata = await music_service.get_metadata(room_id, external_id)
    except EntityNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e

    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{external_id}' not found on platform.",
        )

    _persist_song(metadata, song_service)

    return metadata
