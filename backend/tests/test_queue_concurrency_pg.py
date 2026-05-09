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
    # Use CASCADE to break circular FKs (users <-> rooms)
    with engine.connect() as conn:
        from sqlalchemy import text

        drop_sql = (
            "DROP TABLE IF EXISTS queue_votes, "
            "queue_histories, queue_items, sessions, "
            "rooms, users, songs CASCADE"
        )
        conn.execute(text(drop_sql))
        conn.commit()


@pytest.fixture
def pg_seed(pg_engine):
    """Per-test fixture that seeds fresh User+Room+Session+Song data.

    Clears cached seed data before each test and removes any leftover
    records from previous test runs to ensure idempotency.
    Returns (session_id, seed_song_ids_list).
    """
    # Clear the module-level cache
    if hasattr(_ensure_seed_data, "_cached"):
        del _ensure_seed_data._cached
    # Clean up any leftover seed data from previous tests (reverse FK order)
    with DBSession(pg_engine) as s:
        from sqlmodel import delete

        from backend.db.models import (
            QueueHistory,
            QueueItem,
            QueueVote,
            Room,
            Session,
            Song,
            User,
        )

        s.exec(delete(QueueVote))
        s.exec(delete(QueueHistory))
        s.exec(delete(QueueItem).where(QueueItem.session_id != None))  # noqa: E711
        s.exec(delete(Session))
        s.exec(delete(Room))
        s.exec(delete(User).where(User.username == "test-user"))
        s.exec(delete(Song).where(Song.title.like("Test Seed Song%")))
        s.commit()
    return _ensure_seed_data(pg_engine)


def _ensure_seed_data(pg_engine):
    """Seed User+Room+Session+Song records for FK-constrained PG tests.

    Chain: User (username) -> Room (host_user_id, room_name) -> Session (room_id)
    Seed 50 Songs so all add-to-queue threads have valid FK references.
    Cached globally. Returns (session_id, seed_song_ids_list).
    """
    from backend.db.models.enum import PlaybackStatus, StreamingPlatforms
    from backend.db.models.room import Room
    from backend.db.models.session import Session as SessionModel
    from backend.db.models.song import Song
    from backend.db.models.user import User

    if not hasattr(_ensure_seed_data, "_cached"):
        uid = uuid4()
        room_id = uuid4()
        sid = uuid4()
        seed_song_ids = [uuid4() for _ in range(50)]
        with DBSession(pg_engine) as s:
            user = User(id=uid, username="test-user")
            s.add(user)
            s.flush()  # Ensure User exists before Room references it
            room = Room(id=room_id, host_user_id=uid, room_name="test-room")
            s.add(room)
            s.flush()
            sess = SessionModel(
                id=sid,
                room_id=room_id,
                current_platform=StreamingPlatforms.SPOTIFY,
                playback_status=PlaybackStatus.STOPPED,
            )
            s.add(sess)
            for i, song_uid in enumerate(seed_song_ids):
                song = Song(
                    id=song_uid,
                    external_id=f"test-seed-song-{i}",
                    title=f"Test Seed Song {i}",
                    artist="Test Artist",
                    platform=StreamingPlatforms.SPOTIFY,
                    duration=180.0,
                )
                s.add(song)
            s.commit()
        _ensure_seed_data._cached = (sid, seed_song_ids)
    return _ensure_seed_data._cached


# Store pg_engine reference for use in inner thread functions
_current_pg_engine = None


