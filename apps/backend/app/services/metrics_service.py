"""Admin dashboard metrics.

All queries operate on the events + podcasts + segments tables.
No mocked data — every number is derived from real activity.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Event, Podcast, Segment
from ..schemas import (
    AdminMetrics,
    EventLog,
    KPIMetrics,
    OutletShare,
    TimeSeriesPoint,
)


async def get_admin_metrics(db: AsyncSession) -> AdminMetrics:
    kpis = await _compute_kpis(db)
    timeseries = await _compute_timeseries(db, days=14)
    outlets = await _compute_outlets(db, limit=10)
    recent = await _recent_events(db, limit=15)
    return AdminMetrics(
        kpis=kpis,
        timeseries=timeseries,
        outlets=outlets,
        recent_events=recent,
    )


async def _compute_kpis(db: AsyncSession) -> KPIMetrics:
    """Aggregate KPIs from the podcasts table."""
    total_q = await db.execute(select(func.count(Podcast.id)))
    total = total_q.scalar_one()

    completed_q = await db.execute(
        select(func.count(Podcast.id)).where(Podcast.status == "ready")
    )
    completed = completed_q.scalar_one()

    failed_q = await db.execute(
        select(func.count(Podcast.id)).where(Podcast.status == "failed")
    )
    failed = failed_q.scalar_one()

    avg_duration_q = await db.execute(
        select(func.avg(Podcast.duration_sec)).where(Podcast.status == "ready")
    )
    avg_duration = avg_duration_q.scalar_one() or 0

    avg_cost_q = await db.execute(
        select(func.avg(Podcast.cost_cents)).where(Podcast.status == "ready")
    )
    avg_cost = avg_cost_q.scalar_one() or 0

    return KPIMetrics(
        total_podcasts=total,
        success_rate=(completed / total) if total > 0 else 0.0,
        avg_duration_sec=float(avg_duration),
        avg_cost_cents=float(avg_cost),
        total_failures=failed,
    )


async def _compute_timeseries(db: AsyncSession, days: int) -> list[TimeSeriesPoint]:
    """Daily counts of completed and failed podcasts over the last `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            func.date(Podcast.created_at).label("day"),
            func.sum(case((Podcast.status == "ready", 1), else_=0)).label("completed"),
            func.sum(case((Podcast.status == "failed", 1), else_=0)).label("failed"),
        )
        .where(Podcast.created_at >= since)
        .group_by(func.date(Podcast.created_at))
        .order_by(func.date(Podcast.created_at))
    )
    rows = (await db.execute(stmt)).all()

    # Fill missing days with zeros so the chart has continuous x-axis
    by_date: dict[date, tuple[int, int]] = {
        r.day: (int(r.completed or 0), int(r.failed or 0)) for r in rows
    }

    points: list[TimeSeriesPoint] = []
    today = datetime.now(timezone.utc).date()
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        completed, failed = by_date.get(d, (0, 0))
        points.append(
            TimeSeriesPoint(
                date=d.isoformat(),
                completed=completed,
                failed=failed,
            )
        )
    return points


async def _compute_outlets(db: AsyncSession, limit: int) -> list[OutletShare]:
    """Top outlets by number of segments produced from them."""
    stmt = (
        select(Segment.source_outlet, func.count(Segment.id).label("count"))
        .where(Segment.source_outlet.is_not(None))
        .group_by(Segment.source_outlet)
        .order_by(func.count(Segment.id).desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [OutletShare(outlet=r.source_outlet, count=int(r.count)) for r in rows]


async def _recent_events(db: AsyncSession, limit: int) -> list[EventLog]:
    stmt = select(Event).order_by(Event.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        EventLog(
            id=e.id,
            type=e.type,
            properties=e.properties or {},
            created_at=e.created_at,
        )
        for e in rows
    ]