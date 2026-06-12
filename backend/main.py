"""Main entry point for the FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
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
from backend.core.exceptions import (
    AppException,
    DeviceUnreachableException,
    EntityExistsException,
    EntityNotFoundException,
    ForbiddenException,
    InvalidCredentialsException,
    InvalidDeviceURLException,
    InvalidPlatformCredentialsException,
    InviteExpiredException,
    PasswordRequiredException,
    ProfileIncompleteException,
    SpotifyUpstreamException,
    TooManyRequestsException,
    UserAlreadyInRoomException,
    UserBannedException,
)
from backend.core.network import is_ip_allowed
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


# Documentation endpoints are served by gated routes below, so the
# auto-generated ones are disabled here. Setting these to None also prevents the
# SPA catch-all from masking them.
app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# --- API docs access control ----------------------------------------------
# /docs, /redoc and /openapi.json are restricted to DOCS_ALLOWED_HOSTS. The
# real openapi spec is exposed at an internal path that the gated routes proxy
# to, so it is never reachable directly.
_INTERNAL_OPENAPI_PATH = "/openapi.json"


def _docs_client_ip(request: Request) -> str | None:
    """Resolve the client IP used for docs access control.

    Honors X-Forwarded-For only when DOCS_TRUST_PROXY is set, which must only
    be enabled behind a trusted reverse proxy (the header is client-spoofable).
    """
    if settings.DOCS_TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First entry is the original client when set by a trusted proxy.
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _require_docs_access(request: Request) -> None:
    """Raise 404 unless the request originates from an allowed host.

    404 (not 403) is used deliberately so the endpoints' existence is not
    disclosed to disallowed clients.
    """
    client_ip = _docs_client_ip(request)
    if not is_ip_allowed(client_ip, settings.docs_allowed_networks):
        raise HTTPException(status_code=404)


@app.get(_INTERNAL_OPENAPI_PATH, include_in_schema=False)
async def gated_openapi(request: Request) -> JSONResponse:
    """Serve the OpenAPI schema only to allowed hosts."""
    _require_docs_access(request)
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False)
async def gated_swagger_ui(request: Request):
    """Serve Swagger UI only to allowed hosts."""
    _require_docs_access(request)
    return get_swagger_ui_html(
        openapi_url=_INTERNAL_OPENAPI_PATH,
        title=f"{settings.PROJECT_NAME} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
async def gated_redoc(request: Request):
    """Serve ReDoc only to allowed hosts."""
    _require_docs_access(request)
    return get_redoc_html(
        openapi_url=_INTERNAL_OPENAPI_PATH,
        title=f"{settings.PROJECT_NAME} - ReDoc",
    )


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


@app.exception_handler(TooManyRequestsException)
async def too_many_requests_handler(
    request: Request, exc: TooManyRequestsException
) -> JSONResponse:
    """Return 429 when a user exceeds a rate limit."""
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc), "retry_after": exc.retry_after},
        headers={"Retry-After": str(int(exc.retry_after))},
    )


# Maps AppException subclasses to their HTTP status codes. These act as a global
# safety net: per-endpoint try/except blocks still take precedence (they convert
# to HTTPException before anything bubbles up), but any uncaught AppException is
# turned into the correct status code here instead of a generic 500.
_APP_EXCEPTION_STATUS: dict[type[AppException], int] = {
    EntityNotFoundException: 404,
    EntityExistsException: 409,
    UserAlreadyInRoomException: 409,
    UserBannedException: 403,
    InvalidCredentialsException: 401,
    PasswordRequiredException: 401,
    ForbiddenException: 403,
    InviteExpiredException: 410,
    InvalidPlatformCredentialsException: 400,
    InvalidDeviceURLException: 400,
    SpotifyUpstreamException: 502,
    DeviceUnreachableException: 502,
}


def _make_app_exception_handler(status_code: int):
    """Build a handler that renders an AppException as a JSON error response.

    Args:
        status_code: The HTTP status code to return.

    Returns:
        An async FastAPI exception handler.
    """

    async def handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


for _exc_type, _status_code in _APP_EXCEPTION_STATUS.items():
    app.add_exception_handler(_exc_type, _make_app_exception_handler(_status_code))


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

avatars_dir = Path(__file__).resolve().parent / "static" / "avatars"
avatars_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=avatars_dir), name="avatars")

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
