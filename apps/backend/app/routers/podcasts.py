"""Podcast endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..schemas import GenerateRequest, GenerateResponse
from ..services.podcast_service import generate_podcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/podcasts", tags=["podcasts"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate a podcast synchronously.

    WARNING: This takes 30-60s. In production we use Celery to make
    this fire-and-forget. For now, kept sync to validate the full pipeline
    integration end-to-end before adding async machinery.
    """
    logger.info("Generating podcast with %d interests, length=%d",
                len(request.interests), request.length_min)
    return await generate_podcast(request)


@router.get("/audio/{filename}")
async def get_audio(filename: str) -> FileResponse:
    """Stream a generated audio file.

    Supports HTTP Range requests via FileResponse — so the audio player
    can seek without downloading the whole file.
    """
    # Basic path traversal protection
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