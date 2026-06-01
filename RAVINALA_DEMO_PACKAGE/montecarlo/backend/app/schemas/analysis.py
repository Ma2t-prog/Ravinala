"""
schemas/analysis.py — Company analysis schemas.

Étape 13 — Frontend/Backend Boundary
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalysisModule(str, Enum):
    fundamentals = "fundamentals"
    dcf = "dcf"
    monte_carlo = "monte_carlo"
    ratios = "ratios"
    peers = "peers"


class CompanyAnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    modules: list[AnalysisModule] = Field(
        default_factory=lambda: [AnalysisModule.fundamentals, AnalysisModule.ratios]
    )


class FundamentalsResult(BaseModel):
    market_cap: float | None = None
    enterprise_value: float | None = None
    revenue: float | None = None
    net_income: float | None = None
    eps: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    roe: float | None = None
    roa: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    sector: str = ""
    industry: str = ""
    description: str = ""


class DCFResult(BaseModel):
    intrinsic_value: float | None = None
    current_price: float | None = None
    upside_pct: float | None = None
    wacc: float | None = None
    terminal_growth_rate: float | None = None
    fcf_projections: list[float] = Field(default_factory=list)


class MonteCarloResult(BaseModel):
    simulations: int = 0
    mean_price: float | None = None
    median_price: float | None = None
    percentile_5: float | None = None
    percentile_95: float | None = None
    probability_above_current: float | None = None


class RatiosResult(BaseModel):
    profitability: dict[str, float | None] = Field(default_factory=dict)
    liquidity: dict[str, float | None] = Field(default_factory=dict)
    leverage: dict[str, float | None] = Field(default_factory=dict)
    efficiency: dict[str, float | None] = Field(default_factory=dict)
    valuation: dict[str, float | None] = Field(default_factory=dict)


class PeersResult(BaseModel):
    peer_tickers: list[str] = Field(default_factory=list)
    comparison: list[dict] = Field(default_factory=list)


class CompanyAnalysisResponse(BaseModel):
    ticker: str
    company_name: str = ""
    fundamentals: FundamentalsResult | None = None
    dcf: DCFResult | None = None
    monte_carlo: MonteCarloResult | None = None
    ratios: RatiosResult | None = None
    peers: PeersResult | None = None


class CompanyAnalysisAsyncResponse(BaseModel):
    """
    Async dispatch payload for company analysis.

    - PENDING: Celery accepted the job and returns `job_id`.
    - COMPLETED_SYNC: Celery unavailable, analysis executed synchronously.
    """

    status: Literal["PENDING", "COMPLETED_SYNC"]
    job_id: str | None = None
    result: CompanyAnalysisResponse | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "CompanyAnalysisAsyncResponse":
        if self.status == "PENDING":
            if not self.job_id:
                raise ValueError("job_id is required when status is PENDING")
            if self.result is not None:
                raise ValueError("result must be omitted when status is PENDING")
            return self

        if self.status == "COMPLETED_SYNC":
            if self.result is None:
                raise ValueError("result is required when status is COMPLETED_SYNC")
            if self.job_id is not None:
                raise ValueError("job_id must be omitted when status is COMPLETED_SYNC")
            return self

        raise ValueError("status must be one of: PENDING, COMPLETED_SYNC")
