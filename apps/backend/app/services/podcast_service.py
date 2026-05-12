"""Podcast generation orchestration.

This is the seam between HTTP routing and the pipeline package.
Routers call this; this calls the pipeline.

Keeping it here means we can later add Celery, caching, or persistence
without changing the routers.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from pipeline.cli import run_pipeline
from pipeline.config import Interest, PipelineConfig
from pipeline.types import PipelineResult

from ..config import settings
from ..schemas import GenerateRequest, GenerateResponse, SegmentResponse


async def generate_podcast(request: GenerateRequest) -> GenerateResponse:
    """Run the full pipeline and return metadata about the generated podcast.

    Audio is written to disk under AUDIO_STORAGE_PATH; the response includes
    a path the frontend can use to stream it.
    """
    # Each podcast gets a UUID-named file to avoid collisions
    podcast_id = uuid.uuid4()
    storage_dir = Path(settings.audio_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    output_path = storage_dir / f"{podcast_id}.mp3"

    # Build pipeline config from request
    config = PipelineConfig(
        interests=[Interest(label=i.label, weight=i.weight) for i in request.interests],
        exclusions=request.exclusions,
        length_min=request.length_min,
        tone=request.tone,
        voice_id=request.voice_id,
        max_articles=request.max_articles,
        since_hours=request.since_hours,
        output_path=str(output_path.absolute()),
    )

    result: PipelineResult = await run_pipeline(config)

    return GenerateResponse(
        audio_path=str(podcast_id) + ".mp3",  # relative path served by /audio endpoint
        duration_sec=result.duration_sec,
        transcript=result.transcript,
        segments=[
            SegmentResponse(
                idx=seg.idx,
                title=seg.title,
                source_url=seg.source_url,
                source_outlet=seg.source_outlet,
                start_sec=seg.start_sec,
                end_sec=seg.end_sec,
            )
            for seg in result.segments
        ],
        cost_cents=result.cost_cents,
    )