"""Backend configuration loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://podcast:podcast_dev_password@localhost:5432/podcast"
    redis_url: str = "redis://localhost:6379/0"

    # These are consumed by the pipeline package, not by the backend itself,
    # but we accept them here so they're available in container env.
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    newsapi_key: str | None = None
    firecrawl_api_key: str | None = None

    app_env: str = "development"
    log_level: str = "INFO"
    audio_storage_path: str = "./data/audio"

    default_user_email: str = "demo@example.com"


settings = BackendSettings()