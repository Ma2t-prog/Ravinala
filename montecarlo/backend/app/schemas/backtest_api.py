"""Pydantic schemas for the backtest API slice."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    assets: list[str] = Field(..., min_length=1, max_length=50, description="Tickers to trade")
    strategy: str = Field(default="momentum", description="Strategy name")
    benchmark: str = Field(default="SPY", description="Benchmark ticker")
    period: str = Field(default="5y", description="yfinance period for price data")
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_bps: float = Field(default=5.0, ge=0, le=100)
    slippage_bps: float = Field(default=5.0, ge=0, le=100)
    risk_free_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional annualised override. Defaults to governed backend convention.",
    )
    seed: int | None = Field(default=42, ge=0)
    params: dict[str, Any] | None = Field(default=None, description="Strategy-specific params")


class RunSummary(BaseModel):
    run_id: str
    run_name: str
    strategy: str
    level: str
    status: str
    assets: list[str]
    start_date: str
    end_date: str
    total_return: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    risk_free_rate_used: float | None = None
    n_trades: int = 0
    deployment_policy: str


class TradeOut(BaseModel):
    trade_date: str
    asset: str
    side: str
    quantity: float
    price: float
    commission: float
    slippage: float
    portfolio_value: float
    cash_after: float
    reason: str = ""


class CostModelResponse(BaseModel):
    name: str = "flat_bps"
    commission_bps: float
    slippage_bps: float


class FullRunResponse(BaseModel):
    run_id: str
    run_name: str
    strategy: str
    level: str
    status: str
    assets: list[str]
    benchmark: str
    start_date: str
    end_date: str
    params: dict[str, Any]
    seed: int | None
    initial_capital: float
    cost_model: CostModelResponse
    metrics: dict[str, float]
    benchmark_metrics: dict[str, float]
    risk_free_rate_used: float | None = None
    limitations: dict[str, dict[str, str]]
    deployment_policy: str
    n_trades: int
    duration_seconds: float
    error_message: str | None = None


class BacktestRunResponse(BaseModel):
    primary: FullRunResponse
    baseline_buy_hold: FullRunResponse
    baseline_equal_weight: FullRunResponse
    comparison: dict[str, float]


class BacktestAsyncResponse(BaseModel):
    job_id: str
    status: str = "PENDING"


class BacktestLimitationsResponse(BaseModel):
    limitations: dict[str, dict[str, str]]
    deployment_policy: str
