"""Celery tasks.

Each function decorated with @celery_app.task becomes a unit of work
the worker can execute. The task receives serializable args (no DB sessions,
no FastAPI objects — just plain types) and creates its own DB session.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery import Task

from pipeline.cli import run_pipeline
from pipeline.config import Interest, PipelineConfig

from ..config import settings
from ..db import SessionLocal
from ..models import Event, Podcast, Segment
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="generate_podcast_task",
    bind=True,
    autoretry_for=(),  # don't auto-retry — we want explicit failure tracking
    max_retries=0,
)
def generate_podcast_task(
    self: Task,
    podcast_id: str,
    user_id: str,
    interests: list[dict],
    exclusions: list[str],
    length_min: int,
    tone: str,
    voice_id: str,
    max_articles: int,
    since_hours: int,
) -> dict:
    """Run the podcast pipeline in the background.

    Updates the Podcast row in DB as it progresses through stages.
    Returns a small dict mostly for logging — the frontend queries
    the DB directly (via /podcasts/{id}/status), not the Celery result.
    """
    podcast_uuid = uuid.UUID(podcast_id)
    user_uuid = uuid.UUID(user_id)

    storage_dir = Path(settings.audio_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    output_path = storage_dir / f"{podcast_id}.mp3"

    # Sync DB session — Celery tasks run in sync workers.
    db = SessionLocal()
    try:
        podcast = db.get(Podcast, podcast_uuid)
        if podcast is None:
            logger.error("Podcast %s not found, aborting", podcast_id)
            return {"status": "aborted", "reason": "podcast_not_found"}

        # Progress callback: writes the current stage into the DB
        # so the frontend can show "Generating script..." etc.
        def report_progress(stage: str, progress: float) -> None:
            podcast.status = stage
            podcast.stage_progress = progress
            db.commit()

        config = PipelineConfig(
            interests=[Interest(**i) for i in interests],
            exclusions=exclusions,
            length_min=length_min,
            tone=tone,
            voice_id=voice_id,
            max_articles=max_articles,
            since_hours=since_hours,
            output_path=str(output_path.absolute()),
            progress_callback=report_progress,
        )

        # The pipeline is async; we run it inside this sync task with asyncio.run
        result = asyncio.run(run_pipeline(config))

        # Mark as ready
        podcast.status = "ready"
        podcast.stage_progress = 1.0
        podcast.audio_path = f"{podcast_id}.mp3"
        podcast.duration_sec = result.duration_sec
        podcast.transcript = result.transcript
        podcast.cost_cents = result.cost_cents
        podcast.token_usage = result.token_usage
        podcast.ready_at = datetime.now(timezone.utc)
        podcast.title = result.segments[0].title if result.segments else None

        for seg in result.segments:
            db.add(Segment(
                podcast_id=podcast_uuid,
                idx=seg.idx,
                title=seg.title,
                source_url=seg.source_url,
                source_outlet=seg.source_outlet,
                text=seg.text,
                start_sec=seg.start_sec,
                end_sec=seg.end_sec,
            ))

        db.add(Event(
            user_id=user_uuid,
            podcast_id=podcast_uuid,
            type="podcast_completed",
            properties={
                "duration_sec": result.duration_sec,
                "n_segments": len(result.segments),
                "cost_cents": result.cost_cents,
            },
        ))
        db.commit()

        logger.info("Podcast %s ready — %ds", podcast_id, result.duration_sec)
        return {"status": "ready", "podcast_id": podcast_id}

    except Exception as exc:
        logger.exception("Podcast %s failed", podcast_id)
        # Refresh in case the previous commit made `podcast` stale
        podcast = db.get(Podcast, podcast_uuid)
        if podcast:
            podcast.status = "failed"
            podcast.error = str(exc)[:1000]
            db.add(Event(
                user_id=user_uuid,
                podcast_id=podcast_uuid,
                type="podcast_failed",
                properties={"error": str(exc)[:500]},
            ))
            db.commit()
        raise  # re-raise so Celery marks the task as FAILED
    finally:
        db.close()