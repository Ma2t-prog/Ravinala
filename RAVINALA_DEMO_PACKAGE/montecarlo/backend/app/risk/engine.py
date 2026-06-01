"""
risk/engine.py — Governed risk calculation engine.

Étape 10 — Risk Engine Governance
──────────────────────────────────
All metrics use centralised conventions from conventions.py.
Every output carries:
  - governance_level : "calculated" | "governed" | "exploitable"
  - method           : which formula was used
  - data_source      : provenance of input data
  - conventions_used : snapshot of key parameters
  - limitations      : list of known caveats

This replaces the scattered risk calculations with a single,
auditable, convention-consistent engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from app.risk.conventions import CONVENTIONS, GOVERNANCE_LEVELS, METRIC_SPECS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# GOVERNED METRIC RESULT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GovernedMetric:
    """
    Every risk metric output is wrapped in this envelope.
    Provides auditability: what was computed, how, with what assumptions.
    """
    metric_name: str
    value: float | None
    unit: str = ""
    governance_level: str = "calculated"
    method: str = ""
    confidence: float | None = None
    horizon_days: int | None = None
    n_observations: int = 0
    data_source: str = ""
    conventions_snapshot: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "governance_level": self.governance_level,
            "method": self.method,
            "confidence": self.confidence,
            "horizon_days": self.horizon_days,
            "n_observations": self.n_observations,
            "data_source": self.data_source,
            "conventions_snapshot": self.conventions_snapshot,
            "limitations": self.limitations,
            "computed_at": self.computed_at,
        }


def _conventions_snapshot() -> dict[str, Any]:
    """Snapshot of key conventions at computation time."""
    return {
        "trading_days_per_year": CONVENTIONS.trading_days_per_year,
        "risk_free_rate": CONVENTIONS.risk_free_rate,
        "risk_free_rate_source": CONVENTIONS.risk_free_rate_source,
        "return_type": CONVENTIONS.return_type,
        "var_sign_convention": CONVENTIONS.var_sign_convention,
        "ann_factor_vol": round(CONVENTIONS.ann_factor_vol, 6),
    }


def _governance_level(n_obs: int, metric_key: str) -> str:
    """Determine governance level based on data sufficiency."""
    spec = METRIC_SPECS.get(metric_key, {})
    min_obs = spec.get("min_observations", CONVENTIONS.var_min_observations)
    if n_obs >= CONVENTIONS.min_history_for_governed and n_obs >= min_obs:
        return "governed"
    if n_obs >= min_obs:
        return "calculated"
    return "calculated"


# ═══════════════════════════════════════════════════════════════════════════
# VaR
# ═══════════════════════════════════════════════════════════════════════════

def var_historical(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Historical simulation VaR.

    For horizon > 1: overlapping returns (no √T assumption).
    Sign: positive = loss magnitude (CONVENTIONS.var_sign_convention).
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="var_historical", value=None, unit="decimal",
            governance_level="calculated", method="historical",
            confidence=confidence, horizon_days=horizon, n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 10 observations)"],
        )

    if horizon > 1:
        # Overlapping returns
        cum = (1 + returns).rolling(window=horizon).apply(lambda x: x.prod() - 1, raw=True)
        cum = cum.dropna()
        n = len(cum)
    else:
        cum = returns

    var_value = float(-np.percentile(cum, (1 - confidence) * 100))

    return GovernedMetric(
        metric_name="var_historical",
        value=round(var_value, 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "var_historical"),
        method="Empirical quantile of historical returns",
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["var_historical"]["limitations"],
    )


def var_parametric(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Parametric VaR (normal assumption).

    Horizon scaling: √T for volatility, T for mean.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="var_parametric", value=None, unit="decimal",
            governance_level="calculated", method="parametric_normal",
            confidence=confidence, horizon_days=horizon, n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data"],
        )

    mu = float(returns.mean())
    sigma = float(returns.std())
    z = stats.norm.ppf(1 - confidence)

    # √T scaling
    var_value = -(mu * horizon + sigma * np.sqrt(horizon) * z)

    return GovernedMetric(
        metric_name="var_parametric",
        value=round(var_value, 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "var_parametric"),
        method="Normal distribution: VaR = -(μT + σ√T × Z)",
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["var_parametric"]["limitations"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# CVaR (Expected Shortfall)
# ═══════════════════════════════════════════════════════════════════════════

def cvar(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Conditional VaR (Expected Shortfall) — historical method.

    Average of returns beyond VaR threshold.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="cvar", value=None, unit="decimal",
            governance_level="calculated", method="historical_cvar",
            confidence=confidence, horizon_days=horizon, n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data"],
        )

    if horizon > 1:
        cum = (1 + returns).rolling(window=horizon).apply(lambda x: x.prod() - 1, raw=True)
        cum = cum.dropna()
        n = len(cum)
    else:
        cum = returns

    var_threshold = np.percentile(cum, (1 - confidence) * 100)
    tail = cum[cum <= var_threshold]
    cvar_value = float(-tail.mean()) if len(tail) > 0 else None

    return GovernedMetric(
        metric_name="cvar",
        value=round(cvar_value, 8) if cvar_value is not None else None,
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "cvar"),
        method="Average of returns beyond VaR threshold",
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["cvar"]["limitations"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# VOLATILITY
# ═══════════════════════════════════════════════════════════════════════════

def annualised_volatility(
    returns: pd.Series | np.ndarray,
    window: int | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Annualised volatility = std(returns) × √252.

    If window is given, uses the last `window` observations.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()

    if window:
        returns = returns.iloc[-window:]

    n = len(returns)
    if n < 5:
        return GovernedMetric(
            metric_name="volatility", value=None, unit="annualised decimal",
            governance_level="calculated", method="annualised_std",
            n_observations=n, data_source=data_source,
            limitations=["Insufficient data"],
        )

    vol = float(returns.std() * CONVENTIONS.ann_factor_vol)

    return GovernedMetric(
        metric_name="volatility",
        value=round(vol, 8),
        unit="annualised decimal",
        governance_level=_governance_level(n, "volatility"),
        method=f"std(returns) × √{CONVENTIONS.trading_days_per_year}",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["volatility"]["limitations"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# MAX DRAWDOWN
# ═══════════════════════════════════════════════════════════════════════════

def max_drawdown(
    returns: pd.Series | np.ndarray,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """Max peak-to-trough decline."""
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 2:
        return GovernedMetric(
            metric_name="max_drawdown", value=None, unit="decimal",
            governance_level="calculated",
            n_observations=n, data_source=data_source,
        )

    equity = (1 + returns).cumprod()
    cummax = equity.cummax()
    dd = (equity - cummax) / cummax
    mdd = float(dd.min())

    return GovernedMetric(
        metric_name="max_drawdown",
        value=round(mdd, 8),
        unit="decimal (negative = drawdown)",
        governance_level=_governance_level(n, "max_drawdown"),
        method="Max peak-to-trough decline in cumulative return",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["max_drawdown"]["limitations"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# PERFORMANCE RATIOS
# ═══════════════════════════════════════════════════════════════════════════

def sharpe_ratio(
    returns: pd.Series | np.ndarray,
    risk_free_rate: float | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """Annualised Sharpe ratio with centralised Rf."""
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate

    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 21:
        return GovernedMetric(
            metric_name="sharpe_ratio", value=None, unit="ratio",
            governance_level="calculated",
            n_observations=n, data_source=data_source,
            limitations=["Insufficient data (< 21 observations)"],
        )

    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1
    excess = returns - daily_rf
    ann_excess_mean = float(excess.mean() * CONVENTIONS.trading_days_per_year)
    ann_vol = float(excess.std() * CONVENTIONS.ann_factor_vol)

    sr = ann_excess_mean / ann_vol if ann_vol > 0 else 0.0

    return GovernedMetric(
        metric_name="sharpe_ratio",
        value=round(sr, 6),
        unit="ratio (annualised)",
        governance_level=_governance_level(n, "sharpe_ratio"),
        method=f"(r_ann - Rf) / σ_ann  |  Rf = {rf}",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["sharpe_ratio"]["limitations"],
    )


def sortino_ratio(
    returns: pd.Series | np.ndarray,
    risk_free_rate: float | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """Annualised Sortino ratio with centralised Rf."""
    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate

    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 21:
        return GovernedMetric(
            metric_name="sortino_ratio", value=None, unit="ratio",
            governance_level="calculated",
            n_observations=n, data_source=data_source,
        )

    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1
    excess = returns - daily_rf
    ann_excess_mean = float(excess.mean() * CONVENTIONS.trading_days_per_year)
    downside = returns[returns < daily_rf] - daily_rf
    downside_std = float(downside.std() * CONVENTIONS.ann_factor_vol) if len(downside) > 0 else 0.0

    sortino = ann_excess_mean / downside_std if downside_std > 0 else 0.0

    return GovernedMetric(
        metric_name="sortino_ratio",
        value=round(sortino, 6),
        unit="ratio (annualised)",
        governance_level=_governance_level(n, "sortino_ratio"),
        method=f"(r_ann - Rf) / σ_downside  |  Rf = {rf}",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["sortino_ratio"]["limitations"],
    )


def calmar_ratio(
    returns: pd.Series | np.ndarray,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """Calmar ratio = annualised return / |max drawdown|."""
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 63:
        return GovernedMetric(
            metric_name="calmar_ratio", value=None, unit="ratio",
            governance_level="calculated",
            n_observations=n, data_source=data_source,
        )

    total_ret = float((1 + returns).prod() - 1)
    ann_factor = CONVENTIONS.trading_days_per_year / max(n, 1)
    ann_ret = (1 + total_ret) ** ann_factor - 1

    equity = (1 + returns).cumprod()
    mdd = float(((equity - equity.cummax()) / equity.cummax()).min())

    calmar = ann_ret / abs(mdd) if mdd != 0 else 0.0

    return GovernedMetric(
        metric_name="calmar_ratio",
        value=round(calmar, 6),
        unit="ratio",
        governance_level=_governance_level(n, "calmar_ratio"),
        method="r_ann / |MDD|",
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=METRIC_SPECS["calmar_ratio"]["limitations"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# STRESS TEST (SIMPLE)
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_SHOCKS = [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20]


def stress_test_simple(
    portfolio_value: float,
    shocks: list[float] | None = None,
    data_source: str = "portfolio",
) -> list[GovernedMetric]:
    """
    Simple stress test: apply fixed % shocks to portfolio value.

    Returns one GovernedMetric per shock level.
    """
    shocks = shocks or DEFAULT_SHOCKS
    results = []
    for shock in shocks:
        pnl = portfolio_value * shock
        results.append(GovernedMetric(
            metric_name=f"stress_pnl_{shock:+.0%}",
            value=round(pnl, 2),
            unit="currency",
            governance_level="calculated",
            method=f"portfolio_value × {shock:+.2%}",
            n_observations=0,
            data_source=data_source,
            conventions_snapshot=_conventions_snapshot(),
            limitations=METRIC_SPECS["stress_test"]["limitations"],
        ))
    return results


# ═══════════════════════════════════════════════════════════════════════════
# FULL RISK REPORT
# ═══════════════════════════════════════════════════════════════════════════

def compute_full_risk_report(
    returns: pd.Series | np.ndarray,
    portfolio_value: float = 100_000.0,
    data_source: str = "yfinance",
) -> dict[str, Any]:
    """
    Compute all governed metrics at once for a single asset/portfolio.

    Returns a dict of { metric_name: GovernedMetric.to_dict() }.
    """
    results: dict[str, Any] = {}

    # VaR / CVaR at standard confidence levels and horizons
    for conf in CONVENTIONS.var_confidence_levels:
        for h in (1, 5, 21):
            key_h = f"var_hist_{conf}_{h}d"
            results[key_h] = var_historical(returns, conf, h, data_source).to_dict()

            key_p = f"var_param_{conf}_{h}d"
            results[key_p] = var_parametric(returns, conf, h, data_source).to_dict()

            key_c = f"cvar_{conf}_{h}d"
            results[key_c] = cvar(returns, conf, h, data_source).to_dict()

    # Volatility
    results["volatility"] = annualised_volatility(returns, data_source=data_source).to_dict()
    results["volatility_21d"] = annualised_volatility(returns, window=21, data_source=data_source).to_dict()
    results["volatility_63d"] = annualised_volatility(returns, window=63, data_source=data_source).to_dict()

    # Drawdown
    results["max_drawdown"] = max_drawdown(returns, data_source).to_dict()

    # Performance ratios
    results["sharpe_ratio"] = sharpe_ratio(returns, data_source=data_source).to_dict()
    results["sortino_ratio"] = sortino_ratio(returns, data_source=data_source).to_dict()
    results["calmar_ratio"] = calmar_ratio(returns, data_source=data_source).to_dict()

    # Stress tests (simple)
    stress = stress_test_simple(portfolio_value, data_source=data_source)
    results["stress_tests"] = [s.to_dict() for s in stress]

    # ── Étape 14: Advanced models (graceful degradation if not enough data) ──
    try:
        from app.risk.models.var_cornish_fisher import (
            var_cornish_fisher, var_monte_carlo, var_student_t, cvar_parametric,
        )
        from app.risk.models.volatility_garch import ewma_volatility, garch_volatility
        from app.risk.models.advanced_metrics import (
            rolling_sharpe, probabilistic_sharpe_ratio,
            drawdown_duration, conditional_drawdown_at_risk,
        )
        from app.risk.stress_testing.conditional_stress import conditional_stress_as_metrics

        for conf in CONVENTIONS.var_confidence_levels:
            results[f"var_cf_{conf}_1d"] = var_cornish_fisher(returns, conf, 1, data_source).to_dict()
            results[f"var_mc_{conf}_1d"] = var_monte_carlo(returns, conf, 1, data_source=data_source).to_dict()
            results[f"var_t_{conf}_1d"] = var_student_t(returns, conf, 1, data_source).to_dict()
            results[f"cvar_param_{conf}_1d"] = cvar_parametric(returns, conf, 1, data_source).to_dict()

        results["ewma_volatility"] = ewma_volatility(returns, data_source=data_source).to_dict()
        results["garch_volatility"] = garch_volatility(returns, data_source=data_source).to_dict()

        results["rolling_sharpe_63d"] = rolling_sharpe(returns, window=63, data_source=data_source).to_dict()
        results["probabilistic_sharpe"] = probabilistic_sharpe_ratio(returns, data_source=data_source).to_dict()
        results["drawdown_duration"] = drawdown_duration(returns, data_source=data_source).to_dict()
        results["conditional_drawdown_at_risk"] = conditional_drawdown_at_risk(returns, data_source=data_source).to_dict()

        cond_stress = conditional_stress_as_metrics(portfolio_value, returns=returns, data_source=data_source)
        results["conditional_stress_tests"] = [m.to_dict() for m in cond_stress]

    except Exception as _adv_exc:
        logger.warning("Advanced risk models skipped: %s", _adv_exc)
        results["advanced_models_status"] = {"error": str(_adv_exc)}

    # Governance summary
    gov_counts = {"calculated": 0, "governed": 0, "exploitable": 0}
    for k, v in results.items():
        if isinstance(v, dict) and "governance_level" in v:
            gov_counts[v["governance_level"]] = gov_counts.get(v["governance_level"], 0) + 1
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "governance_level" in item:
                    gov_counts[item["governance_level"]] = gov_counts.get(item["governance_level"], 0) + 1

    results["_governance_summary"] = gov_counts
    results["_conventions"] = _conventions_snapshot()

    return results
