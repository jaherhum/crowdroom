from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

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

    # Database
    DATABASE_URL: str = "sqlite:///./crowdroom.db"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = ConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding = "utf-8",
        case_sensitive = True
    )


settings = Settings()