"""Song API dependencies."""

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.database import get_session
from backend.repositories.song_repo import SongRepository
from backend.services.song_service import SongService


def get_song_repo(session: AsyncSession = Depends(get_session)) -> SongRepository:
    """Dependency that provides a SongRepository instance."""
    return SongRepository(session)


def get_song_service(
    song_repo: SongRepository = Depends(get_song_repo),
) -> SongService:
    """Dependency that provides a SongService instance."""
    return SongService(song_repo)
