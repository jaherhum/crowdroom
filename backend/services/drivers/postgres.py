"""PostgreSQL driver: advisory locking via pg_advisory_xact_lock."""

import hashlib
from contextlib import AbstractContextManager
from typing import Any
from uuid import UUID

from sqlmodel import Session as DBSession
from sqlmodel import text


class PGQueueLock(AbstractContextManager):
    """Acquires advisory lock for a queue group in PostgreSQL."""

    def __init__(self, session: DBSession, session_id: UUID, group: str) -> None:
        """Initialize the PostgreSQL advisory lock with a unique key.

        Derives a 31-bit lock key from an MD5 hash of the session and
        queue group name so that different sessions/groups get distinct
        locks.

        Args:
            session: Database session for executing the lock query.
            session_id: UUID identifying the session whose queue to lock.
            group: Queue group name included in the lock key derivation.
        """
        self._session = session
        key = f"{session_id}:{group}"
        self._lock_key = int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31 - 1)

    def __enter__(self) -> "PGQueueLock":
        """Acquire a PostgreSQL advisory transaction lock.

        Executes ``SELECT pg_advisory_xact_lock(:key)`` which blocks until
        no other transaction holds the same lock. The lock is automatically
        released when the transaction commits or rolls back.

        Returns:
            The PGQueueLock instance (self).
        """
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": self._lock_key},
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the context manager without action.

        The advisory lock is automatically released by PostgreSQL when the
        transaction ends (commit or rollback), so no manual cleanup is needed.
        """
