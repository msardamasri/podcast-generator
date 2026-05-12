"""SQLAlchemy ORM models.

Each class maps to a table. Relationships use SQLAlchemy 2.0 typed syntax
with Mapped[...] annotations — gives mypy and IDEs proper type info.

All timestamps use DateTime(timezone=True) so they're stored as
TIMESTAMP WITH TIME ZONE in Postgres — clients receive UTC ISO strings
with explicit offset, which JS Date() parses correctly into local time.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    """Standard UUID primary key with server-side default."""
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    preferences: Mapped["Preferences | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    podcasts: Mapped[list["Podcast"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Preferences(Base):
    __tablename__ = "preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interests: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    exclusions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    length_min: Mapped[int] = mapped_column(default=4, nullable=False)
    tone: Mapped[str] = mapped_column(
        String(32), default="conversational", nullable=False
    )
    voice_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schedule: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {"type": "on_demand"}, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="preferences")


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )
    stage_progress: Mapped[float] = mapped_column(default=0.0, nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_cents: Mapped[int] = mapped_column(default=0, nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="podcasts")
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="podcast",
        cascade="all, delete-orphan",
        order_by="Segment.idx",
    )

    __table_args__ = (
        Index("ix_podcasts_user_created", "user_id", "created_at"),
    )


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    podcast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("podcasts.id", ondelete="CASCADE"),
        nullable=False,
    )
    idx: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_outlet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_sec: Mapped[float | None] = mapped_column(nullable=True)
    end_sec: Mapped[float | None] = mapped_column(nullable=True)

    podcast: Mapped["Podcast"] = relationship(back_populates="segments")


class Event(Base):
    """Append-only event log. The dashboard queries off this."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    podcast_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("podcasts.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_events_type_created", "type", "created_at"),
        Index("ix_events_user_created", "user_id", "created_at"),
    )