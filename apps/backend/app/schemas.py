"""Pydantic schemas for HTTP request/response bodies.

Kept separate from SQLAlchemy models — schemas describe the API shape,
models describe the storage shape. Mixing them couples your public API
to your database design.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InterestInput(BaseModel):
    """One interest from the user."""
    label: str = Field(..., min_length=2, max_length=200)
    weight: float = Field(default=1.0, ge=0.0, le=5.0)


class GenerateRequest(BaseModel):
    """Body for POST /api/v1/podcasts/generate."""
    interests: list[InterestInput] = Field(..., min_length=1, max_length=20)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    length_min: Literal[5, 10, 20] = 10
    tone: Literal["conversational", "formal", "energetic"] = "conversational"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    since_hours: int = Field(default=24, ge=1, le=168)
    max_articles: int = Field(default=6, ge=3, le=12)


class SegmentResponse(BaseModel):
    """Segment metadata in a podcast response."""
    idx: int
    title: str
    source_url: str
    source_outlet: str
    start_sec: float | None = None
    end_sec: float | None = None


class GenerateResponse(BaseModel):
    """Body for POST /api/v1/podcasts/generate response."""
    audio_path: str
    duration_sec: int
    transcript: str
    segments: list[SegmentResponse]
    cost_cents: int