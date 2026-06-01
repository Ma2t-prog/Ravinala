"""Pydantic schemas for governed risk API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class RiskComputeRequest(BaseModel):
    asset: str = Field(..., min_length=1, max_length=20, description="Ticker symbol")
    period: str = Field(default="5y", description="yfinance period for price data")
    portfolio_value: float = Field(
        default=100_000.0,
        gt=0,
        description="Notional for stress tests",
    )


class ConventionsResponse(BaseModel):
    trading_days_per_year: int
    risk_free_rate: float
    risk_free_rate_source: str
    risk_free_rate_last_updated: str
    return_type: str
    ann_factor_vol: float
    var_confidence_levels: list[float]
    var_sign_convention: str
    var_min_observations: int
    rolling_windows: list[int]
    default_rolling_window: int
    mc_simulations: int
    data_source_policy: str
    stale_data_threshold_days: int
    min_history_for_governed: int


class RiskComputeResponse(BaseModel):
    asset: str
    period: str
    report: dict[str, Any]


class RiskAsyncResponse(BaseModel):
    job_id: str
    status: Literal["PENDING"] = "PENDING"


class RiskMetricSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    category: str
    governance_level: str
    method: str
    formula: str
    sign_convention: str
    confidence: float | list[float] | str
    horizons: list[int] | str
    horizon_scaling: str
    min_observations: int
    annualisation: str
    risk_free_rate: str
    limitations: list[str]
    what_to_keep_simple: str
    what_to_defer: str


class RiskMetricsCatalog(RootModel[dict[str, RiskMetricSpec]]):
    """Catalog of metric specifications keyed by metric name."""


class GovernanceLevelInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    description: str
    usable_for_decisions: bool


class GovernanceLevelsCatalog(RootModel[dict[str, GovernanceLevelInfo]]):
    """Governance level dictionary keyed by level name."""


class RiskIncoherenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issue: str
    detail: str
    correction: str
    status: str


class RiskCorrectionPlanStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    step: str
    action: str
    status: str


class RiskIncoherencesResponse(BaseModel):
    incoherences: list[RiskIncoherenceItem]
    correction_plan: list[RiskCorrectionPlanStep]


class RiskSnapshotRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str
    asset: str
    computed_at: datetime
    data_source: str
    n_observations: int
    metrics: dict[str, Any]
    conventions_used: dict[str, Any]
    governance_summary: dict[str, Any]

