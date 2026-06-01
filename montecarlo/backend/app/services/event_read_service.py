"""
Read-side service for observability event summaries.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.events import EndpointStat, EventSummaryResponse


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


async def build_event_summary(db: AsyncSession, hours: int) -> EventSummaryResponse:
    """
    Build a windowed summary of API event activity.

    The query is filtered on the requested lookback window so the endpoint
    matches its contract instead of returning all-time aggregates.
    """
    from app.db.models import ApiEvent  # noqa: PLC0415

    cutoff = _utcnow() - timedelta(hours=hours)
    stmt = (
        select(
            ApiEvent.endpoint,
            func.count(ApiEvent.id).label("total"),
            func.sum(func.cast(ApiEvent.demo_data, Integer)).label("demo_cnt"),
            func.sum(func.cast(ApiEvent.cache_hit, Integer)).label("cache_cnt"),
            func.avg(ApiEvent.duration_ms).label("avg_ms"),
        )
        .where(ApiEvent.created_at >= cutoff)
        .group_by(ApiEvent.endpoint)
        .order_by(func.count(ApiEvent.id).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    endpoint_stats: list[EndpointStat] = []
    grand_total = 0
    grand_demo = 0
    grand_cache = 0
    grand_duration_sum = 0.0
    grand_duration_cnt = 0

    for row in rows:
        total = int(row.total or 0)
        demo = int(row.demo_cnt or 0)
        cache = int(row.cache_cnt or 0)
        avg_ms = float(row.avg_ms) if row.avg_ms is not None else None

        grand_total += total
        grand_demo += demo
        grand_cache += cache
        if avg_ms is not None:
            grand_duration_sum += avg_ms * total
            grand_duration_cnt += total

        endpoint_stats.append(
            EndpointStat(
                endpoint=row.endpoint,
                total_requests=total,
                demo_requests=demo,
                live_requests=total - demo,
                cache_hits=cache,
                avg_duration_ms=round(avg_ms, 1) if avg_ms is not None else None,
                p95_duration_ms=None,
            )
        )

    overall_avg = (
        round(grand_duration_sum / grand_duration_cnt, 1)
        if grand_duration_cnt > 0
        else None
    )

    return EventSummaryResponse(
        total_requests=grand_total,
        demo_ratio=round(grand_demo / grand_total, 4) if grand_total else 0.0,
        cache_hit_ratio=round(grand_cache / grand_total, 4) if grand_total else 0.0,
        avg_duration_ms=overall_avg,
        endpoints=endpoint_stats,
        generated_at=_utcnow().isoformat(),
    )
