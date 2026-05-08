"""Base class for database-specific queue locks."""

from contextlib import AbstractContextManager


class BaseQueueLock(AbstractContextManager):
    """Abstract context manager for acquiring database locks."""
