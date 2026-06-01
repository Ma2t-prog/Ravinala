"""
risk/models/advanced_metrics.py — Advanced performance & risk metrics.

Étape 14 — Modèles Risk Avancés
──────────────────────────────────
Metrics:
  rolling_sharpe              — Sharpe ratio over rolling windows
  rolling_sortino             — Sortino ratio over rolling windows
  rolling_calmar              — Calmar ratio over rolling 3Y windows
  probabilistic_sharpe_ratio  — PSR: probability that Sharpe > 0 (or benchmark)
  drawdown_duration           — Average / max drawdown duration in trading days
  conditional_drawdown_at_risk — CDaR: Expected drawdown beyond threshold
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

from app.risk.conventions import CONVENTIONS
from app.risk.engine import GovernedMetric, _conventions_snapshot, _governance_level

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ROLLING SHARPE
# ═══════════════════════════════════════════════════════════════════════════

def rolling_sharpe(
    returns: pd.Series | np.ndarray,
    window: int = 63,
    risk_free_rate: float | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Rolling Sharpe ratio computed over a sliding window.

    Returns the most recent value plus min/max/mean of the series
    as metadata (packed into method string for auditability).
    Use rolling_sharpe_series() to obtain the full time series.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate

    if n < window + 1:
        return GovernedMetric(
            metric_name="rolling_sharpe",
            value=None,
            unit="ratio (annualised)",
            governance_level="calculated",
            method=f"Rolling Sharpe (window={window}d)",
            n_observations=n,
            data_source=data_source,
            limitations=[f"Insufficient data for window={window} (need >{window} obs)"],
        )

    series = rolling_sharpe_series(returns, window=window, risk_free_rate=rf)
    current = float(series.iloc[-1])
    series_clean = series.dropna()

    return GovernedMetric(
        metric_name="rolling_sharpe",
        value=round(current, 6),
        unit="ratio (annualised)",
        governance_level=_governance_level(n, "sharpe_ratio"),
        method=(
            f"Rolling Sharpe window={window}d | "
            f"min={series_clean.min():.3f}, "
            f"max={series_clean.max():.3f}, "
            f"mean={series_clean.mean():.3f}"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            f"Point-in-time value for window={window}d",
            "Sharpe can be misleading for short windows",
        ],
    )


def rolling_sharpe_series(
    returns: pd.Series,
    window: int = 63,
    risk_free_rate: float | None = None,
) -> pd.Series:
    """Return full rolling Sharpe time series."""
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate
    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1
    excess = returns - daily_rf

    roll_mean = excess.rolling(window).mean() * CONVENTIONS.trading_days_per_year
    roll_std = excess.rolling(window).std() * CONVENTIONS.ann_factor_vol

    return (roll_mean / roll_std).replace([np.inf, -np.inf], np.nan)


# ═══════════════════════════════════════════════════════════════════════════
# ROLLING SORTINO
# ═══════════════════════════════════════════════════════════════════════════

def rolling_sortino(
    returns: pd.Series | np.ndarray,
    window: int = 63,
    risk_free_rate: float | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """Rolling Sortino ratio (current value + series stats)."""
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate

    if n < window + 1:
        return GovernedMetric(
            metric_name="rolling_sortino",
            value=None,
            unit="ratio (annualised)",
            governance_level="calculated",
            method=f"Rolling Sortino (window={window}d)",
            n_observations=n,
            data_source=data_source,
            limitations=[f"Insufficient data for window={window}"],
        )

    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1

    def _sortino(w: pd.Series) -> float:
        exc = w - daily_rf
        ann_exc = exc.mean() * CONVENTIONS.trading_days_per_year
        down = exc[exc < 0]
        if len(down) < 2:
            return np.nan
        ann_down = down.std() * CONVENTIONS.ann_factor_vol
        return ann_exc / ann_down if ann_down > 0 else np.nan

    series = returns.rolling(window).apply(_sortino, raw=False)
    current = float(series.iloc[-1])
    series_clean = series.dropna()

    return GovernedMetric(
        metric_name="rolling_sortino",
        value=round(current, 6),
        unit="ratio (annualised)",
        governance_level=_governance_level(n, "sortino_ratio"),
        method=(
            f"Rolling Sortino window={window}d | "
            f"min={series_clean.min():.3f}, max={series_clean.max():.3f}"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "Downside deviation uses only returns below Rf",
            f"Window={window}d — short windows produce noisy estimates",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# ROLLING CALMAR (3Y WINDOW)
# ═══════════════════════════════════════════════════════════════════════════

def rolling_calmar(
    returns: pd.Series | np.ndarray,
    window: int = 756,  # 3Y in trading days
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Rolling Calmar ratio over a 3-year (756 trading-day) window.

    Calmar = annualised_return / |MDD|
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < window:
        return GovernedMetric(
            metric_name="rolling_calmar",
            value=None,
            unit="ratio",
            governance_level="calculated",
            method=f"Rolling Calmar (window={window}d)",
            n_observations=n,
            data_source=data_source,
            limitations=[f"Insufficient data for {window}d window (need ≥{window} obs)"],
        )

    w = returns.iloc[-window:]
    total_ret = float((1 + w).prod() - 1)
    ann_factor = CONVENTIONS.trading_days_per_year / window
    ann_ret = (1 + total_ret) ** ann_factor - 1

    equity = (1 + w).cumprod()
    mdd = float(((equity - equity.cummax()) / equity.cummax()).min())

    calmar = ann_ret / abs(mdd) if mdd != 0 else 0.0

    return GovernedMetric(
        metric_name="rolling_calmar",
        value=round(calmar, 6),
        unit="ratio",
        governance_level=_governance_level(n, "calmar_ratio"),
        method=f"Rolling Calmar {window}d window: r_ann={ann_ret:.4f}, MDD={mdd:.4f}",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            f"Uses last {window} trading days ({window // CONVENTIONS.trading_days_per_year:.1f}Y)",
            "Sensitive to the start/end period chosen",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# PROBABILISTIC SHARPE RATIO (PSR)
# ═══════════════════════════════════════════════════════════════════════════

def probabilistic_sharpe_ratio(
    returns: pd.Series | np.ndarray,
    benchmark_sharpe: float = 0.0,
    risk_free_rate: float | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Probabilistic Sharpe Ratio (Bailey & López de Prado, 2012).

    PSR(SR*) = Φ( (SR - SR*) · √(T-1) / √(1 - S·SR + (K-1)/4·SR²) )

    Answers: "What is the probability that the true Sharpe > benchmark SR*?"
    Adjusts for estimation error, skewness (S), and kurtosis (K).
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate

    if n < 30:
        return GovernedMetric(
            metric_name="probabilistic_sharpe_ratio",
            value=None,
            unit="probability [0,1]",
            governance_level="calculated",
            method="PSR (Bailey-Lopez de Prado)",
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 30 observations)"],
        )

    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1
    excess = returns - daily_rf
    sr = float(excess.mean() / excess.std() * CONVENTIONS.ann_factor_vol)

    S = float(stats.skew(returns))
    K = float(stats.kurtosis(returns))  # excess kurtosis

    # PSR denominator
    denom_sq = 1 - S * sr / CONVENTIONS.ann_factor_vol + (K - 1) / 4 * (sr / CONVENTIONS.ann_factor_vol) ** 2
    if denom_sq <= 0:
        denom_sq = 1e-8  # numerical guard

    z = (sr - benchmark_sharpe) * np.sqrt(n - 1) / (np.sqrt(denom_sq) * CONVENTIONS.ann_factor_vol)
    psr = float(stats.norm.cdf(z))

    return GovernedMetric(
        metric_name="probabilistic_sharpe_ratio",
        value=round(psr, 6),
        unit="probability [0,1]",
        governance_level=_governance_level(n, "sharpe_ratio"),
        method=(
            f"PSR(SR*={benchmark_sharpe:.2f}): SR={sr:.4f}, "
            f"S={S:.4f}, K={K:.4f} → P(true SR > SR*) = {psr:.4f}"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            f"Benchmark SR* = {benchmark_sharpe:.2f}",
            "Based on IID assumption — autocorrelated returns inflate PSR",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# DRAWDOWN DURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DrawdownDurationResult:
    max_duration_days: int
    avg_duration_days: float
    current_duration_days: int
    n_drawdown_periods: int


def drawdown_duration(
    returns: pd.Series | np.ndarray,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Drawdown duration analysis.

    Computes max / avg / current drawdown duration in trading days.
    A drawdown period starts when equity falls below the previous peak
    and ends when it recovers to that peak.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="drawdown_duration",
            value=None,
            unit="trading days",
            governance_level="calculated",
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data"],
        )

    equity = (1 + returns).cumprod()
    cummax = equity.cummax()
    in_dd = equity < cummax

    durations: list[int] = []
    current_len = 0
    for is_dd in in_dd:
        if is_dd:
            current_len += 1
        else:
            if current_len > 0:
                durations.append(current_len)
            current_len = 0

    # If still in drawdown at end
    if current_len > 0:
        current_dd = current_len
    else:
        current_dd = 0

    if not durations and current_dd == 0:
        # No drawdown observed
        return GovernedMetric(
            metric_name="drawdown_duration",
            value=0,
            unit="trading days (max)",
            governance_level=_governance_level(n, "max_drawdown"),
            method="No drawdown periods detected",
            n_observations=n,
            data_source=data_source,
        )

    all_durs = durations + ([current_dd] if current_dd > 0 else [])
    max_dur = int(max(all_durs))
    avg_dur = float(np.mean(all_durs))

    return GovernedMetric(
        metric_name="drawdown_duration",
        value=max_dur,
        unit="trading days (max duration)",
        governance_level=_governance_level(n, "max_drawdown"),
        method=(
            f"Max={max_dur}d, Avg={avg_dur:.1f}d, "
            f"Current={current_dd}d, Periods={len(all_durs)}"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "Duration counts trading days (not calendar days)",
            "Current drawdown included if portfolio has not yet recovered",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# CONDITIONAL DRAWDOWN AT RISK (CDaR)
# ═══════════════════════════════════════════════════════════════════════════

def conditional_drawdown_at_risk(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Conditional Drawdown at Risk (CDaR).

    CDaR(α) = E[drawdown | drawdown > DaR(α)]

    where DaR(α) is the α-quantile of the drawdown distribution.
    Analogous to CVaR but for drawdowns rather than single-period losses.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < 30:
        return GovernedMetric(
            metric_name="conditional_drawdown_at_risk",
            value=None,
            unit="decimal (positive = drawdown magnitude)",
            governance_level="calculated",
            method=f"CDaR(α={confidence})",
            confidence=confidence,
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 30 observations)"],
        )

    equity = (1 + returns).cumprod()
    cummax = equity.cummax()
    drawdowns = ((equity - cummax) / cummax).abs()  # positive = magnitude

    alpha = 1 - confidence
    dar = float(np.percentile(drawdowns, confidence * 100))
    tail = drawdowns[drawdowns >= dar]
    cdar = float(tail.mean()) if len(tail) > 0 else float(dar)

    return GovernedMetric(
        metric_name="conditional_drawdown_at_risk",
        value=round(cdar, 8),
        unit="decimal (positive = drawdown magnitude)",
        governance_level=_governance_level(n, "max_drawdown"),
        method=f"CDaR(α={confidence}): DaR={dar:.4f}, E[DD|DD≥DaR]={cdar:.4f}",
        confidence=confidence,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "CDaR uses path-dependent drawdown (not single-period returns)",
            "High CDaR may indicate a single prolonged drawdown episode",
        ],
    )
