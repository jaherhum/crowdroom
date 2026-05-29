"""Application configuration management."""

import logging
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (the folder where config.py resides is backend/core/)
# So parent.parent is the 'backend' directory itself.
BACKEND_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

def validate_spotify_config() -> None:
    """Log warning if Spotify OAuth config is incomplete."""
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        logger.warning(
            "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not set. "
            "All Spotify features (search, queue, playback) will be unavailable."
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
    # Default to an absolute path inside the backend directory
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR}/crowdroom.db"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Metadata Cache
    METADATA_CACHE_TTL_SECONDS: int = 86400
    METADATA_CACHE_MAX_SIZE: int = 2048

    # WebSocket Heartbeat
    WS_HEARTBEAT_INTERVAL_SECONDS: int = 30
    WS_HEARTBEAT_TIMEOUT_SECONDS: int = 10

    # Spotify OAuth (playback control)
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/spotify/callback"
    PLAYBACK_POLL_INTERVAL_SECONDS: int = 3

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
