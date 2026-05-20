"""Main entry point for the FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.auth.router import router as auth_router
from backend.api.platform_connections.router import (
    router as platform_connections_router,
)
from backend.api.queue.router import router as queue_router
from backend.api.rooms.router import router as rooms_router
from backend.api.search.router import router as search_router
from backend.api.session.router import router as session_router
from backend.api.songs.router import router as songs_router
from backend.api.users.router import router as user_router
from backend.core.config import settings
from backend.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application lifecycle."""
    print("Creating tables in database...")
    create_db_and_tables()
    yield
    print("App closed.")


app = FastAPI(lifespan=lifespan)


app.include_router(
    platform_connections_router,
    prefix=settings.API_V1_STR,
    tags=["platform_connections"],
)
app.include_router(rooms_router, prefix=settings.API_V1_STR, tags=["rooms"])
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(queue_router, prefix=settings.API_V1_STR, tags=["queue"])
app.include_router(search_router, prefix=settings.API_V1_STR, tags=["search"])
app.include_router(session_router, prefix=settings.API_V1_STR, tags=["session"])
app.include_router(songs_router, prefix=settings.API_V1_STR, tags=["songs"])
app.include_router(user_router, prefix=settings.API_V1_STR, tags=["users"])
