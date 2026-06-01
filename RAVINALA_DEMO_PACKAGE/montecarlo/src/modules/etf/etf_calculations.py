"""
ETF performance, risk, and tracking-error calculations.
All functions accept a pandas Series of daily close prices (date-indexed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class PerformanceMetrics:
    d1: float | None = None      # 1-day return
    w1: float | None = None      # 1-week return
    m1: float | None = None      # 1-month return
    m3: float | None = None      # 3-month return
    m6: float | None = None      # 6-month return
    ytd: float | None = None     # year-to-date return
    y1: float | None = None      # 1-year return
    y3: float | None = None      # 3-year annualised return
    y5: float | None = None      # 5-year annualised return
    inception: float | None = None  # since-inception total return


@dataclass
class RiskMetrics:
    volatility_1y: float | None = None      # annualised 1Y vol
    volatility_3y: float | None = None      # annualised 3Y vol
    sharpe_1y: float | None = None          # Sharpe (risk-free ≈ 0)
    sharpe_3y: float | None = None
    max_drawdown: float | None = None       # maximum drawdown (negative %)
    max_drawdown_start: str | None = None   # drawdown peak date
    max_drawdown_end: str | None = None     # drawdown trough date
    beta: float | None = None               # beta vs benchmark
    correlation: float | None = None        # correlation vs benchmark


@dataclass
class TrackingMetrics:
    tracking_difference: float | None = None   # annualised (ETF - benchmark) return
    tracking_error: float | None = None        # annualised std dev of daily diff returns
    information_ratio: float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

TRADING_DAYS = 252


def _pct_change_period(prices: pd.Series, days: int) -> float | None:
    """Return total return over the last `days` trading days, or None."""
    if len(prices) < days + 1:
        return None
    p_end = prices.iloc[-1]
    p_start = prices.iloc[-days - 1]
    if p_start == 0:
        return None
    return (p_end / p_start) - 1.0


def _annualise(total_return: float, years: float) -> float:
    """Convert a total return to an annualised return."""
    return (1 + total_return) ** (1 / years) - 1


def _daily_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


# ── Public functions ──────────────────────────────────────────────────────────

def compute_performance(prices: pd.Series) -> PerformanceMetrics:
    """Compute standard period returns from a daily price series."""
    if prices is None or len(prices) < 2:
        return PerformanceMetrics()

    m = PerformanceMetrics()
    m.d1 = _pct_change_period(prices, 1)
    m.w1 = _pct_change_period(prices, 5)
    m.m1 = _pct_change_period(prices, 21)
    m.m3 = _pct_change_period(prices, 63)
    m.m6 = _pct_change_period(prices, 126)

    # YTD: from last Dec 31
    try:
        last_date = prices.index[-1]
        ytd_start = pd.Timestamp(last_date.year - 1, 12, 31)
        ytd_prices = prices[prices.index >= ytd_start]
        if len(ytd_prices) >= 2:
            m.ytd = (ytd_prices.iloc[-1] / ytd_prices.iloc[0]) - 1
    except Exception:
        pass

    m.y1 = _pct_change_period(prices, TRADING_DAYS)

    # 3Y annualised
    if len(prices) >= 3 * TRADING_DAYS:
        raw = _pct_change_period(prices, 3 * TRADING_DAYS)
        if raw is not None:
            m.y3 = _annualise(raw, 3)

    # 5Y annualised
    if len(prices) >= 5 * TRADING_DAYS:
        raw = _pct_change_period(prices, 5 * TRADING_DAYS)
        if raw is not None:
            m.y5 = _annualise(raw, 5)

    # Since inception
    if len(prices) >= 2:
        m.inception = (prices.iloc[-1] / prices.iloc[0]) - 1

    return m


def compute_risk(
    prices: pd.Series,
    benchmark_prices: pd.Series | None = None,
    rf: float = 0.0,
) -> RiskMetrics:
    """Compute volatility, Sharpe, max drawdown, and beta."""
    if prices is None or len(prices) < 2:
        return RiskMetrics()

    r = RiskMetrics()
    rets = _daily_returns(prices)

    # Volatility
    if len(rets) >= TRADING_DAYS:
        r.volatility_1y = rets.iloc[-TRADING_DAYS:].std() * np.sqrt(TRADING_DAYS)
    if len(rets) >= 3 * TRADING_DAYS:
        r.volatility_3y = rets.iloc[-3 * TRADING_DAYS:].std() * np.sqrt(TRADING_DAYS)

    # Sharpe
    if r.volatility_1y and r.volatility_1y > 0:
        mean_1y = rets.iloc[-TRADING_DAYS:].mean() * TRADING_DAYS
        r.sharpe_1y = (mean_1y - rf) / r.volatility_1y
    if r.volatility_3y and r.volatility_3y > 0:
        mean_3y = rets.iloc[-3 * TRADING_DAYS:].mean() * TRADING_DAYS
        r.sharpe_3y = (mean_3y - rf) / r.volatility_3y

    # Maximum drawdown
    try:
        roll_max = prices.cummax()
        drawdown = (prices - roll_max) / roll_max
        min_idx = drawdown.idxmin()
        r.max_drawdown = float(drawdown[min_idx])
        # Peak: last time series was at its max before the trough
        peak_idx = prices[:min_idx].idxmax()
        r.max_drawdown_start = str(peak_idx.date()) if hasattr(peak_idx, "date") else str(peak_idx)
        r.max_drawdown_end = str(min_idx.date()) if hasattr(min_idx, "date") else str(min_idx)
    except Exception:
        pass

    # Beta & correlation vs benchmark
    if benchmark_prices is not None and len(benchmark_prices) >= 2:
        try:
            bench_rets = _daily_returns(benchmark_prices)
            # Align on common dates
            common = rets.index.intersection(bench_rets.index)
            if len(common) >= 20:
                e = rets.loc[common]
                b = bench_rets.loc[common]
                cov = np.cov(e, b)
                r.beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else None
                r.correlation = np.corrcoef(e, b)[0, 1]
        except Exception:
            pass

    return r


def compute_tracking(
    etf_prices: pd.Series,
    benchmark_prices: pd.Series,
) -> TrackingMetrics:
    """
    Compute tracking difference, tracking error, and information ratio.

    Tracking difference = annualised (ETF return - benchmark return) over 1Y.
    Tracking error      = annualised std dev of daily return differences.
    """
    t = TrackingMetrics()

    if etf_prices is None or benchmark_prices is None:
        return t
    if len(etf_prices) < 20 or len(benchmark_prices) < 20:
        return t

    try:
        etf_rets = _daily_returns(etf_prices)
        bm_rets = _daily_returns(benchmark_prices)
        common = etf_rets.index.intersection(bm_rets.index)
        if len(common) < 20:
            return t

        e = etf_rets.loc[common]
        b = bm_rets.loc[common]
        diff = e - b

        # Tracking error (annualised std of daily differences)
        t.tracking_error = float(diff.std() * np.sqrt(TRADING_DAYS))

        # Tracking difference (annualised mean)
        t.tracking_difference = float(diff.mean() * TRADING_DAYS)

        # Information ratio
        if t.tracking_error and t.tracking_error > 0:
            t.information_ratio = t.tracking_difference / t.tracking_error

    except Exception:
        pass

    return t


def rolling_drawdown(prices: pd.Series) -> pd.Series:
    """Return a Series of rolling drawdown values (always ≤ 0)."""
    roll_max = prices.cummax()
    return (prices - roll_max) / roll_max


def normalise_prices(prices: pd.Series, base: float = 100.0) -> pd.Series:
    """Rebased price series starting at `base`."""
    if prices.iloc[0] == 0:
        return prices
    return prices / prices.iloc[0] * base


def fmt_pct(value: float | None, decimals: int = 2) -> str:
    """Format a return as a percentage string with sign, e.g. '+3.45 %'."""
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.{decimals}f} %"


def colour_pct(value: float | None) -> str:
    """Return a CSS colour string: green if positive, red if negative."""
    if value is None:
        return "#6B7280"
    return "#00D9A6" if value >= 0 else "#EF4444"