@skip_pg
class TestPGQueueAddConcurrency:
    """Test atomic add operations under concurrent access against PostgreSQL."""

    def test_concurrent_add_same_group_no_duplicates(self, pg_engine, pg_seed):
        """Multiple threads adding to the same group should produce unique positions."""
        global _current_pg_engine
        _current_pg_engine = pg_engine
        session_id, seed_songs = pg_seed
        song_ids = seed_songs[:20]
        errors, results = [], []
        lock = threading.Lock()

        def add_one(idx):
            with DBSession(_current_pg_engine) as session:
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
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Add failures: {errors}"
        assert len(results) == 20
        positions = sorted(results)
        assert positions == list(range(20))

    def test_concurrent_add_different_groups_independent(self, pg_engine, pg_seed):
        """Adding to different groups should not interfere with each other."""
        global _current_pg_engine
        _current_pg_engine = pg_engine
        session_id, seed_songs = pg_seed
        manual_song_ids = seed_songs[:10]
        playlist_song_ids = seed_songs[10:20]
        manual_items, playlist_items, errors = [], [], []
        lock = threading.Lock()

        def add_manual(idx):
            with DBSession(_current_pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    item = repo.add_to_queue_atomic(
                        session_id, manual_song_ids[idx], group="manual"
                    )
                    with lock:
                        manual_items.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        def add_playlist(idx):
            with DBSession(_current_pg_engine) as session:
                from backend.repositories.queue_repo import QueueRepository

                repo = QueueRepository(session)
                try:
                    item = repo.add_to_queue_atomic(
                        session_id, playlist_song_ids[idx], group="playlist"
                    )
                    with lock:
                        playlist_items.append(item.position)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [
            threading.Thread(target=add_manual, args=(i,)) for i in range(10)
        ] + [threading.Thread(target=add_playlist, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Add failures: {errors}"
        assert len(manual_items) == 10
        assert len(playlist_items) == 10
        assert sorted(manual_items) == list(range(10))
        assert sorted(playlist_items) == list(range(10))


@skip_pg
class TestPGQueueRemoveConcurrency:
    """Test atomic delete operations under concurrent access against PostgreSQL."""

    def test_concurrent_delete_same_item(self, pg_engine, pg_seed):
        """Multiple threads deleting the same item should only succeed once."""
        global _current_pg_engine
        _current_pg_engine = pg_engine
        sess_id, seed_songs = pg_seed
        song_id = seed_songs[0]
        with DBSession(pg_engine) as s:
            from backend.db.models import QueueItem

            item = QueueItem(
                session_id=sess_id,
                song_id=song_id,
                position=0,
                group="manual",
            )
            s.add(item)
            s.commit()
            s.refresh(item)
            item_id = item.id

        delete_results, errors = [], []
        lock = threading.Lock()

        def try_delete():
            with DBSession(_current_pg_engine) as session:
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
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Delete failures: {errors}"
        true_count = delete_results.count(True)
        false_count = delete_results.count(False)
        assert true_count == 1, f"Expected 1 True, got {true_count}: {delete_results}"
        assert false_count == 19, f"Expected 19 False, got {false_count}"

    def test_concurrent_delete_different_items(self, pg_engine, pg_seed):
        """Multiple threads deleting different items should all succeed."""
        global _current_pg_engine
        _current_pg_engine = pg_engine
        sess_id, seed_songs = pg_seed
        song_id = seed_songs[0]  # Reuse seeded song (unique positions)
        with DBSession(pg_engine) as s:
            from backend.db.models import QueueItem

            for i in range(10):
                item = QueueItem(
                    session_id=sess_id,
                    song_id=song_id,
                    position=i,
                    group="manual",
                )
                s.add(item)
            s.commit()
            items = s.exec(select(QueueItem).order_by(QueueItem.position)).all()
            item_ids = [item.id for item in items]

        delete_results, errors = [], []
        lock = threading.Lock()

        def try_delete(idx):
            with DBSession(_current_pg_engine) as session:
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
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Delete failures: {errors}"
        assert len(delete_results) == 10
        assert all(r[1] for r in delete_results)


@skip_pg
class TestPGAdvisoryLockIsolation:
    """Test that advisory locks serialize concurrent writes to the same queue."""

    def test_advisory_locks_serialize_same_session(self, pg_engine, pg_seed):
        """Concurrent adds to the same session must produce sequential positions."""
        global _current_pg_engine
        _current_pg_engine = pg_engine
        session_id, seed_songs = pg_seed
        song_ids = seed_songs[:30]  # Use seeded songs (FK-safe)
        errors, results = [], []
        lock = threading.Lock()

        def add_one(idx):
            with DBSession(_current_pg_engine) as session:
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
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Add failures: {errors}"
        assert len(results) == 30
        positions = sorted(results)
        assert positions == list(range(30)), (
            f"Expected sequential 0..29, got: {positions}"
        )
