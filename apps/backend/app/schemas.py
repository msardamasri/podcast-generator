"""Pydantic schemas for HTTP request/response bodies.

Kept separate from SQLAlchemy models — schemas describe the API shape,
models describe the storage shape. Mixing them couples your public API
to your database design.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

import uuid
from datetime import datetime


class InterestInput(BaseModel):
    """One interest from the user."""
    label: str = Field(..., min_length=2, max_length=200)
    weight: float = Field(default=1.0, ge=0.0, le=5.0)


class GenerateRequest(BaseModel):
    """Body for POST /api/v1/podcasts/generate."""
    interests: list[InterestInput] = Field(..., min_length=1, max_length=20)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    length_min: Literal[2, 4, 7] = 4
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

# ---------- Preferences ----------

class ScheduleConfig(BaseModel):
    """When the podcast should be generated automatically."""
    type: Literal["on_demand", "daily", "weekly"] = "on_demand"
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    weekday: int | None = Field(default=None, ge=0, le=6)  # 0=Monday
    tz: str = "Europe/Madrid"


class PreferencesResponse(BaseModel):
    """Body returned by GET /api/v1/preferences."""
    interests: list[InterestInput]
    exclusions: list[str]
    length_min: Literal[2, 4, 7] = 4
    tone: Literal["conversational", "formal", "energetic"]
    voice_id: str
    schedule: ScheduleConfig


class PreferencesUpdate(BaseModel):
    """Body for PUT /api/v1/preferences. Same shape as response, but
    allows the user to send only what they want to change in the future.
    For now we treat it as full replacement to keep things simple."""
    interests: list[InterestInput] = Field(..., min_length=1, max_length=30)
    exclusions: list[str] = Field(default_factory=list, max_length=30)
    length_min: Literal[2, 4, 7] = 4
    tone: Literal["conversational", "formal", "energetic"] = "conversational"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


# ---------- Podcasts (list + detail) ----------

class PodcastSummary(BaseModel):
    """Body item for GET /api/v1/podcasts."""
    id: uuid.UUID
    title: str | None
    status: str
    duration_sec: int | None
    created_at: datetime
    ready_at: datetime | None


class PodcastListResponse(BaseModel):
    """Body for GET /api/v1/podcasts."""
    items: list[PodcastSummary]
    total: int


class PodcastDetail(BaseModel):
    """Body for GET /api/v1/podcasts/{id}."""
    id: uuid.UUID
    title: str | None
    status: str
    duration_sec: int | None
    audio_path: str | None
    transcript: str | None
    error: str | None
    cost_cents: int
    created_at: datetime
    ready_at: datetime | None
    segments: list[SegmentResponse]

class EnqueueResponse(BaseModel):
    """Body for POST /api/v1/podcasts/generate (now async)."""
    podcast_id: uuid.UUID
    task_id: str
    status: str

# ---------- Admin metrics ----------

class KPIMetrics(BaseModel):
    total_podcasts: int
    success_rate: float  # 0-1
    avg_duration_sec: float
    avg_cost_cents: float
    total_failures: int


class TimeSeriesPoint(BaseModel):
    date: str  # YYYY-MM-DD
    completed: int
    failed: int


class OutletShare(BaseModel):
    outlet: str
    count: int


class EventLog(BaseModel):
    id: int
    type: str
    properties: dict
    created_at: datetime


class AdminMetrics(BaseModel):
    kpis: KPIMetrics
    timeseries: list[TimeSeriesPoint]
    outlets: list[OutletShare]
    recent_events: list[EventLog]