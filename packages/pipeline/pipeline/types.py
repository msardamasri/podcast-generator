"""Shared types passed between pipeline stages."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class Article(BaseModel):
    """A raw news article fetched from a source."""
    url: str
    title: str
    outlet: str
    content: str  # full text if available, else summary/description
    published_at: datetime | None = None
    embedding: list[float] | None = None
    score: float | None = None  # filled in during ranking


class ScriptSegment(BaseModel):
    """One spoken segment of the final podcast."""
    idx: int
    title: str
    source_url: str
    source_outlet: str
    text: str
    start_sec: float | None = None
    end_sec: float | None = None


class Script(BaseModel):
    """Full podcast script — what the host will say."""
    intro: str
    segments: list[ScriptSegment]
    outro: str


class AudioSegment(BaseModel):
    """A segment with its rendered audio."""
    script: ScriptSegment
    audio_bytes: bytes
    duration_sec: float
    start_sec: float = 0.0  # filled in during stitching

    model_config = {"arbitrary_types_allowed": True}


class PipelineResult(BaseModel):
    """Output of a complete pipeline run."""
    audio_path: str
    duration_sec: int
    transcript: str
    segments: list[ScriptSegment]
    token_usage: dict[str, int]  # {"openai_input": ..., "elevenlabs_chars": ...}
    cost_cents: int

    model_config = {"arbitrary_types_allowed": True}