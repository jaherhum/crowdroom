"""Search API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.repositories.song_repo import SongRepository
from backend.services.music_service import MusicService
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.song_service import SongService


def get_room_repo(session: DBSession = Depends(get_session)) -> RoomRepository:
    """Provide a RoomRepository bound to the current database session."""
    return RoomRepository(session)


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Provide a SessionRepository bound to the current database session."""
    return SessionRepository(session)


def get_platform_connection_repo(
    session: DBSession = Depends(get_session),
) -> PlatformConnectionRepo:
    """Provide a PlatformConnectionRepo bound to the current database session."""
    return PlatformConnectionRepo(session)


def get_platform_connection_service(
    repo: PlatformConnectionRepo = Depends(get_platform_connection_repo),
) -> PlatformConnectionService:
    """Provide a PlatformConnectionService wired with its repository."""
    return PlatformConnectionService(repo)


def get_music_service(
    platform_connection_service: PlatformConnectionService = Depends(
        get_platform_connection_service
    ),
    room_repo: RoomRepository = Depends(get_room_repo),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> MusicService:
    """Provide a MusicService wired with all required dependencies."""
    return MusicService(
        platform_connection_service=platform_connection_service,
        room_repo=room_repo,
        session_repo=session_repo,
    )


def get_song_repo(session: DBSession = Depends(get_session)) -> SongRepository:
    """Provide a SongRepository bound to the current database session."""
    return SongRepository(session)


def get_song_service(
    song_repo: SongRepository = Depends(get_song_repo),
) -> SongService:
    """Provide a SongService wired with its repository."""
    return SongService(song_repo)
