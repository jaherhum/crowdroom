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

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Advisory lock is auto-released at transaction end."""
        pass
