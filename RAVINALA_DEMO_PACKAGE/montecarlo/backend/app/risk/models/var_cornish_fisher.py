"""
risk/models/var_cornish_fisher.py — Advanced VaR: Cornish-Fisher, Monte Carlo,
Student-t, and parametric CVaR.

Étape 14 — Modèles Risk Avancés
──────────────────────────────────
All functions return GovernedMetric instances (same envelope as Étape 10).

Methods:
  var_cornish_fisher  — CF expansion adjusts normal VaR for skewness/kurtosis
  var_monte_carlo     — GBM-based MC simulation (10,000 paths default)
  var_student_t       — Student-t VaR, better tail modelling
  cvar_parametric     — Parametric CVaR under normal assumption
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from app.risk.conventions import CONVENTIONS
from app.risk.engine import GovernedMetric, _conventions_snapshot, _governance_level

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# VaR CORNISH-FISHER
# ═══════════════════════════════════════════════════════════════════════════

def var_cornish_fisher(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Cornish-Fisher VaR.

    Adjusts the normal quantile (z) for the empirical skewness (S) and
    excess kurtosis (K) of the return distribution:

        z_CF = z + (z²-1)·S/6 + (z³-3z)·K/24 - (2z³-5z)·S²/36

    More accurate than parametric VaR for fat-tailed / skewed distributions.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 30:
        return GovernedMetric(
            metric_name="var_cornish_fisher",
            value=None,
            unit="decimal",
            governance_level="calculated",
            method="cornish_fisher",
            confidence=confidence,
            horizon_days=horizon,
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 30 observations)"],
        )

    mu = float(returns.mean())
    sigma = float(returns.std())
    S = float(stats.skew(returns))
    K = float(stats.kurtosis(returns))  # excess kurtosis

    alpha = 1 - confidence
    z = stats.norm.ppf(alpha)

    # Cornish-Fisher expansion
    z_cf = (
        z
        + (z**2 - 1) * S / 6
        + (z**3 - 3 * z) * K / 24
        - (2 * z**3 - 5 * z) * S**2 / 36
    )

    # √T horizon scaling
    var_value = -(mu * horizon + sigma * np.sqrt(horizon) * z_cf)

    return GovernedMetric(
        metric_name="var_cornish_fisher",
        value=round(float(var_value), 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "var_historical"),
        method=(
            f"Cornish-Fisher expansion: z_CF={z_cf:.4f}, "
            f"S={S:.4f}, K={K:.4f}"
        ),
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "CF expansion valid for mild non-normality; may be inaccurate for extreme skew",
            "Horizon scaling via √T (IID assumption)",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# VaR MONTE CARLO (GBM)
# ═══════════════════════════════════════════════════════════════════════════

def var_monte_carlo(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    n_simulations: int | None = None,
    seed: int | None = None,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Monte Carlo VaR via Geometric Brownian Motion.

    Calibrates GBM parameters (μ, σ) from historical returns and simulates
    `n_simulations` paths of length `horizon` days.  The VaR is the
    (1-confidence) percentile of the simulated P&L distribution.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    n_sim = n_simulations if n_simulations is not None else CONVENTIONS.mc_simulations
    rng_seed = seed if seed is not None else CONVENTIONS.mc_default_seed

    if n < 30:
        return GovernedMetric(
            metric_name="var_monte_carlo",
            value=None,
            unit="decimal",
            governance_level="calculated",
            method="monte_carlo_gbm",
            confidence=confidence,
            horizon_days=horizon,
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 30 observations)"],
        )

    mu_daily = float(returns.mean())
    sigma_daily = float(returns.std())

    rng = np.random.default_rng(rng_seed)
    # Simulate horizon-day log returns for n_sim paths
    log_returns = rng.normal(
        loc=mu_daily - 0.5 * sigma_daily**2,
        scale=sigma_daily,
        size=(n_sim, horizon),
    )
    # Total log return over horizon
    total_log_return = log_returns.sum(axis=1)
    # Simple return ≈ e^x - 1
    simple_returns = np.exp(total_log_return) - 1

    var_value = float(-np.percentile(simple_returns, (1 - confidence) * 100))

    return GovernedMetric(
        metric_name="var_monte_carlo",
        value=round(var_value, 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "var_historical"),
        method=(
            f"GBM MC: {n_sim:,} paths, horizon={horizon}d, "
            f"μ={mu_daily:.6f}, σ={sigma_daily:.6f}, seed={rng_seed}"
        ),
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "GBM assumes log-normal returns (no jumps)",
            "Constant μ and σ (no regime changes)",
            f"Seed={rng_seed} for reproducibility",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# VaR STUDENT-T
# ═══════════════════════════════════════════════════════════════════════════

def var_student_t(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Student-t VaR.

    Fits a Student-t distribution to returns via MLE (df, loc, scale),
    then reads the (1-confidence) quantile.  Better captures fat tails
    than the normal parametric VaR and does not require skew/kurtosis
    adjustments like Cornish-Fisher.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 30:
        return GovernedMetric(
            metric_name="var_student_t",
            value=None,
            unit="decimal",
            governance_level="calculated",
            method="student_t_mle",
            confidence=confidence,
            horizon_days=horizon,
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data (< 30 observations)"],
        )

    try:
        df_fit, loc_fit, scale_fit = stats.t.fit(returns, floc=0)
        alpha = 1 - confidence
        # Daily VaR quantile
        q = stats.t.ppf(alpha, df=df_fit, loc=loc_fit, scale=scale_fit)
        # √T scaling (approximate)
        var_value = -q * np.sqrt(horizon)
    except Exception as exc:
        logger.warning("Student-t fit failed: %s", exc)
        return GovernedMetric(
            metric_name="var_student_t",
            value=None,
            governance_level="calculated",
            method="student_t_mle",
            n_observations=n,
            data_source=data_source,
            limitations=[f"MLE fitting failed: {exc}"],
        )

    return GovernedMetric(
        metric_name="var_student_t",
        value=round(float(var_value), 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "var_historical"),
        method=(
            f"Student-t MLE: df={df_fit:.2f}, loc={loc_fit:.6f}, "
            f"scale={scale_fit:.6f}"
        ),
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "Student-t assumes symmetric fat tails",
            "Horizon scaling via √T (IID assumption)",
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# CVaR PARAMETRIC
# ═══════════════════════════════════════════════════════════════════════════

def cvar_parametric(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    horizon: int = 1,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Parametric CVaR under normal assumption.

    CVaR_normal = -(μT - σ√T · φ(z) / (1-α))

    where φ(z) is the standard normal PDF at the z-quantile and α is the
    confidence level.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    returns = returns.dropna()
    n = len(returns)

    if n < 10:
        return GovernedMetric(
            metric_name="cvar_parametric",
            value=None,
            unit="decimal",
            governance_level="calculated",
            method="parametric_normal",
            confidence=confidence,
            horizon_days=horizon,
            n_observations=n,
            data_source=data_source,
            limitations=["Insufficient data"],
        )

    mu = float(returns.mean())
    sigma = float(returns.std())
    alpha = 1 - confidence
    z = stats.norm.ppf(alpha)
    phi_z = stats.norm.pdf(z)

    # Parametric CVaR: E[L | L > VaR] under normality
    cvar_daily = -(mu + sigma * phi_z / alpha)
    cvar_value = cvar_daily * horizon  # scale linearly (mean component dominates)

    return GovernedMetric(
        metric_name="cvar_parametric",
        value=round(float(cvar_value), 8),
        unit="decimal (positive = loss magnitude)",
        governance_level=_governance_level(n, "cvar"),
        method=f"Normal CVaR: -(μT - σ√T·φ(z)/(1-α)), α={alpha}",
        confidence=confidence,
        horizon_days=horizon,
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "Assumes normal distribution — underestimates tail risk",
            "Use historical CVaR for fat-tailed assets",
        ],
    )
