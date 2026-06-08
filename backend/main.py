"""Main entry point for the FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.auth.router import router as auth_router
from backend.api.invites.router import router as invites_router
from backend.api.platform_connections.router import (
    router as platform_connections_router,
)
from backend.api.playback.router import router as playback_router
from backend.api.queue.router import router as queue_router
from backend.api.rooms.router import router as rooms_router
from backend.api.search.router import router as search_router
from backend.api.session.router import router as session_router
from backend.api.songs.router import router as songs_router
from backend.api.users.router import router as user_router
from backend.api.websocket import router as websocket_router
from backend.core.config import settings, validate_spotify_config
from backend.core.exceptions import ProfileIncompleteException
from backend.db.database import create_db_and_tables
from backend.services.playback_poller_service import PlaybackPollerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application lifecycle."""
    validate_spotify_config()
    print("Creating tables in database...")
    create_db_and_tables()
    app.state.playback_poller = PlaybackPollerService()
    yield
    await app.state.playback_poller.stop_all()
    print("App closed.")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(ProfileIncompleteException)
async def profile_incomplete_handler(
    request: Request, exc: ProfileIncompleteException
) -> JSONResponse:
    """Return 403 with PROFILE_INCOMPLETE code when user profile is missing fields."""
    return JSONResponse(
        status_code=403,
        content={
            "detail": str(exc),
            "code": "PROFILE_INCOMPLETE",
            "missing_fields": exc.missing_fields,
        },
    )


app.include_router(
    platform_connections_router,
    prefix=settings.API_V1_STR,
    tags=["platform_connections"],
)
app.include_router(invites_router, prefix=settings.API_V1_STR, tags=["invites"])
app.include_router(playback_router, prefix=settings.API_V1_STR, tags=["playback"])
app.include_router(rooms_router, prefix=settings.API_V1_STR, tags=["rooms"])
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(queue_router, prefix=settings.API_V1_STR, tags=["queue"])
app.include_router(search_router, prefix=settings.API_V1_STR, tags=["search"])
app.include_router(session_router, prefix=settings.API_V1_STR, tags=["session"])
app.include_router(songs_router, prefix=settings.API_V1_STR, tags=["songs"])
app.include_router(user_router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(request: Request, path: str):
        """Serve Vue SPA — all routes fall back to index.html."""
        file_path = frontend_dist / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
