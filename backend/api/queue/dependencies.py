"""Queue API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.queue_repo import QueueRepository
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.services.queue_service import QueueService


def get_queue_repo(session: DBSession = Depends(get_session)) -> QueueRepository:
    """Provide a QueueRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A QueueRepository instance for queue item data access.
    """
    return QueueRepository(session)


def get_queue_service(
    queue_repo: QueueRepository = Depends(get_queue_repo),
) -> QueueService:
    """Provide a QueueService wired with its required dependencies.

    Args:
        queue_repo: QueueRepository from dependency injection.

    Returns:
        A QueueService instance for queue business logic.
    """
    return QueueService(queue_repo)


def get_queue_vote_repo(
    session: DBSession = Depends(get_session),
) -> QueueVoteRepository:
    """Provide a QueueVoteRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A QueueVoteRepository instance for skip vote data access.
    """


def get_queue_history_repo(
    session: DBSession = Depends(get_session),
) -> QueueHistoryRepository:
    """Provide a QueueHistoryRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A QueueHistoryRepository instance for playback history data access.
    """
    return QueueHistoryRepository(session)
