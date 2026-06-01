"""
routes/universe.py — Universe search, screening & instrument detail.

Étape 13 — Frontend/Backend Boundary
──────────────────────────────────────
Endpoints:
  GET  /api/v1/universe/search        — free-text search across instruments
  POST /api/v1/universe/screen        — multi-criteria screener
  GET  /api/v1/universe/{ticker}      — single instrument detail
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.executor import get_shared_executor
from app.schemas.envelope import ApiResponse
from app.schemas.universe import (
    InstrumentResponse,
    ScreenerRequest,
    ScreenerResponse,
    UniverseSearchResponse,
)
from app.services.universe_service import (
    get_instrument_detail,
    screen_universe,
    search_universe,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/universe", tags=["universe"])


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _search_sync(query: str, asset_class: str | None, limit: int) -> dict:
    """Delegate search to the service layer."""
    return search_universe(query=query, asset_class=asset_class, limit=limit)


def _screen_sync(req: ScreenerRequest) -> dict:
    """Delegate screening to the service layer."""
    return screen_universe(req)


def _detail_sync(ticker: str) -> InstrumentResponse | None:
    """Delegate detail lookup to the service layer."""
    return get_instrument_detail(ticker)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/search", response_model=ApiResponse[UniverseSearchResponse])
async def universe_search(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    asset_class: str | None = Query(None, description="Filter by asset class"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
):
    """Search instruments by ticker, name, or sector."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _search_sync, q, asset_class, limit)
    except Exception as exc:
        logger.error(f"Universe search failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        data=UniverseSearchResponse(**result),
        data_quality="live",
    )


@router.post("/screen", response_model=ApiResponse[ScreenerResponse])
async def universe_screen(req: ScreenerRequest):
    """Screen instruments with multi-criteria filters."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _screen_sync, req)
    except Exception as exc:
        logger.error(f"Universe screener failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        data=ScreenerResponse(**result),
        data_quality="live",
    )


@router.get("/{ticker}", response_model=ApiResponse[InstrumentResponse])
async def universe_instrument_detail(ticker: str):
    """Get detailed information for a single instrument."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _detail_sync, ticker)
    except Exception as exc:
        logger.error(f"Instrument detail failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    if result is None:
        raise HTTPException(status_code=404, detail=f"Instrument '{ticker}' not found in universe")

    return ApiResponse(
        data=result,
        data_quality="live",
    )
