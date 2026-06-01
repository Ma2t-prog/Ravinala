"""
Shared quant conventions for src-side analytics engines.

This module mirrors the backend quant baseline so the core research and
analytics engines stop drifting on annualisation and risk-free assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QuantConventions:
    """Immutable platform defaults for annualisation and performance metrics."""

    trading_days_per_year: int = 252
    risk_free_rate: float = 0.043
    risk_free_rate_source: str = "US 10Y Treasury demo baseline"
    risk_free_rate_last_updated: str = "2026-03-23"
    standard_horizons: tuple[int, ...] = field(default_factory=lambda: (1, 5, 21, 63, 252))

    @property
    def annualization_factor_return(self) -> float:
        return float(self.trading_days_per_year)

    @property
    def annualization_factor_vol(self) -> float:
        return sqrt(self.trading_days_per_year)


CONVENTIONS = QuantConventions()

TRADING_DAYS = CONVENTIONS.trading_days_per_year
RISK_FREE_RATE = CONVENTIONS.risk_free_rate
RISK_FREE_RATE_SOURCE = CONVENTIONS.risk_free_rate_source
RISK_FREE_RATE_LAST_UPDATED = CONVENTIONS.risk_free_rate_last_updated
STANDARD_HORIZONS = CONVENTIONS.standard_horizons
ANNUALIZATION_FACTOR_RETURN = CONVENTIONS.annualization_factor_return
ANNUALIZATION_FACTOR_VOL = CONVENTIONS.annualization_factor_vol

TIMEFRAME_PERIODS_PER_YEAR: dict[str, int] = {
    "1m": TRADING_DAYS * 390,
    "5m": TRADING_DAYS * 78,
    "15m": TRADING_DAYS * 26,
    "30m": TRADING_DAYS * 13,
    "1h": int(TRADING_DAYS * 6.5),
    "4h": TRADING_DAYS * 2,
    "1d": TRADING_DAYS,
    "1w": 52,
    "1M": 12,
}


def annualize_return_from_mean(
    daily_mean_return: float,
    *,
    trading_days: int = TRADING_DAYS,
) -> float:
    """Arithmetic annualisation for average daily returns."""

    return float(daily_mean_return) * float(trading_days)


def annualize_geometric_return(
    daily_returns: Iterable[float],
    *,
    trading_days: int = TRADING_DAYS,
) -> float:
    """Compound annual growth rate from a daily return series."""

    series = np.asarray(list(daily_returns), dtype=float)
    if series.size == 0:
        return 0.0
    return float(np.prod(1.0 + series) ** (float(trading_days) / float(series.size)) - 1.0)


def annualize_volatility(
    daily_std: float,
    *,
    annualization_factor: float = ANNUALIZATION_FACTOR_VOL,
) -> float:
    """Annualise daily volatility with the platform convention."""

    return float(daily_std) * float(annualization_factor)


def sharpe_ratio(
    annual_return: float,
    annual_volatility: float,
    *,
    risk_free_rate: float = RISK_FREE_RATE,
) -> float:
    """Compute ex-post Sharpe ratio with the platform risk-free baseline."""

    if annual_volatility <= 1e-12:
        return 0.0
    return (float(annual_return) - float(risk_free_rate)) / float(annual_volatility)


def periods_per_year_for_timeframe(timeframe: str | None, *, fallback: int = TRADING_DAYS) -> int:
    """Resolve a UI/data timeframe to an annualisation frequency."""

    if not timeframe:
        return int(fallback)
    return int(TIMEFRAME_PERIODS_PER_YEAR.get(str(timeframe), fallback))


def infer_periods_per_year(index: pd.Index | Iterable[object], *, fallback: int = TRADING_DAYS) -> int:
    """Infer annualisation frequency from a datetime-like index."""

    try:
        idx = pd.Index(index)
        if len(idx) < 2:
            return int(fallback)
        if not isinstance(idx, pd.DatetimeIndex):
            idx = pd.to_datetime(idx)
        deltas = idx.to_series().diff().dropna()
        if deltas.empty:
            return int(fallback)
        median_seconds = float(deltas.dt.total_seconds().median())
    except Exception:
        return int(fallback)

    if median_seconds <= 90:
        return TIMEFRAME_PERIODS_PER_YEAR["1m"]
    if median_seconds <= 7.5 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["5m"]
    if median_seconds <= 22.5 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["15m"]
    if median_seconds <= 45 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["30m"]
    if median_seconds <= 90 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["1h"]
    if median_seconds <= 6 * 60 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["4h"]
    if median_seconds <= 36 * 60 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["1d"]
    if median_seconds <= 10 * 24 * 60 * 60:
        return TIMEFRAME_PERIODS_PER_YEAR["1w"]
    return TIMEFRAME_PERIODS_PER_YEAR["1M"]
