"""PostgreSQL driver: advisory locking via pg_advisory_xact_lock."""

import hashlib
from uuid import UUID

from sqlmodel import Session as DBSession
from sqlmodel import text

from backend.services.drivers.base import BaseQueueLock


class PGQueueLock(BaseQueueLock):
    """Acquires advisory lock for a queue group in PostgreSQL.

    Uses ``pg_advisory_xact_lock()`` — auto-released at transaction end.
    """

    def __init__(self, session: DBSession, session_id: UUID, group: str) -> None:
        self._session = session
        key = f"{session_id}:{group}"
        self._lock_key = int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31 - 1)

    def __enter__(self) -> "PGQueueLock":
        """Acquire pg_advisory_xact_lock for this queue group."""
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": self._lock_key},
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Advisory lock is auto-released at transaction end."""
        pass

