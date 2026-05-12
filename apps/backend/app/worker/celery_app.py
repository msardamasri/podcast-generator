"""Celery application factory.

Configured to use Redis as both broker (job queue) and result backend
(where task results are stored).

The worker process imports this file with:
    celery -A app.worker.celery_app worker --loglevel=info
"""
from __future__ import annotations

from celery import Celery

from ..config import settings


celery_app = Celery(
    "podcast_generator",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],  # modules to autodiscover tasks from
)


celery_app.conf.update(
    # Don't pickle — JSON is safer and human-readable
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone — Celery beats and ETAs use this
    timezone="UTC",
    enable_utc=True,

    # Track when a task starts running (in addition to PENDING / SUCCESS / FAILURE)
    task_track_started=True,

    # Don't let a task hang forever — kill after 10 min hard, soft warn at 8 min
    task_time_limit=10 * 60,
    task_soft_time_limit=8 * 60,

    # Each worker process handles one task at a time before recycling.
    # Useful when tasks have memory leaks (e.g., libraries that don't release GPU mem).
    # For our pipeline it's overkill but it's a safe default.
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)