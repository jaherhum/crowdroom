"""Song management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.songs.dependencies import get_song_service
from backend.schemas.song import CreateSong, ReadSong, UpdateSong
from backend.services.song_service import SongService

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/", response_model=list[ReadSong], status_code=status.HTTP_200_OK)
async def get_songs(
    song_service: SongService = Depends(get_song_service),
) -> list[ReadSong]:
    """Retrieve a list of all songs.

    Args:
        song_service (SongService): The injected song service.

    Returns:
        list[ReadSong]: A list of song schemas.
    """
    return song_service.get_all_songs()


@router.get(
    "/by-external/{external_id}",
    response_model=ReadSong,
    status_code=status.HTTP_200_OK,
)
async def get_song_by_external_id(
    external_id: str,
    platform: str = "spotify",
    song_service: SongService = Depends(get_song_service),
) -> ReadSong:
    """Retrieve a song by its external platform ID.

    Args:
        external_id: The platform-specific track identifier.
        platform: The streaming platform name (default: spotify).
        song_service: The injected song service.

    Returns:
        ReadSong: The song schema.

    Raises:
        HTTPException: 404 if no song found with the given external_id.
    """
    song = song_service.get_by_external_id(external_id, platform)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song with external_id '{external_id}' not found.",
        )
    return song


@router.get("/{song_id}", response_model=ReadSong, status_code=status.HTTP_200_OK)
async def get_song(
    song_id: UUID,
    song_service: SongService = Depends(get_song_service),
) -> ReadSong:
    """Retrieve a specific song by its ID.

    Args:
        song_id (UUID): The unique identifier of the song.
        song_service (SongService): The injected song service.

    Returns:
        ReadSong: The song schema.
    """
    return song_service.get_song(song_id)


@router.post("/", response_model=ReadSong, status_code=status.HTTP_201_CREATED)
async def create_song(
    song_data: CreateSong,
    song_service: SongService = Depends(get_song_service),
) -> ReadSong:
    """Create a new song.

    Args:
        song_data (CreateSong): The schema containing song details.
        song_service (SongService): The injected song service.

    Returns:
        ReadSong: The newly created song schema.
    """
    return song_service.create_song(song_data)


@router.patch("/{song_id}", response_model=ReadSong, status_code=status.HTTP_200_OK)
async def update_song(
    song_id: UUID,
    song_data: UpdateSong,
    song_service: SongService = Depends(get_song_service),
) -> ReadSong:
    """Update an existing song.

    Args:
        song_id (UUID): The unique identifier of the song to update.
        song_data (UpdateSong): The schema containing the fields to update.
        song_service (SongService): The injected song service.

    Returns:
        ReadSong: The updated song schema.
    """
    return song_service.update_song(song_id, song_data)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    song_id: UUID,
    song_service: SongService = Depends(get_song_service),
) -> None:
    """Delete a song from the system.

    Args:
        song_id (UUID): The unique identifier of the song to delete.
        song_service (SongService): The injected song service.
    """
    song_service.delete_song(song_id)
