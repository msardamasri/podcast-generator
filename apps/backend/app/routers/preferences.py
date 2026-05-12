"""User preferences endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..deps import CurrentUserId, DBSession
from ..schemas import PreferencesResponse, PreferencesUpdate
from ..services.preferences_service import get_preferences, update_preferences

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesResponse)
async def read_preferences(
    user_id: CurrentUserId,
    db: DBSession,
) -> PreferencesResponse:
    """Return the current user's preferences, or sane defaults."""
    return await get_preferences(user_id, db)


@router.put("", response_model=PreferencesResponse)
async def write_preferences(
    update: PreferencesUpdate,
    user_id: CurrentUserId,
    db: DBSession,
) -> PreferencesResponse:
    """Replace the current user's preferences."""
    return await update_preferences(user_id, update, db)