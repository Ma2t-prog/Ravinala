"""
services/universe_service.py - universe search and screening orchestration.

Keeps the legacy bridge to `src/genesix.universe_explorer` out of the route
layer and centralises result normalization.
"""

from __future__ import annotations

from typing import Any

from app.schemas.universe import InstrumentResponse, ScreenerRequest
from app.services.legacy_quant_bridge import import_legacy_module


def _load_universe_module():
    """Lazy-load the legacy universe explorer module from `src`."""
    return import_legacy_module("genesix.universe_explorer")


def _get_pipeline():
    universe_explorer = _load_universe_module()
    return universe_explorer.get_pipeline()


def instrument_to_response(inst: Any) -> InstrumentResponse:
    """Convert a genesix instrument object to the backend API schema."""
    return InstrumentResponse(
        ticker=inst.ticker,
        name=inst.name,
        asset_class=inst.asset_class.value if hasattr(inst.asset_class, "value") else str(inst.asset_class),
        sector=inst.sector or "",
        country=inst.country or "",
        exchange=inst.exchange or "",
        currency=inst.currency or "USD",
        price=inst.price,
        price_change_1d=getattr(inst, "price_change_1d", None),
        price_change_1m=getattr(inst, "price_change_1m", None),
        price_change_1y=getattr(inst, "price_change_1y", None),
        volume_avg_30d=getattr(inst, "volume_avg_30d", None),
        market_cap=inst.market_cap,
        pe_ratio=inst.pe_ratio,
        pb_ratio=inst.pb_ratio,
        dividend_yield=inst.dividend_yield,
        volatility_1y=inst.volatility_1y,
        beta=inst.beta,
        sharpe_1y=inst.sharpe_1y,
        esg_score=inst.esg_score,
    )


def search_universe(
    *,
    query: str,
    asset_class: str | None,
    limit: int,
) -> dict[str, Any]:
    """Search the universe and return normalized API payload data."""
    universe_explorer = _load_universe_module()
    pipeline = _get_pipeline()
    instruments = pipeline.get_instruments()

    criteria = universe_explorer.ScreenerCriteria(search_query=query)
    if asset_class:
        try:
            criteria.asset_classes = [universe_explorer.AssetClass(asset_class)]
        except ValueError:
            pass

    engine = universe_explorer.ScreenerEngine(instruments)
    result = engine.screen(criteria)
    items = result.instruments[:limit]

    return {
        "query": query,
        "total": len(items),
        "results": [instrument_to_response(item) for item in items],
    }


def screen_universe(req: ScreenerRequest) -> dict[str, Any]:
    """Run the multi-criteria screener and return normalized payload data."""
    universe_explorer = _load_universe_module()
    pipeline = _get_pipeline()
    instruments = pipeline.get_instruments()

    criteria = universe_explorer.ScreenerCriteria(
        pe_min=req.pe_min,
        pe_max=req.pe_max,
        pb_min=req.pb_min,
        pb_max=req.pb_max,
        dividend_yield_min=req.dividend_yield_min,
        dividend_yield_max=req.dividend_yield_max,
        market_cap_min=req.market_cap_min,
        market_cap_max=req.market_cap_max,
        volatility_max=req.volatility_max,
        sharpe_min=req.sharpe_min,
        esg_score_min=req.esg_score_min,
        search_query=req.search_query or None,
        sectors=req.sectors or None,
        countries=req.countries or None,
    )
    if req.asset_classes:
        try:
            criteria.asset_classes = [universe_explorer.AssetClass(ac) for ac in req.asset_classes]
        except ValueError:
            pass

    engine = universe_explorer.ScreenerEngine(instruments)
    result = engine.screen(criteria)
    items = result.instruments[: req.limit]

    filters_applied = {
        key: value
        for key, value in req.model_dump().items()
        if value is not None and value != [] and value != ""
    }

    return {
        "total": result.total_count,
        "instruments": [instrument_to_response(item) for item in items],
        "filters_applied": filters_applied,
    }


def get_instrument_detail(ticker: str) -> InstrumentResponse | None:
    """Fetch a single instrument detail by ticker."""
    pipeline = _get_pipeline()
    instruments = pipeline.get_instruments()

    ticker_upper = ticker.upper()
    for instrument in instruments:
        if instrument.ticker.upper() == ticker_upper:
            return instrument_to_response(instrument)
    return None
