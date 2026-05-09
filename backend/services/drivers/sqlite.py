"""SQLite driver: file-level locking via BEGIN IMMEDIATE."""

from contextlib import AbstractContextManager
from typing import Any

from sqlmodel import Session as DBSession
from sqlmodel import text


class SQLiteQueueLock(AbstractContextManager):
    """Context manager that acquires BEGIN IMMEDIATE on a SQLite session."""

    def __init__(self, session: DBSession, *args: Any, **kwargs: Any) -> None:
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

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Do NOT rollback — the caller manages commit/rollback."""
        self._locked = False
