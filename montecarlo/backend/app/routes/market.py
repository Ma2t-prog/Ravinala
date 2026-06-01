"""
routes/market.py — Market data endpoints.

Étape 3 — Structuration backend
─────────────────────────────────
Routes:
  GET  /api/v1/snapshot
  GET  /api/v1/indices
  GET  /api/v1/bonds
  GET  /api/v1/fx-pairs
  GET  /api/v1/commodities
  GET  /api/v1/macro
  POST /api/v1/refresh
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Header, Query

from app.models import (
    BondsSnapshotModel,
    CacheRefreshResponseModel,
    CommoditiesSnapshotModel,
    FXSnapshotModel,
    IndicesSnapshotModel,
    MacroSnapshotModel,
    SnapshotResponseModel,
)
from app.schemas.envelope import ApiError
from app.services.cache import get_cache
from app.services.snapshot_service import (
    get_bonds_async,
    get_commodities_async,
    get_fx_async,
    get_full_snapshot_async,
    get_indices_async,
    get_macro_async,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["market"])

_ERROR_RESPONSES = {
    500: {"model": ApiError, "description": "Provider error or internal failure"},
    504: {"model": ApiError, "description": "Provider timeout"},
}

_ALLOWED_SECTIONS = frozenset(["indices", "bonds", "fx", "commodities", "macro"])

_CACHE_SECTIONS = frozenset(["indices", "fx", "commodities", "bonds", "macro", "snapshot"])


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/snapshot",
    response_model=SnapshotResponseModel,
    responses={**_ERROR_RESPONSES},
    summary="Full dashboard snapshot",
    description=(
        "Returns all market sections in a single call. Cache TTL: 15 min. "
        "Supports ETag for conditional GETs. "
        "Use `sections` to request a subset."
    ),
)
async def snapshot(
    etag: str | None = Header(None),
    sections: str | None = Query(
        None, description="Comma-separated: indices,bonds,fx,commodities,macro"
    ),
) -> dict:
    """Full dashboard snapshot with all sections. Cache: 15 min, ETag supported."""
    data = await get_full_snapshot_async()

    if sections:
        requested = set(sections.split(","))
        unknown = requested - _ALLOWED_SECTIONS
        if unknown:
            logger.warning(f"Unknown sections requested: {unknown}")
        allowed = requested & _ALLOWED_SECTIONS  # only keep valid ones
        filtered = {k: v for k, v in data.items() if k in allowed}
        filtered["timestamp"] = data.get("timestamp")
        filtered["cache_hit"] = data.get("cache_hit", False)
        return filtered

    return data


# ─────────────────────────────────────────────────────────────────────────────
# INDICES
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/indices",
    response_model=IndicesSnapshotModel,
    responses={**_ERROR_RESPONSES},
    summary="Global equity indices",
    description="30 global indices grouped by zone (Americas, Europe, Asia-Pacific, Middle East). Cache: 5 min. Live via yfinance. data_quality=live.",
)
async def get_indices(
    zones: str | None = Query(
        None, description="Comma-separated: americas,europe,asia,middle_east"
    ),
    limit: int = Query(default=30, ge=1, le=200, description="Max number of indices to return"),
) -> dict:
    """30 global indices grouped by zone. Cache: 5 min."""
    result = await get_indices_async(limit)
    if zones:
        allowed_zones = set(zones.split(","))
        for zone in ["americas", "europe", "asia_pacific", "middle_east_other"]:
            if zone not in allowed_zones:
                result[zone] = []
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BONDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/bonds",
    response_model=BondsSnapshotModel,
    responses={**_ERROR_RESPONSES},
    summary="Government bond yields",
    description="Bond yields for 20 countries across 2Y/5Y/10Y maturities + spread vs Bund. Cache: 1 hour. \u26a0\ufe0f data_quality=demo_static \u2014 hardcoded reference values.",
)
async def get_bonds(
    countries: str | None = Query(None, description="Comma-separated country codes"),
    maturities: str | None = Query(None, description="Comma-separated: 2Y,5Y,10Y"),
) -> dict:
    """Government bond yields + spreads. Cache: 1 hour."""
    result = await get_bonds_async()
    if countries:
        allowed = set(countries.split(","))
        result["bonds"] = [b for b in result["bonds"] if b.get("country_code") in allowed]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FX PAIRS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/fx-pairs",
    response_model=FXSnapshotModel,
    responses={**_ERROR_RESPONSES},
    summary="Major FX pairs",
    description="20 major FX pairs. Cache: 5 min. Live via yfinance. data_quality=live.",
)
async def get_fx(
    base: str | None = Query("USD"),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    """Major FX pairs. Cache: 5 min."""
    return await get_fx_async()


# ─────────────────────────────────────────────────────────────────────────────
# COMMODITIES
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/commodities",
    response_model=CommoditiesSnapshotModel,
    responses={**_ERROR_RESPONSES},
    summary="Commodities (metals, energy, agriculture, crypto)",
    description="Commodities by category. Cache: 5 min. Live via yfinance. data_quality=live.",
)
async def get_commodities(
    categories: str | None = Query(
        None, description="Comma-separated: metals,energy,agriculture,crypto"
    ),
) -> dict:
    """Commodities by category. Cache: 5 min."""
    result = await get_commodities_async()
    if categories:
        allowed = set(categories.split(","))
        for cat in ["metals", "energy", "agriculture", "crypto"]:
            if cat not in allowed:
                result[cat] = []
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MACRO
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/macro",
    response_model=MacroSnapshotModel,
    responses={**_ERROR_RESPONSES},
    summary="Macro indicators",
    description="CPI, PMI, GDP, unemployment by country. Cache: 1 day. \u26a0\ufe0f data_quality=demo_static \u2014 hardcoded reference values.",
)
async def get_macro(
    countries: str | None = Query(
        None, description="Comma-separated: USA,China,etc"
    ),
) -> dict:
    """Macro indicators (CPI, PMI, GDP, unemployment). Cache: 1 day."""
    result = await get_macro_async()
    if countries:
        allowed = set(countries.split(","))
        result["indicators"] = [
            ind for ind in result["indicators"] if ind.get("country") in allowed
        ]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CACHE REFRESH
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=CacheRefreshResponseModel,
    summary="Force cache refresh",
    description="Clears Redis/in-memory cache for a specific section or all sections. Use `section` query param to target one section.",
)
async def refresh_cache(
    section: str | None = Query(None),
    background_tasks: BackgroundTasks = None,
) -> dict:
    """Force-clear Redis/in-memory cache for a specific section or all sections."""
    cache = get_cache()

    if section and section not in _CACHE_SECTIONS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown section '{section}'. Valid: {sorted(_CACHE_SECTIONS)}")

    if section:
        cache.clear_section(section)
        logger.info(f"🔄 Cleared cache for section: {section}")
        return {"status": "refreshed", "section": section}

    for sec in ["indices", "fx", "commodities", "bonds", "macro", "snapshot"]:
        cache.clear_section(sec)
    logger.info("🔄 Cleared all caches")
    return {"status": "refreshed", "section": "all"}
