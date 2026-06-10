"""Application configuration management."""

import logging
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (the folder where config.py resides is backend/core/)
# So parent.parent is the 'backend' directory itself.
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Default database URLs derived from the deployment mode (AUTH_MODE):
#   - LOCAL  -> SQLite (file inside the backend directory)
#   - ONLINE -> PostgreSQL
# These are only used when DATABASE_URL is not explicitly provided.
DEFAULT_LOCAL_DATABASE_URL = f"sqlite:///{BACKEND_DIR}/crowdroom.db"
DEFAULT_ONLINE_DATABASE_URL = (
    "postgresql://crowdroom:crowdroom@localhost:5432/crowdroom"
)

logger = logging.getLogger(__name__)


def validate_spotify_config() -> None:
    """Log warning if Spotify OAuth config is incomplete."""
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        logger.warning(
            "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not set. "
            "Per-user Spotify app credentials will be required."
        )
        return

    if not settings.SPOTIFY_REDIRECT_URI:
        logger.warning(
            "SPOTIFY_REDIRECT_URI not set. "
            "Search will work but Spotify OAuth playback flow will fail."
        )


class Settings(BaseSettings):
    """Manages global application configuration via environment variables.

    Uses pydantic-settings to automatically load and validate settings
    from a .env file.
    """

    # General Config
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CrowdRoom"
    DEBUG: bool = False
    TESTING: bool = False

    # Auth Mode
    AUTH_MODE: Literal["LOCAL", "ONLINE"] = "LOCAL"

    # Database
    # If left empty, the URL is derived from AUTH_MODE:
    #   LOCAL  -> SQLite, ONLINE -> PostgreSQL (see _resolve_database_url below).
    # Set DATABASE_URL explicitly to override the mode-based default.
    DATABASE_URL: str = ""

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Auth Cookie (httpOnly access token)
    # COOKIE_SECURE must be True in production (HTTPS). Keep False for local http.
    AUTH_COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # Metadata Cache
    METADATA_CACHE_TTL_SECONDS: int = 86400
    METADATA_CACHE_MAX_SIZE: int = 2048

    # Vote Skip
    VOTE_SKIP_COOLDOWN_SECONDS: int = 2

    # WebSocket Heartbeat
    WS_HEARTBEAT_INTERVAL_SECONDS: int = 30
    WS_HEARTBEAT_TIMEOUT_SECONDS: int = 10

    # Spotify OAuth (playback control)
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/spotify/callback"
    PLAYBACK_POLL_INTERVAL_SECONDS: int = 3
    SPOTIFY_OAUTH_STATE_TTL_SECONDS: int = 600
    FRONTEND_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        """Select the database backend based on the deployment mode.

        When DATABASE_URL is not provided, derive it from AUTH_MODE:
        - LOCAL  -> SQLite (single-file DB, no external service required)
        - ONLINE -> PostgreSQL

        An explicitly provided DATABASE_URL always takes precedence so that
        deployments can point at any database they want.
        """
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                DEFAULT_ONLINE_DATABASE_URL
                if self.AUTH_MODE == "ONLINE"
                else DEFAULT_LOCAL_DATABASE_URL
            )
        return self


settings = Settings()
