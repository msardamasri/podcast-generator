"""Backend configuration loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Backend-specific settings.

    DATABASE_URL points to wherever Postgres is reachable from this process:
    - When running uvicorn/alembic from Windows host: localhost:5432
    - When running inside Docker Compose: postgres:5432 (container name)
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://podcast:podcast_dev_password@localhost:5432/podcast"
    redis_url: str = "redis://localhost:6379/0"

    app_env: str = "development"
    log_level: str = "INFO"
    audio_storage_path: str = "./data/audio"

    default_user_email: str = "demo@example.com"


settings = BackendSettings()