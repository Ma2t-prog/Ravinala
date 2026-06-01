"""
providers/base.py — Canonical types and abstract provider interface.

All market data flows through these types.  Concrete providers (yfinance,
Bloomberg, etc.) implement MarketDataProvider, returning canonical models.
DataFetcher then delegates to the active provider instead of calling
yfinance directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Canonical value objects ──────────────────────────────────────────────

class DataQualityLevel(str, Enum):
    live = "live"
    demo_static = "demo_static"
    stale_cache = "stale_cache"
    error = "error"


class ProviderStatus(BaseModel):
    provider: str
    reachable: bool
    latency_ms: Optional[float] = None
    last_checked: datetime


class CanonicalQuote(BaseModel):
    """Single equity / index / commodity price point."""
    symbol: str
    name: str
    price: float
    change_absolute: float = 0.0
    change_percent: float = 0.0
    timestamp: datetime
    data_quality: DataQualityLevel = DataQualityLevel.live
    source: str = "unknown"


class CanonicalFXRate(BaseModel):
    """Single FX pair snapshot."""
    pair: str
    bid: float
    ask: float
    mid: float
    change_percent: float = 0.0
    timestamp: datetime
    data_quality: DataQualityLevel = DataQualityLevel.live


class CanonicalBond(BaseModel):
    """Government bond yield curve point."""
    country: str
    country_code: str
    yield_2y: float
    yield_5y: float
    yield_10y: float
    spread_vs_bund_bp: float = 0.0
    timestamp: datetime
    data_quality: DataQualityLevel = DataQualityLevel.demo_static


class CanonicalMacro(BaseModel):
    """Macro indicator reading."""
    country: str
    indicator: str
    latest_value: float
    unit: str
    forecast_value: Optional[float] = None
    previous_value: Optional[float] = None
    source: str = ""
    timestamp: datetime
    data_quality: DataQualityLevel = DataQualityLevel.demo_static


class CanonicalPriceBar(BaseModel):
    """OHLCV bar (for historical series)."""
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    adj_close: Optional[float] = None


# ─── Abstract provider ────────────────────────────────────────────────────

class MarketDataProvider(ABC):
    """
    Interface that every data source must implement.

    Concrete implementations: YFinanceProvider, (future) BloombergProvider, etc.
    """

    @abstractmethod
    def fetch_quotes(self, symbols: dict[str, tuple[str, str]], limit: int = 30) -> list[CanonicalQuote]:
        """Fetch live quotes for a dict of {ticker: (name, region)}."""
        ...

    @abstractmethod
    def fetch_fx(self, pairs: dict[str, str]) -> list[CanonicalFXRate]:
        """Fetch FX prices for {ticker: display_name}."""
        ...

    @abstractmethod
    def fetch_commodities(self, symbols: dict[str, tuple[str, str]]) -> list[CanonicalQuote]:
        """Fetch commodity prices."""
        ...

    @abstractmethod
    def fetch_bonds(self) -> list[CanonicalBond]:
        """Fetch government bond yields."""
        ...

    @abstractmethod
    def fetch_macro(self) -> list[CanonicalMacro]:
        """Fetch macro indicators."""
        ...

    @abstractmethod
    def health_check(self) -> ProviderStatus:
        """Quick connectivity check."""
        ...
