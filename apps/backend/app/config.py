"""Backend configuration loaded from environment."""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Esto localiza el .env que está en apps/backend/.env
# (Subiendo dos niveles desde app/config.py)
current_dir = Path(__file__).parent.parent
env_path = current_dir / ".env"

class BackendSettings(BaseSettings):
    # Forzamos la ruta exacta del .env del backend
    model_config = SettingsConfigDict(
        env_file=env_path, 
        extra="ignore",
        env_file_encoding='utf-8'
    )

    openai_api_key: str
    elevenlabs_api_key: str
    newsapi_key: str | None = None
    firecrawl_api_key: str | None = None

    database_url: str = "postgresql+psycopg://podcast:podcast_dev_password@localhost:5432/podcast"
    redis_url: str = "redis://localhost:6379/0"

    app_env: str = "development"
    log_level: str = "INFO"
    audio_storage_path: str = "./data/audio"
    default_user_email: str = "demo@example.com"

settings = BackendSettings()