"""Song API dependencies."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.song_repo import SongRepository
from backend.services.song_service import SongService


def get_song_repo(session: DBSession = Depends(get_session)) -> SongRepository:
    """Provide a SongRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A SongRepository instance for song data access.
    """
    return SongRepository(session)


def get_song_service(
    song_repo: SongRepository = Depends(get_song_repo),
) -> SongService:
    """Provide a SongService wired with its required dependencies.

    Args:
        song_repo: SongRepository from dependency injection.

    Returns:
        A SongService instance for song business logic.
    """
    return SongService(song_repo)
