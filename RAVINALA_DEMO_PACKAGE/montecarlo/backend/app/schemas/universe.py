"""
schemas/universe.py — Universe search & screening schemas.

Étape 13 — Frontend/Backend Boundary
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssetClassEnum(str, Enum):
    equity = "equity"
    fixed_income = "fixed_income"
    commodity = "commodity"
    crypto = "crypto"
    real_estate = "real_estate"
    cash = "cash"
    other = "other"


class InstrumentResponse(BaseModel):
    ticker: str
    name: str
    asset_class: str
    sector: str = ""
    country: str = ""
    exchange: str = ""
    currency: str = "USD"
    price: float | None = None
    price_change_1d: float | None = None
    price_change_1m: float | None = None
    price_change_1y: float | None = None
    volume_avg_30d: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    volatility_1y: float | None = None
    beta: float | None = None
    sharpe_1y: float | None = None
    esg_score: float | None = None


class ScreenerRequest(BaseModel):
    asset_classes: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    search_query: str = ""
    pe_min: float | None = None
    pe_max: float | None = None
    pb_min: float | None = None
    pb_max: float | None = None
    dividend_yield_min: float | None = None
    dividend_yield_max: float | None = None
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    volatility_max: float | None = None
    sharpe_min: float | None = None
    esg_score_min: float | None = None
    limit: int = Field(default=50, ge=1, le=500)


class ScreenerResponse(BaseModel):
    total: int
    instruments: list[InstrumentResponse]
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class UniverseSearchResponse(BaseModel):
    query: str
    total: int
    results: list[InstrumentResponse]
