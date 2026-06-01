"""
services/snapshot_service.py — Shared full-snapshot builder.

Étape 3 — Structuration backend
─────────────────────────────────
Extracted from main.py so both routes/market.py and routes/export.py can
import it without circular dependency.
"""

import asyncio
import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import HTTPException

from app.services.cache import get_cache
from app.services.data_fetcher import get_data_fetcher

logger = logging.getLogger(__name__)
_SNAPSHOT_EXECUTOR = ThreadPoolExecutor(max_workers=5, thread_name_prefix="snapshot")


def _utcnow_iso() -> str:
    """Return a timezone-aware UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _build_response_payload(snapshot: dict, *, cache_hit: bool) -> dict:
    """Return an isolated response payload with request-level cache metadata."""
    payload = copy.deepcopy(snapshot)
    payload["cache_hit"] = cache_hit
    return payload


async def get_indices_async(limit: int = 30) -> dict:
    """Fetch equity indices with cache. Section TTL: 5 min."""
    cache = get_cache()
    cached = cache.get("indices:full")
    if cached:
        cached["cache_age_seconds"] = cache.get_age("indices:full") or 0
        return cached
    fetcher = get_data_fetcher()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, lambda: fetcher.fetch_indices(limit))
    # Only cache if we got actual data
    total = sum(len(v) for v in result.values() if isinstance(v, list))
    if total > 0:
        cache.set("indices:full", result, section="indices")
    result["cache_age_seconds"] = 0
    return result


async def get_bonds_async() -> dict:
    """Fetch bond yields with cache. Section TTL: 1 hour."""
    cache = get_cache()
    cached = cache.get("bonds:full")
    if cached:
        cached["cache_age_seconds"] = cache.get_age("bonds:full") or 0
        return cached
    fetcher = get_data_fetcher()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_bonds)
    cache.set("bonds:full", result, section="bonds")
    result["cache_age_seconds"] = 0
    return result


async def get_fx_async() -> dict:
    """Fetch FX pairs with cache. Section TTL: 5 min."""
    cache = get_cache()
    cached = cache.get("fx:full")
    if cached:
        cached["cache_age_seconds"] = cache.get_age("fx:full") or 0
        return cached
    fetcher = get_data_fetcher()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_fx_pairs)
    cache.set("fx:full", result, section="fx")
    result["cache_age_seconds"] = 0
    return result


async def get_commodities_async() -> dict:
    """Fetch commodities with cache. Section TTL: 5 min."""
    cache = get_cache()
    cached = cache.get("commodities:full")
    if cached:
        cached["cache_age_seconds"] = cache.get_age("commodities:full") or 0
        return cached
    fetcher = get_data_fetcher()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_commodities)
    cache.set("commodities:full", result, section="commodities")
    result["cache_age_seconds"] = 0
    return result


async def get_macro_async() -> dict:
    """Fetch macro indicators with cache. Section TTL: 1 day."""
    cache = get_cache()
    cached = cache.get("macro:full")
    if cached:
        cached["cache_age_seconds"] = cache.get_age("macro:full") or 0
        return cached
    fetcher = get_data_fetcher()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_macro)
    cache.set("macro:full", result, section="macro")
    result["cache_age_seconds"] = 0
    return result


async def get_full_snapshot_async() -> dict:
    """
    Build a full dashboard snapshot from all data sources.

    Checks Redis / in-memory cache first (TTL = 15 min).
    On miss, fetches all providers concurrently in a thread pool
    (data_fetcher methods are synchronous / blocking).
    """
    cache = get_cache()

    cached = cache.get("snapshot:full")
    if cached:
        return _build_response_payload(cached, cache_hit=True)

    logger.info("📡 Fetching full snapshot (cache miss)...")
    try:
        fetcher = get_data_fetcher()
        loop = asyncio.get_running_loop()

        # Bonds and macro are fast (static/FRED) — run concurrently
        bonds, macro = await asyncio.gather(
            loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_bonds),
            loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_macro),
        )

        # yfinance fetchers run sequentially to avoid Yahoo Finance rate-limiting
        indices = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_indices)
        await asyncio.sleep(0.3)
        fx = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_fx_pairs)
        await asyncio.sleep(0.3)
        commodities = await loop.run_in_executor(_SNAPSHOT_EXECUTOR, fetcher.fetch_commodities)

        snapshot = {
            "indices": indices,
            "bonds": bonds,
            "fx": fx,
            "commodities": commodities,
            "macro": macro,
            "timestamp": _utcnow_iso(),
        }

        cache.set("snapshot:full", snapshot, section="snapshot")

        # Also populate individual section caches so per-section endpoints
        # don't trigger a second yfinance fetch right after warm-up.
        def _has_data(section_dict: dict) -> bool:
            return any(isinstance(v, list) and v for v in section_dict.values())

        if _has_data(indices):
            cache.set("indices:full", indices, section="indices")
        if _has_data(fx):
            cache.set("fx:full", fx, section="fx")
        if _has_data(commodities):
            cache.set("commodities:full", commodities, section="commodities")
        cache.set("bonds:full", bonds, section="bonds")
        cache.set("macro:full", macro, section="macro")

        return _build_response_payload(snapshot, cache_hit=False)

    except Exception as exc:
        logger.error(f"❌ Snapshot fetch failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
