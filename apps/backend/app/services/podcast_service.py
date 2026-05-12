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


async def enqueue_podcast(
    request: GenerateRequest,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Create a 'pending' podcast row and enqueue the generation task.

    Returns immediately with the podcast_id — the actual work happens
    in the Celery worker. Client polls /podcasts/{id} to track progress.
    """
    from ..worker.tasks import generate_podcast_task  # local import to avoid circular

    podcast_id = uuid.uuid4()

    podcast = Podcast(
        id=podcast_id,
        user_id=user_id,
        status="pending",
    )
    db.add(podcast)
    await db.flush()

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

    # Enqueue. apply_async returns immediately — the worker picks it up.
    task = generate_podcast_task.apply_async(
        kwargs={
            "podcast_id": str(podcast_id),
            "user_id": str(user_id),
            "interests": [i.model_dump() for i in request.interests],
            "exclusions": request.exclusions,
            "length_min": request.length_min,
            "tone": request.tone,
            "voice_id": request.voice_id,
            "max_articles": request.max_articles,
            "since_hours": request.since_hours,
        }
    )

    logger.info("Enqueued podcast %s as task %s", podcast_id, task.id)

    return {
        "podcast_id": str(podcast_id),
        "task_id": task.id,
        "status": "pending",
    }


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