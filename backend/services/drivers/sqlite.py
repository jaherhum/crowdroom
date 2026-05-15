"""SQLite driver: file-level locking via BEGIN IMMEDIATE."""

from contextlib import AbstractContextManager
from typing import Any

from sqlmodel import Session as DBSession
from sqlmodel import text


class SQLiteQueueLock(AbstractContextManager):
    """Context manager that acquires BEGIN IMMEDIATE on a SQLite session."""

    def __init__(self, session: DBSession, *args: Any, **kwargs: Any) -> None:
        """Initialize the SQLite file-level lock with a database session.

        Args:
            session: Database session for executing BEGIN IMMEDIATE.
            *args: Additional positional arguments (unused, forwarded).
            **kwargs: Additional keyword arguments (unused, forwarded).
        """
        self._session = session
        self._locked = False

    def __enter__(self) -> "SQLiteQueueLock":
        """Acquire a BEGIN IMMEDIATE lock on the SQLite database.

        This blocks other connections from writing while holding the lock,
        preventing race conditions during concurrent queue operations.
        Exceptions during lock acquisition are silently swallowed.

        Returns:
            The SQLiteQueueLock instance (self).
        """
        try:
            self._session.execute(text("BEGIN IMMEDIATE"))
            self._locked = True
        except Exception:
            pass
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Reset the internal lock flag without altering transaction state.

        Does not commit or rollback — that responsibility belongs to the
        caller who invoked this context manager.
        """
        self._locked = False
