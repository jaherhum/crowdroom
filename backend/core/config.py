from pathlib import Path


from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CrowdRoom"
    SECRET_KEY: str
    DEBUG: bool = False
    TESTING: bool = False
    DATABASE_URL: str = "sqlite:///./crowdroom.db"

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()