"""
risk/models/volatility_garch.py — Volatility modelling: EWMA, GARCH(1,1), E-GARCH.

Étape 14 — Modèles Risk Avancés
──────────────────────────────────
Methods:
  ewma_volatility   — Exponentially Weighted Moving Average (RiskMetrics λ=0.94)
  garch_volatility  — GARCH(1,1) conditional volatility via arch library
  egarch_volatility — E-GARCH(1,1) with leverage effect

All functions return GovernedMetric instances.
The `arch` library is required for GARCH/E-GARCH (pip install arch).
EWMA has no additional dependencies.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.risk.conventions import CONVENTIONS
from app.risk.engine import GovernedMetric, _conventions_snapshot, _governance_level

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# EWMA VOLATILITY
# ═══════════════════════════════════════════════════════════════════════════

_RISKMETRICS_LAMBDA = 0.94  # J.P. Morgan RiskMetrics standard


def ewma_volatility(
    returns: pd.Series | np.ndarray,
    lam: float = _RISKMETRICS_LAMBDA,
    annualise: bool = True,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Exponentially Weighted Moving Average volatility.

    σ²_t = λ·σ²_(t-1) + (1-λ)·r²_(t-1)

    λ = 0.94 is the RiskMetrics standard for daily returns.
    Returns σ_t at the last observation point.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="ewma_volatility",
            value=None,
            unit="annualised decimal" if annualise else "daily decimal",
            governance_level="calculated",
            method=f"EWMA(λ={lam})",
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 10 observations)"],
        )

    # Initialise with sample variance of first 10 obs
    variance = float(returns.iloc[:10].var())
    r = returns.to_numpy()

    for ret in r[10:]:
        variance = lam * variance + (1 - lam) * ret**2

    vol_daily = float(np.sqrt(variance))
    vol = vol_daily * CONVENTIONS.ann_factor_vol if annualise else vol_daily

    return GovernedMetric(
        metric_name="ewma_volatility",
        value=round(vol, 8),
        unit="annualised decimal" if annualise else "daily decimal",
        governance_level=_governance_level(n, "volatility"),
        method=(
            f"EWMA(λ={lam}): σ²_t = λ·σ²_(t-1) + (1-λ)·r²_(t-1)  "
            f"[RiskMetrics standard λ={_RISKMETRICS_LAMBDA}]"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            f"λ={lam} — higher λ = more weight on recent observations",
            "Point-in-time estimate (last observation)",
            "No mean-reversion (unlike GARCH)",
        ],
    )


def ewma_volatility_series(
    returns: pd.Series,
    lam: float = _RISKMETRICS_LAMBDA,
    annualise: bool = True,
) -> pd.Series:
    """
    Return the full EWMA volatility time series (one value per return).
    Useful for rolling plots and regime detection.
    """
    returns = returns.dropna().astype(float)
    r = returns.to_numpy()
    variance = float(returns.iloc[:10].var()) if len(returns) >= 10 else float(returns.var())

    vols = []
    for ret in r:
        variance = lam * variance + (1 - lam) * ret**2
        v = np.sqrt(variance)
        vols.append(v * CONVENTIONS.ann_factor_vol if annualise else v)

    return pd.Series(vols, index=returns.index)


# ═══════════════════════════════════════════════════════════════════════════
# GARCH(1,1) VOLATILITY
# ═══════════════════════════════════════════════════════════════════════════

def garch_volatility(
    returns: pd.Series | np.ndarray,
    annualise: bool = True,
    forecast_horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    GARCH(1,1) conditional volatility forecast.

    σ²_t = ω + α·ε²_(t-1) + β·σ²_(t-1)

    Fitted via MLE using the `arch` library.
    Returns the `forecast_horizon`-step-ahead conditional volatility.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < 100:
        return GovernedMetric(
            metric_name="garch_volatility",
            value=None,
            unit="annualised decimal" if annualise else "daily decimal",
            governance_level="calculated",
            method="GARCH(1,1)",
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 100 observations) for GARCH fitting"],
        )

    try:
        from arch import arch_model  # type: ignore

        # Returns in % for numerical stability (arch convention)
        r_pct = returns * 100
        model = arch_model(r_pct, vol="GARCH", p=1, q=1, mean="Constant", dist="normal")
        result = model.fit(disp="off", show_warning=False)

        forecast = result.forecast(horizon=forecast_horizon, reindex=False)
        var_forecast = float(forecast.variance.iloc[-1].values[-1])
        vol_daily = float(np.sqrt(var_forecast)) / 100  # back to decimal

        omega = float(result.params.get("omega", float("nan")))
        alpha = float(result.params.get("alpha[1]", float("nan")))
        beta = float(result.params.get("beta[1]", float("nan")))

        vol = vol_daily * CONVENTIONS.ann_factor_vol if annualise else vol_daily

        return GovernedMetric(
            metric_name="garch_volatility",
            value=round(vol, 8),
            unit="annualised decimal" if annualise else "daily decimal",
            governance_level=_governance_level(n, "volatility"),
            method=(
                f"GARCH(1,1) MLE: ω={omega:.6f}, α={alpha:.4f}, β={beta:.4f}  "
                f"[persistence={alpha+beta:.4f}]"
            ),
            n_observations=n,
            data_source=data_source,
            conventions_snapshot=_conventions_snapshot(),
            limitations=[
                f"{forecast_horizon}-step-ahead conditional variance forecast",
                "Assumes normal innovations",
                f"Persistence α+β={alpha+beta:.4f} — close to 1 = high volatility clustering",
            ],
        )

    except ImportError:
        return GovernedMetric(
            metric_name="garch_volatility",
            value=None,
            governance_level="calculated",
            method="GARCH(1,1)",
            n_observations=n,
            data_source=data_source,
            limitations=["arch library not installed — pip install arch"],
        )
    except Exception as exc:
        logger.warning("GARCH fitting failed: %s", exc)
        return GovernedMetric(
            metric_name="garch_volatility",
            value=None,
            governance_level="calculated",
            method="GARCH(1,1) — fitting failed",
            n_observations=n,
            data_source=data_source,
            limitations=[f"GARCH fit error: {exc}"],
        )


# ═══════════════════════════════════════════════════════════════════════════
# E-GARCH(1,1) — LEVERAGE EFFECT
# ═══════════════════════════════════════════════════════════════════════════

def egarch_volatility(
    returns: pd.Series | np.ndarray,
    annualise: bool = True,
    forecast_horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Exponential GARCH(1,1) — captures the leverage effect.

    ln(σ²_t) = ω + α·(|z_(t-1)| - E|z|) + γ·z_(t-1) + β·ln(σ²_(t-1))

    Negative returns (z < 0) have larger impact on volatility than positive
    returns of equal magnitude (leverage effect, captured by γ < 0).
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    if n < 100:
        return GovernedMetric(
            metric_name="egarch_volatility",
            value=None,
            unit="annualised decimal" if annualise else "daily decimal",
            governance_level="calculated",
            method="EGARCH(1,1)",
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 100 observations) for E-GARCH fitting"],
        )

    try:
        from arch import arch_model  # type: ignore

        r_pct = returns * 100
        model = arch_model(r_pct, vol="EGARCH", p=1, q=1, mean="Constant", dist="normal")
        result = model.fit(disp="off", show_warning=False)

        forecast = result.forecast(horizon=forecast_horizon, reindex=False)
        var_forecast = float(forecast.variance.iloc[-1].values[-1])
        vol_daily = float(np.sqrt(var_forecast)) / 100

        gamma = result.params.get("gamma[1]", float("nan"))
        leverage_effect = "detected" if float(gamma) < 0 else "not detected"

        vol = vol_daily * CONVENTIONS.ann_factor_vol if annualise else vol_daily

        return GovernedMetric(
            metric_name="egarch_volatility",
            value=round(vol, 8),
            unit="annualised decimal" if annualise else "daily decimal",
            governance_level=_governance_level(n, "volatility"),
            method=(
                f"E-GARCH(1,1) MLE: γ={float(gamma):.4f} "
                f"[leverage effect {leverage_effect}]"
            ),
            n_observations=n,
            data_source=data_source,
            conventions_snapshot=_conventions_snapshot(),
            limitations=[
                f"Leverage {leverage_effect}: γ={'<0 (neg returns → more vol)' if float(gamma) < 0 else '≥0'}",
                f"{forecast_horizon}-step-ahead conditional variance forecast",
            ],
        )

    except ImportError:
        return GovernedMetric(
            metric_name="egarch_volatility",
            value=None,
            governance_level="calculated",
            method="EGARCH(1,1)",
            n_observations=n,
            data_source=data_source,
            limitations=["arch library not installed — pip install arch"],
        )
    except Exception as exc:
        logger.warning("E-GARCH fitting failed: %s", exc)
        return GovernedMetric(
            metric_name="egarch_volatility",
            value=None,
            governance_level="calculated",
            method="EGARCH(1,1) — fitting failed",
            n_observations=n,
            data_source=data_source,
            limitations=[f"E-GARCH fit error: {exc}"],
        )
