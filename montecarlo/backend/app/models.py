"""
Data models for API responses (Pydantic v2)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════
# SNAPSHOT & ASSET RESPONSES
# ═══════════════════════════════════════════════════════════════════════════

class PriceChangeModel(BaseModel):
    """Price change with direction and sentiment."""
    absolute: float = Field(..., description="Absolute change in price")
    percent: float = Field(..., description="Percentage change")
    direction: str = Field(..., description="'up' | 'down' | 'flat'")
    color: str = Field(default="neutral", description="Color code for UI: 'green'|'red'|'neutral'")

class AssetModel(BaseModel):
    """Base asset model (index, commodity, FX, etc.)."""
    symbol: str
    name: str
    region: str
    price: float
    change: PriceChangeModel
    timestamp: datetime
    is_stale: bool = Field(default=False, description="data > 30min old")
    data_source: str = Field(default="yfinance")

class IndicesSnapshotModel(BaseModel):
    """30 global indices grouped by zone."""
    americas: List[AssetModel]
    europe: List[AssetModel]
    asia_pacific: List[AssetModel]
    middle_east_other: List[AssetModel]
    last_updated: datetime
    cache_age_seconds: int

class BondModel(BaseModel):
    """Government bond yield model."""
    country: str
    country_code: str
    yield_2y: Optional[float]
    yield_5y: Optional[float]
    yield_10y: Optional[float]
    spread_vs_bund_bp: Optional[float]
    curve_slope_percent: Optional[float]
    direction: str = Field(default="flat")
    last_updated: datetime

class BondsSnapshotModel(BaseModel):
    """Bond yields for 20 countries."""
    bonds: List[BondModel]
    benchmark_country: str = "Germany"
    last_updated: datetime
    cache_age_seconds: int
    data_quality: Optional[str] = None
    data_quality_note: Optional[str] = None

class FXPairModel(BaseModel):
    """Foreign exchange pair."""
    pair: str
    bid: float
    ask: float
    mid_price: float
    change_percent: float
    volatility_percent: Optional[float]
    last_updated: datetime

class FXSnapshotModel(BaseModel):
    """FX 20 major pairs."""
    usd_base: List[FXPairModel]
    crosses: List[FXPairModel]
    last_updated: datetime
    cache_age_seconds: int

class CommodityModel(BaseModel):
    """Commodity (metal, energy, agro, crypto)."""
    symbol: str
    name: str
    category: str
    price: float
    unit: str
    change_percent: float
    timestamp: datetime

class CommoditiesSnapshotModel(BaseModel):
    """Commodities grouped by category."""
    metals: List[CommodityModel]
    energy: List[CommodityModel]
    agriculture: List[CommodityModel]
    crypto: List[CommodityModel]
    last_updated: datetime
    cache_age_seconds: int

class MacroIndicatorModel(BaseModel):
    """Single macro indicator reading."""
    country: str
    indicator: str
    latest_value: float
    unit: str
    forecast_value: Optional[float]
    previous_value: Optional[float]
    release_date: Optional[datetime]
    source: str
    sentiment: str = Field(default="neutral", description="'positive'|'neutral'|'negative'")

class MacroSnapshotModel(BaseModel):
    """Macro data: CPI, PMI, GDP, unemployment, etc."""
    indicators: List[MacroIndicatorModel]
    last_updated: datetime
    cache_age_seconds: int
    data_quality: Optional[str] = None
    data_quality_note: Optional[str] = None

class FullDashboardModel(BaseModel):
    """Complete dashboard snapshot."""
    indices: IndicesSnapshotModel
    bonds: BondsSnapshotModel
    fx: FXSnapshotModel
    commodities: CommoditiesSnapshotModel
    macro: MacroSnapshotModel
    timestamp: datetime
    cache_hit: bool = Field(default=True)
    etag: Optional[str] = None


class SnapshotResponseModel(BaseModel):
    """
    Dashboard snapshot response.

    Supports both full snapshots and section-filtered snapshots.
    """
    indices: Optional[IndicesSnapshotModel] = None
    bonds: Optional[BondsSnapshotModel] = None
    fx: Optional[FXSnapshotModel] = None
    commodities: Optional[CommoditiesSnapshotModel] = None
    macro: Optional[MacroSnapshotModel] = None
    timestamp: Optional[datetime] = None
    cache_hit: bool = Field(default=True)
    etag: Optional[str] = None


class CacheRefreshResponseModel(BaseModel):
    """Cache refresh status."""
    status: Literal["refreshed"]
    section: str

# ═══════════════════════════════════════════════════════════════════════════
# EXPORT REQUESTS
# ═══════════════════════════════════════════════════════════════════════════

class ExcelExportRequest(BaseModel):
    """Excel export request."""
    sheets: List[str] = Field(default=["indices", "bonds", "fx", "commodities"])
    include_charts: bool = False
    timestamp_format: str = "YYYY-MM-DD HH:mm UTC"

class PDFExportRequest(BaseModel):
    """PDF export request."""
    layout: str = Field(default="dashboard")  # "dashboard" | "report"
    include_charts: bool = True
    page_orientation: str = "landscape"

class EmailExportRequest(BaseModel):
    """Email export request."""
    recipients: List[str]
    format: str = Field(default="pdf")  # "pdf" | "excel" | "both"
    subject: Optional[str] = None
    include_timestamp: bool = True

# ═══════════════════════════════════════════════════════════════════════════
# ERROR & STATUS
# ═══════════════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = None

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    redis_connected: bool
    data_service_ok: bool
    # Étape 2 — persistence layer: "connected" | "not_configured"
    db_status: str = "not_configured"


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT GENERATION MODELS
# ═══════════════════════════════════════════════════════════════════════════

class ProductParams(BaseModel):
    """Parameters for structured product document generation."""
    product_type: Literal[
        "european_call", "european_put", "barrier",
        "autocall", "phoenix", "himalaya", "cliquet",
        "variance_swap", "convertible_bond", "cln"
    ] = "european_call"
    underlying: str = "CAC 40"
    currency: str = "EUR"
    issuer: str = "Ravinala Capital"
    spot: float
    strike: Optional[float] = None
    maturity_years: float
    risk_free_rate: float
    volatility: float
    dividend_yield: float = 0.0
    notional: float = 1.0
    # Barriers
    barrier_level: Optional[float] = None
    barrier_type: Optional[Literal[
        "up-and-out", "down-and-in", "up-and-in", "down-and-out"
    ]] = None
    # Autocall / Phoenix
    autocall_levels: Optional[List[float]] = None
    coupon_rate: Optional[float] = None
    capital_protection: Optional[float] = None
    # Multi-asset
    correlation_matrix: Optional[List[List[float]]] = None
    underlyings: Optional[List[str]] = None
    # Document metadata
    client_name: Optional[str] = None
    product_name: Optional[str] = None
    include_backtesting: bool = False
    language: Literal["fr", "en"] = "fr"

    model_config = {"json_schema_extra": {"example": {
        "product_type": "european_call",
        "underlying": "CAC 40",
        "spot": 7500.0,
        "strike": 7500.0,
        "maturity_years": 1.0,
        "risk_free_rate": 0.03,
        "volatility": 0.20,
        "capital_protection": 0.90,
        "coupon_rate": 0.08,
        "issuer": "Ravinala Capital",
    }}}


class ScenarioBookParams(ProductParams):
    """Extended parameters for scenario book generation."""
    backtest_period_years: float = 5.0
    reference_asset: Optional[str] = None
    var_confidence: float = 0.95


__all__ = [
    "PriceChangeModel",
    "AssetModel",
    "IndicesSnapshotModel",
    "BondModel",
    "BondsSnapshotModel",
    "FXPairModel",
    "FXSnapshotModel",
    "CommodityModel",
    "CommoditiesSnapshotModel",
    "MacroIndicatorModel",
    "MacroSnapshotModel",
    "FullDashboardModel",
    "SnapshotResponseModel",
    "CacheRefreshResponseModel",
    "ExcelExportRequest",
    "PDFExportRequest",
    "EmailExportRequest",
    "ErrorResponse",
    "HealthCheckResponse",
    "ProductParams",
    "ScenarioBookParams",
]
