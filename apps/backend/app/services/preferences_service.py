"""Preferences CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Event, Preferences
from ..schemas import InterestInput, PreferencesResponse, PreferencesUpdate, ScheduleConfig


DEFAULT_PREFS = PreferencesUpdate(
    interests=[InterestInput(label="technology", weight=1.0)],
    exclusions=[],
    length_min=4,
    tone="conversational",
    voice_id="21m00Tcm4TlvDq8ikWAM",
)


async def get_preferences(user_id: uuid.UUID, db: AsyncSession) -> PreferencesResponse:
    """Return the user's preferences, or sane defaults if none saved yet."""
    row = await db.get(Preferences, user_id)
    if row is None:
        return PreferencesResponse(**DEFAULT_PREFS.model_dump())

    return PreferencesResponse(
        interests=[InterestInput(**i) for i in row.interests],
        exclusions=row.exclusions,
        length_min=row.length_min,
        tone=row.tone,
        voice_id=row.voice_id,
        schedule=ScheduleConfig(**row.schedule),
    )


async def update_preferences(
    user_id: uuid.UUID,
    update: PreferencesUpdate,
    db: AsyncSession,
) -> PreferencesResponse:
    """Upsert preferences for the user."""
    row = await db.get(Preferences, user_id)

    if row is None:
        row = Preferences(user_id=user_id)
        db.add(row)

    row.interests = [i.model_dump() for i in update.interests]
    row.exclusions = update.exclusions
    row.length_min = update.length_min
    row.tone = update.tone
    row.voice_id = update.voice_id
    row.schedule = update.schedule.model_dump()

    db.add(Event(
        user_id=user_id,
        type="preferences_updated",
        properties={"n_interests": len(update.interests), "tone": update.tone},
    ))

    await db.commit()
    await db.refresh(row)

    return PreferencesResponse(
        interests=[InterestInput(**i) for i in row.interests],
        exclusions=row.exclusions,
        length_min=row.length_min,
        tone=row.tone,
        voice_id=row.voice_id,
        schedule=ScheduleConfig(**row.schedule),
    )