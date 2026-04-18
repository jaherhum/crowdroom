from pathlib import Path
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Manages global application configuration via environment variables.

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
    DATABASE_URL: str = "sqlite:///./crowdroom.db"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
