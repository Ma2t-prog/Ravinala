"""Pydantic schemas for backtest endpoints."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy: str
    tickers: list[str] = Field(min_length=1, max_length=20)
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100000, gt=0)
    commission_pct: float = Field(default=0.001, ge=0, le=0.05)
    slippage_pct: float = Field(default=0.0005, ge=0, le=0.05)
    benchmark: str = "SPY"
    seed: Optional[int] = None


class BacktestMetrics(BaseModel):
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    total_trades: int
    win_rate: float
    profit_factor: Optional[float] = None


class BacktestRunResponse(BaseModel):
    id: UUID
    strategy_name: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    warnings: list[str] = []
    created_at: datetime
