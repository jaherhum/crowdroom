"""Concurrency tests for QueueRepository atomic operations.

Uses a temporary SQLite database file so that multiple threads can open
independent DBSession instances and genuinely contend for locks.
Validates that queue add/remove operations remain consistent under
concurrent access from multiple threads.
"""

import tempfile
import threading
from uuid import uuid4

from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine, select

from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_repo import QueueRepository


def _make_temp_db():
    """Create a temporary SQLite file + engine for concurrency tests."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}")
    # Import all models so their __table__ metadata is registered
    from backend.db.models import (  # noqa: F401
        queue_history,
        queue_vote,
        room,
        song,
        user,
    )

    SQLModel.metadata.create_all(engine)
    return engine, tmp.name


class TestQueueAddConcurrency:
    """Test atomic add operations under concurrent access."""

    def test_concurrent_add_same_group_no_duplicates(self):
        """Multiple threads adding to the same group should produce unique positions."""
        engine, _ = _make_temp_db()
        session_id, song_ids = uuid4(), [uuid4() for _ in range(10)]

        errors = []
        results = []
        lock = threading.Lock()

        def add_one(idx):
            with DBSession(engine) as session:
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

        threads = [threading.Thread(target=add_one, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Add failures: {errors}"
        assert len(results) == 10

        # Positions should be unique and sequential: 0..9
        positions = sorted(results)
        assert positions == list(range(10))

    def test_concurrent_add_different_groups_independent(self):
        """Adding to different groups should not interfere with each other."""
        engine, _ = _make_temp_db()
        session_id = uuid4()

        manual_items = []
        playlist_items = []
        errors = []
        lock = threading.Lock()

        def add_manual():
            with DBSession(engine) as session:
                repo = QueueRepository(session)
                try:
                    for _ in range(5):
                        item = repo.add_to_queue_atomic(
                            session_id, uuid4(), group="manual"
                        )
                        with lock:
                            manual_items.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        def add_playlist():
            with DBSession(engine) as session:
                repo = QueueRepository(session)
                try:
                    for _ in range(5):
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
        assert len(manual_items) == 5
        assert len(playlist_items) == 5

        # Each group has positions 0..4 independently
        manual_positions = sorted(manual_items)
        playlist_positions = sorted(playlist_items)
        assert manual_positions == list(range(5))
        assert playlist_positions == list(range(5))


class TestQueueRemoveConcurrency:
    """Test atomic delete operations under concurrent access."""

    def test_concurrent_delete_same_item(self):
        """Multiple threads deleting the same item should only succeed once."""
        engine, _ = _make_temp_db()

        # Pre-populate: create an item first (no begin/commit nesting)
        with DBSession(engine) as session:
            item = QueueItem(
                session_id=uuid4(),
                song_id=uuid4(),
                position=0,
                group="manual",
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_id = item.id

        delete_results = []
        errors = []
        lock = threading.Lock()

        def try_delete():
            with DBSession(engine) as session:
                repo = QueueRepository(session)
                try:
                    result = repo.delete(item_id)
                    with lock:
                        delete_results.append(result)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=try_delete) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Delete failures: {errors}"
        # With proper BEGIN IMMEDIATE, exactly one True (deleted), rest False
        true_count = delete_results.count(True)
        false_count = delete_results.count(False)
        assert true_count == 1, f"Expected 1 True, got {true_count}: {delete_results}"
        assert false_count == 9, f"Expected 9 False, got {false_count}"

    def test_concurrent_delete_different_items(self):
        """Multiple threads deleting different items should all succeed."""
        engine, _ = _make_temp_db()

        # Pre-populate: create multiple items (commit after adding)
        with DBSession(engine) as session:
            item_ids = []
            for i in range(5):
                item = QueueItem(
                    session_id=uuid4(),
                    song_id=uuid4(),
                    position=i,
                    group="manual",
                )
                session.add(item)
            session.commit()
            # Refresh all after commit to get PKs populated
            items = session.exec(select(QueueItem).order_by(QueueItem.position)).all()
            for item in items:
                item_ids.append(item.id)

        delete_results = []
        errors = []
        lock = threading.Lock()

        def try_delete(idx):
            with DBSession(engine) as session:
                repo = QueueRepository(session)
                try:
                    result = repo.delete(item_ids[idx])
                    with lock:
                        delete_results.append((idx, result))
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=try_delete, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Delete failures: {errors}"
        assert len(delete_results) == 5
        assert all(r[1] for r in delete_results)  # All should return True
