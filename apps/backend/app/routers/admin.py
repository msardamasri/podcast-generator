"""Admin metrics endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..deps import DBSession
from ..schemas import AdminMetrics
from ..services.metrics_service import get_admin_metrics

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetrics)
async def metrics(db: DBSession) -> AdminMetrics:
    """Aggregate dashboard metrics from real events/podcasts/segments."""
    return await get_admin_metrics(db)