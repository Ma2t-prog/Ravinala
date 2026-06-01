"""
schemas/portfolio.py — Portfolio optimization schemas.

Étape 13 — Frontend/Backend Boundary
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class OptimizationObjective(str, Enum):
    max_sharpe = "max_sharpe"
    min_variance = "min_variance"
    risk_parity = "risk_parity"


class OptimizeRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=50)
    objective: OptimizationObjective = OptimizationObjective.max_sharpe
    risk_free_rate: float | None = None
    lookback_days: int = Field(default=252, ge=30, le=1260)
    max_weight: float = Field(default=1.0, ge=0.01, le=1.0)
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)


class AssetWeight(BaseModel):
    ticker: str
    weight: float
    expected_return: float | None = None
    volatility: float | None = None


class EfficientFrontierPoint(BaseModel):
    expected_return: float
    volatility: float


class OptimizeResponse(BaseModel):
    objective: str
    weights: list[AssetWeight]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    risk_free_rate_used: float
    diversification_ratio: float | None = None
    efficient_frontier: list[EfficientFrontierPoint] = Field(default_factory=list)


class OptimizeAsyncResponse(BaseModel):
    status: Literal["PENDING", "COMPLETED_SYNC"]
    job_id: str | None = None
    result: OptimizeResponse | None = None
