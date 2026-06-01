"""Pydantic schemas for risk endpoints."""

from pydantic import BaseModel, Field


class VaRRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=50)
    confidence: float = Field(default=0.95, ge=0.9, le=0.999)
    horizon_days: int = Field(default=1, ge=1, le=252)
    method: str = Field(default="historical", pattern=r"^(historical|parametric|monte_carlo)$")
    lookback_days: int = Field(default=504, ge=60, le=2520)


class VaRResponse(BaseModel):
    var_pct: float
    cvar_pct: float
    method: str
    confidence: float
    horizon_days: int
    lookback_days: int
