"""Playback control API dependencies."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.api.rooms.dependencies import get_room_service
from backend.api.session.dependencies import get_playback_service, get_session_repo
from backend.db.database import get_session
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.repositories.session_repo import SessionRepository
from backend.repositories.song_repo import SongRepository
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.playback_control_service import PlaybackControlService
from backend.services.playback_service import PlaybackService
from backend.services.room_service import RoomService


def get_song_repo(session: DBSession = Depends(get_session)) -> SongRepository:
    """Provide a SongRepository bound to the current database session."""
    return SongRepository(session)


def get_platform_connection_service(
    session: DBSession = Depends(get_session),
) -> PlatformConnectionService:
    """Provide a PlatformConnectionService."""
    repo = PlatformConnectionRepo(session)
    return PlatformConnectionService(repo)


def get_playback_control_service(
    room_service: RoomService = Depends(get_room_service),
    session_repo: SessionRepository = Depends(get_session_repo),
    song_repo: SongRepository = Depends(get_song_repo),
    platform_connection_service: PlatformConnectionService = Depends(
        get_platform_connection_service
    ),
    playback_service: PlaybackService = Depends(get_playback_service),
) -> PlaybackControlService:
    """Provide a PlaybackControlService wired with all dependencies."""
    return PlaybackControlService(
        room_service=room_service,
        session_repo=session_repo,
        song_repo=song_repo,
        platform_connection_service=platform_connection_service,
        playback_service=playback_service,
    )
