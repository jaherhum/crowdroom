"""SQLite driver: file-level locking via BEGIN IMMEDIATE."""

from sqlmodel import Session as DBSession
from sqlmodel import text

from backend.services.drivers.base import BaseQueueLock


class SQLiteQueueLock(BaseQueueLock):
    """Context manager that acquires BEGIN IMMEDIATE on a SQLite session."""

    def __init__(self, session: DBSession, *args, **kwargs) -> None:
        self._session = session
        self._locked = False

    def __enter__(self) -> "SQLiteQueueLock":
        """Acquire BEGIN IMMEDIATE on the SQLite session."""
        try:
            self._session.execute(text("BEGIN IMMEDIATE"))
            self._locked = True
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Do NOT rollback — the caller manages commit/rollback."""
        self._locked = False

