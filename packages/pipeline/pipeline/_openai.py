"""Shared OpenAI client with sane defaults."""
from __future__ import annotations

from openai import AsyncOpenAI

from .config import Settings


def get_openai_client(settings: Settings | None = None) -> AsyncOpenAI:
    """Return an async OpenAI client.

    AsyncOpenAI is safe to share across coroutines and reuses an internal
    httpx connection pool, so we create one per pipeline run.
    """
    settings = settings or Settings()
    return AsyncOpenAI(api_key=settings.openai_api_key, timeout=30.0)