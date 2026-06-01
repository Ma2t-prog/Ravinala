"""
routes/events.py — Observability / audit-log read endpoints.

Étape 6 — Observabilité
────────────────────────
Exposes read-only views of the api_events table so operators can inspect
data-quality trends, cache efficiency, and endpoint latency without
leaving the API.

All endpoints degrade gracefully (return a 503 explanation) when
DATABASE_URL is not configured.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.schemas.envelope import ApiError
from app.schemas.events import EventSummaryResponse
from app.services.event_read_service import build_event_summary

router = APIRouter(prefix="/api/v1/events", tags=["observability"])

_NO_DB = HTTPException(
    status_code=503,
    detail="Persistence layer not configured. Set DATABASE_URL to enable event log.",
)

_ERROR_RESPONSES = {503: {"model": ApiError}, 500: {"model": ApiError}}


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=EventSummaryResponse,
    responses=_ERROR_RESPONSES,
    summary="Audit-log summary",
    description=(
        "Returns aggregate statistics from the api_events audit log: "
        "request counts, demo vs live data split, cache hit ratio, "
        "and per-endpoint latency. "
        "Window defaults to the last 24 hours. Requires DATABASE_URL."
    ),
)
async def get_events_summary(
    hours: int = Query(24, ge=1, le=720, description="Lookback window in hours"),
    db: Optional[AsyncSession] = Depends(get_session),
) -> EventSummaryResponse:
    if db is None:
        raise _NO_DB
    return await build_event_summary(db, hours=hours)
