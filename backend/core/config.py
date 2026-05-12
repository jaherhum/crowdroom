"""Application configuration management."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (the folder where config.py resides is backend/core/)
# So parent.parent is the 'backend' directory itself.
BACKEND_DIR = Path(__file__).resolve().parent.parent


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

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MusicBrainz API URL
    MUSICBRAINZ_API_URL: str = "https://musicbrainz.org/ws/2"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
