"""Queue API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.queue_repo import QueueRepository
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.services.queue_history_service import QueueHistoryService
from backend.services.queue_service import QueueService


def get_queue_repo(session: DBSession = Depends(get_session)) -> QueueRepository:
    """Dependency that provides a QueueRepository instance."""
    return QueueRepository(session)


def get_queue_service(
    queue_repo: QueueRepository = Depends(get_queue_repo),
) -> QueueService:
    """Dependency that provides a QueueService instance."""
    return QueueService(queue_repo)


def get_queue_vote_repo(
    session: DBSession = Depends(get_session),
) -> QueueVoteRepository:
    """Dependency that provides a QueueVoteRepository instance."""
    return QueueVoteRepository(session)


def get_queue_history_repo(
    session: DBSession = Depends(get_session),
) -> QueueHistoryRepository:
    """Dependency that provides a QueueHistoryRepository instance."""
    return QueueHistoryRepository(session)

