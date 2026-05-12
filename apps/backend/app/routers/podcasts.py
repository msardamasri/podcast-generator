"""Podcast endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import uuid
from fastapi import HTTPException, Query

from ..config import settings
from ..deps import CurrentUserId, DBSession
from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    PodcastDetail,
    PodcastListResponse,
)
from ..services.podcast_service import generate_podcast, get_podcast, list_podcasts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/podcasts", tags=["podcasts"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    user_id: CurrentUserId,
    db: DBSession,
) -> GenerateResponse:
    """Generate a podcast synchronously.

    WARNING: This takes 30-60s. We'll move it to Celery next.
    """
    logger.info("Generating podcast for user=%s, length=%d",
                user_id, request.length_min)
    return await generate_podcast(request, user_id=user_id, db=db)


@router.get("", response_model=PodcastListResponse)
async def list_user_podcasts(
    user_id: CurrentUserId,
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PodcastListResponse:
    """List the current user's podcasts, newest first."""
    return await list_podcasts(user_id, db, limit=limit, offset=offset)


@router.get("/{podcast_id}", response_model=PodcastDetail)
async def get_user_podcast(
    podcast_id: uuid.UUID,
    user_id: CurrentUserId,
    db: DBSession,
) -> PodcastDetail:
    """Return a single podcast with its segments and transcript."""
    podcast = await get_podcast(podcast_id, user_id, db)
    if podcast is None:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast


@router.get("/audio/{filename}")
async def get_audio(filename: str) -> FileResponse:
    """Stream a generated audio file."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    audio_path = Path(settings.audio_storage_path) / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )