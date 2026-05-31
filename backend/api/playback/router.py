"""Playback control API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth.dependencies import get_current_user
from backend.api.playback.dependencies import get_playback_control_service
from backend.core.exceptions import EntityNotFoundException, ForbiddenException
from backend.db.models.user import User
from backend.schemas.playback import PlaybackStateResponse, PlayRequest
from backend.services.playback_control_service import PlaybackControlService

router = APIRouter(prefix="/playback", tags=["playback"])


@router.post("/play", status_code=status.HTTP_204_NO_CONTENT)
async def play(
    body: PlayRequest,
    current_user: User = Depends(get_current_user),
    service: PlaybackControlService = Depends(get_playback_control_service),
) -> None:
    """Start playback of a song on the host's Spotify device."""
    if not current_user.room_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in any room",
        )
    try:
        await service.play(
            room_id=current_user.room_id,
            user_id=current_user.id,
            song_id=body.song_id,
            device_id=body.device_id,
        )
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause(
    current_user: User = Depends(get_current_user),
    service: PlaybackControlService = Depends(get_playback_control_service),
) -> None:
    """Pause the host's Spotify playback."""
    if not current_user.room_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in any room",
        )
    try:
        await service.pause(
            room_id=current_user.room_id, user_id=current_user.id
        )
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/skip", status_code=status.HTTP_204_NO_CONTENT)
async def skip(
    current_user: User = Depends(get_current_user),
    service: PlaybackControlService = Depends(get_playback_control_service),
) -> None:
    """Skip to the next track on the host's Spotify."""
    if not current_user.room_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in any room",
        )
    try:
        await service.skip(
            room_id=current_user.room_id, user_id=current_user.id
        )
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/current", response_model=PlaybackStateResponse | None)
async def get_current_playback(
    current_user: User = Depends(get_current_user),
    service: PlaybackControlService = Depends(get_playback_control_service),
) -> PlaybackStateResponse | None:
    """Get the current Spotify playback state for the room."""
    if not current_user.room_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in any room",
        )
    try:
        state = await service.get_current_playback(
            room_id=current_user.room_id, user_id=current_user.id
        )
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    if state is None:
        return None
    return PlaybackStateResponse(
        is_playing=state.is_playing,
        track_id=state.track_id,
        progress_ms=state.progress_ms,
        device_id=state.device_id,
    )
