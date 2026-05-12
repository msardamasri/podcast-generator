"""Pipeline configuration and runtime settings."""
from __future__ import annotations

from typing import Callable, Literal, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven secrets and infra config.

    Loaded once at process start from .env or the OS environment.
    Pydantic validates types and raises clearly if a required key is missing.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    elevenlabs_api_key: str
    newsapi_key: str | None = None
    firecrawl_api_key: str | None = None


class Interest(BaseModel):
    """One topic the user cares about."""
    label: str
    weight: float = 1.0
    embedding: list[float] | None = None


class PipelineConfig(BaseModel):
    """Inputs for a single podcast generation run.

    Constructed by the Celery task from DB preferences, or by the CLI
    from command-line args. The pipeline knows nothing about where this
    came from — it just consumes a config.
    """
    interests: list[Interest]
    exclusions: list[str] = Field(default_factory=list)
    length_min: Literal[5, 10, 20] = 10
    tone: Literal["conversational", "formal", "energetic"] = "conversational"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel — ElevenLabs default
    max_articles: int = 8
    since_hours: int = 24
    output_path: str = "./output.mp3"

    # Progress reporting hook — Celery uses this to update job status in DB.
    # CLI ignores it. Not part of the schema (excluded from serialization).
    progress_callback: Optional[Callable[[str, float], None]] = Field(
        default=None, exclude=True
    )

    model_config = {"arbitrary_types_allowed": True}