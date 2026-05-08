"""Concurrency tests for QueueRepository against PostgreSQL.

Skip automatically when CROWDROOM_TEST_POSTGRES_URL is not set or
PostgreSQL driver (psycopg2) is not installed.

Usage:
    # Run SQLite tests only (default)
    uv run pytest backend/tests/

    # Also run PostgreSQL tests
    CROWDROOM_TEST_POSTGRES_URL=postgresql://user:pass@localhost/crowdroom_test \\
        uv run pytest backend/tests/test_queue_concurrency.py \\
                         backend/tests/test_queue_concurrency_pg.py -v
"""

import os
import threading
from uuid import uuid4

import pytest
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine, select

skip_pg = pytest.mark.skipif(
    not os.environ.get("CROWDROOM_TEST_POSTGRES_URL"),
    reason="CROWDROOM_TEST_POSTGRES_URL not set",
)


def _make_pg_engine():
    """Create a PostgreSQL engine for testing."""
    url = os.environ["CROWDROOM_TEST_POSTGRES_URL"]
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    return engine


@pytest.fixture(scope="module")
def pg_engine():
    """Module-scoped PostgreSQL engine."""
    engine = _make_pg_engine()
    # Import all models so their __table__ metadata is registered
    from backend.db.models import (
        queue_history,  # noqa: F401
        queue_vote,  # noqa: F401
        room,  # noqa: F401
        session,  # noqa: F401
        song,  # noqa: F401
        user,  # noqa: F401
    )
    from backend.db.models.queue_item import QueueItem  # noqa: F401

    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@skip_pg
class TestPGQueueAddConcurrency:
    """Test atomic add operations under concurrent access against PostgreSQL."""

    def test_concurrent_add_same_group_no_duplicates(self, pg_engine):
        """Multiple threads adding to the same group should produce unique positions."""
        session_id, song_ids = uuid4(), [uuid4() for _ in range(20)]
        errors, results = [], []
        lock = threading.Lock()

        def add_one(idx):
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    item = repo.add_to_queue_atomic(
                        session_id, song_ids[idx], group="manual"
                    )
                    with lock:
                        results.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=add_one, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Add failures: {errors}"
        assert len(results) == 20
        positions = sorted(results)
        assert positions == list(range(20))

    def test_concurrent_add_different_groups_independent(self, pg_engine):
        """Adding to different groups should not interfere with each other."""
        session_id = uuid4()
        manual_items, playlist_items, errors = [], [], []
        lock = threading.Lock()

        def add_manual():
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    for _ in range(10):
                        item = repo.add_to_queue_atomic(
                            session_id, uuid4(), group="manual"
                        )
                        with lock:
                            manual_items.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        def add_playlist():
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    for _ in range(10):
                        item = repo.add_to_queue_atomic(
                            session_id, uuid4(), group="playlist"
                        )
                        with lock:
                            playlist_items.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [
            threading.Thread(target=add_manual),
            threading.Thread(target=add_playlist),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Add failures: {errors}"
        assert len(manual_items) == 10
        assert len(playlist_items) == 10
        assert sorted(manual_items) == list(range(10))
        assert sorted(playlist_items) == list(range(10))


@skip_pg
class TestPGQueueRemoveConcurrency:
    """Test atomic delete operations under concurrent access against PostgreSQL."""

    def test_concurrent_delete_same_item(self, pg_engine):
        """Multiple threads deleting the same item should only succeed once."""
        # Pre-populate: create an item first
        with DBSession(pg_engine) as session:
            from backend.db.models import QueueItem

            item = QueueItem(
                session_id=uuid4(), song_id=uuid4(), position=0, group="manual"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_id = item.id

        delete_results, errors = [], []
        lock = threading.Lock()

        def try_delete():
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    result = repo.delete(item_id)
                    with lock:
                        delete_results.append(result)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=try_delete) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Delete failures: {errors}"
        true_count = delete_results.count(True)
        false_count = delete_results.count(False)
        assert true_count == 1, f"Expected 1 True, got {true_count}: {delete_results}"
        assert false_count == 19, f"Expected 19 False, got {false_count}"

    def test_concurrent_delete_different_items(self, pg_engine):
        """Multiple threads deleting different items should all succeed."""
        with DBSession(pg_engine) as session:
            from backend.db.models import QueueItem

            for i in range(10):
                item = QueueItem(
                    session_id=uuid4(),
                    song_id=uuid4(),
                    position=i,
                    group="manual",
                )
                session.add(item)
            session.commit()
            items = (
                session.exec(select(QueueItem).order_by(QueueItem.position)).all()
            )
            item_ids = [item.id for item in items]

        delete_results, errors = [], []
        lock = threading.Lock()

        def try_delete(idx):
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    result = repo.delete(item_ids[idx])
                    with lock:
                        delete_results.append((idx, result))
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=try_delete, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Delete failures: {errors}"
        assert len(delete_results) == 10
        assert all(r[1] for r in delete_results)


@skip_pg
class TestPGAdvisoryLockIsolation:
    """Test that advisory locks serialize concurrent writes to the same queue."""

    def test_advisory_locks_serialize_same_session(self, pg_engine):
        """Concurrent adds to the same session must produce sequential positions."""
        session_id = uuid4()
        song_ids = [uuid4() for _ in range(30)]  # Higher concurrency stress
        errors, results = [], []
        lock = threading.Lock()

        def add_one(idx):
            with DBSession(pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    item = repo.add_to_queue_atomic(
                        session_id, song_ids[idx], group="manual"
                    )
                    with lock:
                        results.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=add_one, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Add failures: {errors}"
        assert len(results) == 30
        positions = sorted(results)
        assert positions == list(range(30)), (
            f"Expected sequential 0..29, got: {positions}"
        )
