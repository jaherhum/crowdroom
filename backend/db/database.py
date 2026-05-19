"""Database connection, session management, and dialect detection."""

from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine

from backend.core.config import settings

# Import all models so SQLAlchemy knows about them before create_all()
from backend.db.models import *  # noqa: F401,F403

db_url = settings.DATABASE_URL

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(db_url, connect_args=connect_args)


def create_db_and_tables():
    """Creates all database tables defined in the SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Provides a database session for dependency injection.

    Yields:
        DBSession: A database session instance.
    """
    with DBSession(engine) as session:
        yield session
