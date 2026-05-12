"""Podcast generation orchestration.

Bridges HTTP routing and the pipeline package. Persists results to the DB
so we can list and analyze podcasts later.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.cli import run_pipeline
from pipeline.config import Interest, PipelineConfig
from pipeline.types import PipelineResult

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models import Event, Podcast, Segment
from ..schemas import GenerateRequest, GenerateResponse, SegmentResponse, PodcastDetail, PodcastListResponse, PodcastSummary

logger = logging.getLogger(__name__)


async def generate_podcast(
    request: GenerateRequest,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> GenerateResponse:
    """Run the pipeline, persist results, return metadata."""
    podcast_id = uuid.uuid4()
    storage_dir = Path(settings.audio_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    output_path = storage_dir / f"{podcast_id}.mp3"

    # Insert a 'pending' podcast row immediately so we can track failures.
    # Once we have Celery, this row's status will be updated by the worker.
    podcast = Podcast(
    id=podcast_id,
    user_id=user_id,
    status="generating",
    )
    db.add(podcast)
    await db.flush()  # ensure podcast row exists before referencing it from events

    db.add(Event(
        user_id=user_id,
        podcast_id=podcast_id,
        type="podcast_requested",
        properties={
            "length_min": request.length_min,
            "tone": request.tone,
            "n_interests": len(request.interests),
        },
    ))
    await db.commit()

    try:
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

        # Update the podcast row with the actual results
        podcast.status = "ready"
        podcast.audio_path = f"{podcast_id}.mp3"
        podcast.duration_sec = result.duration_sec
        podcast.transcript = result.transcript
        podcast.cost_cents = result.cost_cents
        podcast.token_usage = result.token_usage
        podcast.ready_at = datetime.now(timezone.utc)
        podcast.title = result.segments[0].title if result.segments else None

        # Persist segments for drop-off analytics
        for seg in result.segments:
            db.add(Segment(
                podcast_id=podcast_id,
                idx=seg.idx,
                title=seg.title,
                source_url=seg.source_url,
                source_outlet=seg.source_outlet,
                text=seg.text,
                start_sec=seg.start_sec,
                end_sec=seg.end_sec,
            ))

        db.add(Event(
            user_id=user_id,
            podcast_id=podcast_id,
            type="podcast_completed",
            properties={
                "duration_sec": result.duration_sec,
                "n_segments": len(result.segments),
                "cost_cents": result.cost_cents,
            },
        ))
        await db.commit()

        logger.info("Podcast %s ready — %ds, %d segments",
                    podcast_id, result.duration_sec, len(result.segments))

        return GenerateResponse(
            audio_path=podcast.audio_path,
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

    except Exception as exc:
        # Mark the podcast as failed and re-raise — FastAPI converts to 500
        podcast.status = "failed"
        podcast.error = str(exc)[:1000]
        db.add(Event(
            user_id=user_id,
            podcast_id=podcast_id,
            type="podcast_failed",
            properties={"error": str(exc)[:500]},
        ))
        await db.commit()
        logger.exception("Podcast %s failed", podcast_id)
        raise


async def list_podcasts(
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> PodcastListResponse:
    """Return paginated podcasts for the user, newest first."""
    # Count total for pagination
    total_result = await db.execute(
        select(func.count(Podcast.id)).where(Podcast.user_id == user_id)
    )
    total = total_result.scalar_one()

    # Fetch the page
    result = await db.execute(
        select(Podcast)
        .where(Podcast.user_id == user_id)
        .order_by(Podcast.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    items = [
        PodcastSummary(
            id=p.id,
            title=p.title,
            status=p.status,
            duration_sec=p.duration_sec,
            created_at=p.created_at,
            ready_at=p.ready_at,
        )
        for p in rows
    ]
    return PodcastListResponse(items=items, total=total)


async def get_podcast(
    podcast_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> PodcastDetail | None:
    """Return a podcast with its segments, or None if not found / not owned by user."""
    result = await db.execute(
        select(Podcast)
        .where(Podcast.id == podcast_id, Podcast.user_id == user_id)
        .options(selectinload(Podcast.segments))
    )
    podcast = result.scalar_one_or_none()
    if podcast is None:
        return None

    return PodcastDetail(
        id=podcast.id,
        title=podcast.title,
        status=podcast.status,
        duration_sec=podcast.duration_sec,
        audio_path=podcast.audio_path,
        transcript=podcast.transcript,
        error=podcast.error,
        cost_cents=podcast.cost_cents,
        created_at=podcast.created_at,
        ready_at=podcast.ready_at,
        segments=[
            SegmentResponse(
                idx=seg.idx,
                title=seg.title,
                source_url=seg.source_url,
                source_outlet=seg.source_outlet,
                start_sec=seg.start_sec,
                end_sec=seg.end_sec,
            )
            for seg in podcast.segments
        ],
    )