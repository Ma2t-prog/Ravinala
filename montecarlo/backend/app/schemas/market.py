"""Pydantic schemas for market data endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IndexItem(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: Optional[int] = None
    source: str = "yfinance"
    fetched_at: datetime


class FXPair(BaseModel):
    pair: str
    rate: float
    change: float
    change_pct: float
    source: str = "yfinance"


class BondItem(BaseModel):
    name: str
    yield_pct: float
    change: float
    maturity: Optional[str] = None


class CommodityItem(BaseModel):
    name: str
    price: float
    change: float
    change_pct: float
    unit: str = "USD"


class MacroIndicator(BaseModel):
    name: str
    value: float
    previous: Optional[float] = None
    country: str = "US"


class SnapshotResponse(BaseModel):
    indices: list[IndexItem]
    fx_pairs: list[FXPair]
    bonds: list[BondItem]
    commodities: list[CommodityItem]
    timestamp: datetime
    cache_hit: bool = False
