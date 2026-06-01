"""
risk/conventions.py — Single source of truth for quant conventions.

Étape 10 — Risk Engine Governance
──────────────────────────────────
Centralised parameters so that every risk metric across the platform
uses the same assumptions.  Any deviation must be flagged explicitly.

Changes here propagate everywhere.  Document the *why* next to each value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from app.core.config import get_settings

_SETTINGS = get_settings()


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL QUANT CONVENTIONS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class QuantConventions:
    """
    Immutable registry of quant conventions.

    These are the platform-wide defaults.  Individual metric computations
    may override them *only* if the override is logged and justified.
    """

    # ── Temporal ───────────────────────────────────────────────────────
    trading_days_per_year: int = 252
    """NYSE trading calendar — 252 is the standard convention."""

    standard_horizons: tuple[int, ...] = (1, 5, 21, 63, 252)
    """Day / Week / Month / Quarter / Year in trading days."""

    horizon_labels: dict[int, str] = field(default_factory=lambda: {
        1: "1D", 5: "1W", 21: "1M", 63: "3M", 252: "1Y",
    })

    # ── Risk-free rate ────────────────────────────────────────────────
    risk_free_rate: float = 0.043
    """
    Annualised risk-free rate (decimal).
    Loaded from backend settings so every touched module uses the same value.
    """

    risk_free_rate_source: str = "US 10Y Treasury demo baseline"
    risk_free_rate_last_updated: str = "2026-03-23"

    # ── Return conventions ────────────────────────────────────────────
    return_type: str = "simple"
    """'simple' returns (P1/P0 - 1), NOT log returns.  All % displayed as decimals (0.01 = 1%)."""

    # ── Annualisation ─────────────────────────────────────────────────
    ann_factor_vol: float = 252 ** 0.5
    """σ_annual = σ_daily × √252  (IID assumption documented in limitations)."""

    ann_factor_return: float = 252.0
    """r_annual = r_daily × 252  (arithmetic approximation; geometric used where noted)."""

    # ── VaR / CVaR ────────────────────────────────────────────────────
    var_confidence_levels: tuple[float, ...] = (0.95, 0.99)
    """Standard confidence levels.  0.95 primary, 0.99 secondary."""

    var_sign_convention: str = "positive_loss"
    """VaR = 0.03 means '3 % loss possible'.  Positive = loss magnitude."""

    var_min_observations: int = 100
    """Minimum number of daily returns for VaR to be considered 'governed'."""

    # ── Rolling windows ───────────────────────────────────────────────
    rolling_windows: tuple[int, ...] = (21, 63, 126, 252)
    """Standard rolling windows (1M / 3M / 6M / 1Y)."""

    default_rolling_window: int = 252
    """Default for point-in-time metrics."""

    # ── Monte Carlo ───────────────────────────────────────────────────
    mc_simulations: int = 10_000
    """Default Monte Carlo path count.  Overridable per endpoint."""

    mc_default_seed: int = 42
    """Default seed for reproducibility."""

    # ── Data source policy ────────────────────────────────────────────
    data_source_policy: str = (
        "Price data: Yahoo Finance (auto-adjusted for splits/dividends). "
        "Bond yields: static demo. Macro indicators: static."
    )

    # ── Governance thresholds ─────────────────────────────────────────
    stale_data_threshold_days: int = 3
    """Metric tagged 'stale' if underlying data is older than this."""

    min_history_for_governed: int = 252
    """At least 1 year of data for a metric to be 'governed' (not merely 'calculated')."""

    # ── ML feature engineering ────────────────────────────────────────
    ml_vol_windows: tuple[int, ...] = (5, 21, 63)
    """Realised-volatility rolling windows used in build_features() (trading days)."""

    ml_return_windows: tuple[int, ...] = (1, 5, 21)
    """Return lookback windows used in build_features() (trading days)."""

    ml_rsi_period: int = 14
    """RSI smoothing period (Wilder, 1978)."""

    ml_macd_fast: int = 12
    """MACD fast EMA span (trading days)."""

    ml_macd_slow: int = 26
    """MACD slow EMA span (trading days)."""

    ml_macd_signal: int = 9
    """MACD signal EMA span (trading days)."""

    ml_roc_period: int = 10
    """Rate-of-change lookback period (trading days)."""

    ml_sma_short: int = 20
    """Short moving average period (trading days)."""

    ml_sma_long: int = 50
    """Long moving average period (trading days)."""

    ml_volume_ma_period: int = 20
    """Volume moving average period for ratio feature (trading days)."""


# Singleton — used everywhere as `from app.risk.conventions import CONVENTIONS`
CONVENTIONS = QuantConventions(
    trading_days_per_year=_SETTINGS.trading_days_per_year,
    risk_free_rate=_SETTINGS.risk_free_rate,
    risk_free_rate_source=_SETTINGS.risk_free_rate_source,
    risk_free_rate_last_updated=_SETTINGS.risk_free_rate_last_updated,
    ann_factor_vol=sqrt(_SETTINGS.trading_days_per_year),
    ann_factor_return=float(_SETTINGS.trading_days_per_year),
)


# ═══════════════════════════════════════════════════════════════════════════
# METRIC GOVERNANCE LEVELS
# ═══════════════════════════════════════════════════════════════════════════

GOVERNANCE_LEVELS = {
    "calculated": {
        "label": "Calculated",
        "description": "Computed from available data — no persistence, no backtest, no audit trail.",
        "usable_for_decisions": False,
    },
    "governed": {
        "label": "Governed",
        "description": (
            "Persisted, backtested, historised.  Method documented, "
            "conventions centralised, limitations explicit."
        ),
        "usable_for_decisions": True,
    },
    "exploitable": {
        "label": "Exploitable",
        "description": (
            "Governed + live data source + automated recalc + alerting.  "
            "Ready for production risk management."
        ),
        "usable_for_decisions": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# METRIC SPEC SHEETS
# ═══════════════════════════════════════════════════════════════════════════

METRIC_SPECS: dict[str, dict[str, Any]] = {
    "var_historical": {
        "name": "Historical VaR",
        "category": "risk",
        "governance_level": "governed",
        "method": "Empirical quantile of historical returns",
        "formula": "VaR(α) = -Percentile(returns, 1-α)",
        "sign_convention": CONVENTIONS.var_sign_convention,
        "confidence": list(CONVENTIONS.var_confidence_levels),
        "horizons": list(CONVENTIONS.standard_horizons),
        "horizon_scaling": "Overlapping returns for horizon > 1 (no √T assumption)",
        "min_observations": CONVENTIONS.var_min_observations,
        "annualisation": "N/A (horizon-specific)",
        "risk_free_rate": "N/A",
        "limitations": [
            "Assumption: past distribution ≈ future distribution",
            "Survivorship bias in universe",
            "Fat tails underestimated if history is short",
        ],
        "what_to_keep_simple": "Single-asset VaR only — no portfolio VaR this étape",
        "what_to_defer": "Cornish-Fisher and Monte Carlo VaR deferred to Étape 14",
    },
    "var_parametric": {
        "name": "Parametric VaR",
        "category": "risk",
        "governance_level": "governed",
        "method": "Normal distribution assumption",
        "formula": "VaR(α) = -(μ + σ × Z_{1-α})",
        "sign_convention": CONVENTIONS.var_sign_convention,
        "confidence": list(CONVENTIONS.var_confidence_levels),
        "horizons": list(CONVENTIONS.standard_horizons),
        "horizon_scaling": "√T scaling (σ√T + μT)",
        "min_observations": CONVENTIONS.var_min_observations,
        "annualisation": "Implicit via √T",
        "risk_free_rate": "N/A",
        "limitations": [
            "Assumes normal distribution — understates tail risk",
            "Mean scaling is arithmetic (not geometric)",
        ],
        "what_to_keep_simple": "Normal assumption only — no Student-t this étape",
        "what_to_defer": "Student-t and custom distributions → Étape 14",
    },
    "cvar": {
        "name": "Conditional VaR (Expected Shortfall)",
        "category": "risk",
        "governance_level": "governed",
        "method": "Average of returns beyond VaR threshold",
        "formula": "CVaR(α) = -E[R | R ≤ -VaR(α)]",
        "sign_convention": CONVENTIONS.var_sign_convention,
        "confidence": list(CONVENTIONS.var_confidence_levels),
        "horizons": list(CONVENTIONS.standard_horizons),
        "horizon_scaling": "Inherits from underlying VaR method",
        "min_observations": CONVENTIONS.var_min_observations,
        "annualisation": "N/A",
        "risk_free_rate": "N/A",
        "limitations": [
            "Sensitive to extreme tail events (single outlier can shift significantly)",
            "Historical CVaR requires enough tail observations",
        ],
        "what_to_keep_simple": "Historical CVaR only",
        "what_to_defer": "Parametric CVaR → Étape 14",
    },
    "volatility": {
        "name": "Annualised Volatility",
        "category": "risk",
        "governance_level": "governed",
        "method": "Standard deviation of daily returns × √252",
        "formula": "σ_ann = std(returns) × √252",
        "sign_convention": "positive",
        "confidence": "N/A",
        "horizons": "N/A (annualised)",
        "horizon_scaling": "N/A",
        "min_observations": 21,
        "annualisation": f"√{CONVENTIONS.trading_days_per_year} = {CONVENTIONS.ann_factor_vol:.4f}",
        "risk_free_rate": "N/A",
        "limitations": [
            "IID assumption — vol clustering not captured",
            "Equally weighted (no EWMA / GARCH)",
        ],
        "what_to_keep_simple": "Equal-weight standard deviation",
        "what_to_defer": "EWMA / GARCH volatility models → Étape 14",
    },
    "max_drawdown": {
        "name": "Maximum Drawdown",
        "category": "risk",
        "governance_level": "governed",
        "method": "Max peak-to-trough decline in equity curve",
        "formula": "MDD = max_t [(cummax(equity) - equity_t) / cummax(equity)]",
        "sign_convention": "negative (e.g., -0.20 = 20% drawdown)",
        "confidence": "N/A",
        "horizons": "Full history",
        "horizon_scaling": "N/A",
        "min_observations": 63,
        "annualisation": "N/A",
        "risk_free_rate": "N/A",
        "limitations": [
            "Single number — doesn't capture recovery time or frequency",
            "Path-dependent — different orderings yield different MDD",
        ],
        "what_to_keep_simple": "MDD only — no drawdown duration this étape",
        "what_to_defer": "Drawdown duration, conditional drawdown at risk → Étape 14",
    },
    "sharpe_ratio": {
        "name": "Sharpe Ratio",
        "category": "performance",
        "governance_level": "governed",
        "method": "Excess return per unit volatility",
        "formula": f"SR = (r_ann - Rf) / σ_ann,  Rf = {CONVENTIONS.risk_free_rate}",
        "sign_convention": "higher is better",
        "confidence": "N/A",
        "horizons": "Annualised",
        "horizon_scaling": "N/A",
        "min_observations": 63,
        "annualisation": f"√{CONVENTIONS.trading_days_per_year} for σ, ×{CONVENTIONS.trading_days_per_year} for μ",
        "risk_free_rate": f"{CONVENTIONS.risk_free_rate} ({CONVENTIONS.risk_free_rate_source})",
        "limitations": [
            "Assumes normal distribution of returns",
            "Sensitive to outliers / short periods",
            "Static risk-free rate (not term-structure adjusted)",
        ],
        "what_to_keep_simple": "Ex-post Sharpe with static Rf",
        "what_to_defer": "Rolling Sharpe, probabilistic Sharpe ratio → Étape 14",
    },
    "sortino_ratio": {
        "name": "Sortino Ratio",
        "category": "performance",
        "governance_level": "governed",
        "method": "Excess return per unit downside volatility",
        "formula": f"Sortino = (r_ann - Rf) / σ_downside,  Rf = {CONVENTIONS.risk_free_rate}",
        "sign_convention": "higher is better",
        "confidence": "N/A",
        "horizons": "Annualised",
        "horizon_scaling": "N/A",
        "min_observations": 63,
        "annualisation": f"√{CONVENTIONS.trading_days_per_year}",
        "risk_free_rate": f"{CONVENTIONS.risk_free_rate} ({CONVENTIONS.risk_free_rate_source})",
        "limitations": [
            "Only penalises downside — may overstate risk-adjusted returns",
            "Requires enough negative return observations",
        ],
        "what_to_keep_simple": "Single-period Sortino",
        "what_to_defer": "Rolling / conditional Sortino → Étape 14",
    },
    "calmar_ratio": {
        "name": "Calmar Ratio",
        "category": "performance",
        "governance_level": "governed",
        "method": "Annualised return / |max drawdown|",
        "formula": "Calmar = r_ann / |MDD|",
        "sign_convention": "higher is better",
        "confidence": "N/A",
        "horizons": "Annualised return, full-history MDD",
        "horizon_scaling": "N/A",
        "min_observations": 252,
        "annualisation": f"×{CONVENTIONS.trading_days_per_year} for return",
        "risk_free_rate": "N/A",
        "limitations": [
            "MDD is path-dependent and backward-looking",
            "Single extreme event can dominate",
        ],
        "what_to_keep_simple": "Standard Calmar",
        "what_to_defer": "Modified Calmar (rolling 3Y window) → Étape 14",
    },
    "stress_test": {
        "name": "Stress Test (Simple Shocks)",
        "category": "risk",
        "governance_level": "calculated",
        "method": "Apply fixed % shock to portfolio and compute P&L",
        "formula": "P&L_shock = Σ(weight_i × return_i × (1 + shock))",
        "sign_convention": "negative P&L = loss",
        "confidence": "N/A",
        "horizons": "Instantaneous",
        "horizon_scaling": "N/A",
        "min_observations": 0,
        "annualisation": "N/A",
        "risk_free_rate": "N/A",
        "limitations": [
            "Linear shocks only — no cross-asset correlation in stress",
            "Historical scenarios not versioned",
            "No probability assignment to scenarios",
        ],
        "what_to_keep_simple": "Single-factor shocks (-20% to +20%)",
        "what_to_defer": "Multi-factor stress, reverse stress, conditional scenarios → Étape 14",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# INCOHERENCES & CORRECTION PLAN
# ═══════════════════════════════════════════════════════════════════════════

CURRENT_INCOHERENCES: list[dict[str, str]] = [
    {
        "issue": "Risk-free rate inconsistent across modules",
        "detail": "src/genesix/risk_engine uses Rf=0.02, src/core/risk.py uses Rf=0.0, backtest/engine uses Rf=0.04",
        "correction": "Backend modules now resolve Rf via Settings -> CONVENTIONS; src alignment remains pending",
        "status": "partially_corrected_backend",
    },
    {
        "issue": "Annualisation factor not centralised",
        "detail": "√252 hardcoded in multiple places",
        "correction": "Use CONVENTIONS.ann_factor_vol everywhere",
        "status": "fixed_in_etape_10",
    },
    {
        "issue": "VaR sign convention varies",
        "detail": "risk.py returns (negative, absolute), risk_engine returns positive",
        "correction": "Standardise to positive_loss via CONVENTIONS.var_sign_convention",
        "status": "fixed_in_etape_10",
    },
    {
        "issue": "No rolling window policy",
        "detail": "Some code uses 60d, others 250d, no standard",
        "correction": "Use CONVENTIONS.rolling_windows and default_rolling_window",
        "status": "fixed_in_etape_10",
    },
    {
        "issue": "Stress test scenarios not versioned",
        "detail": "Scenario params embedded in function calls, not stored",
        "correction": "Persist scenario definitions alongside results (deferred to Étape 14)",
        "status": "deferred",
    },
    {
        "issue": "Data source not documented per metric",
        "detail": "No metadata linking metric output to data provenance",
        "correction": "RiskSnapshot stores data_source field",
        "status": "fixed_in_etape_10",
    },
]

CORRECTION_PLAN: list[dict[str, str]] = [
    {"step": "1", "action": "Centralise QuantConventions (this file)", "status": "done"},
    {"step": "2", "action": "Build risk engine using CONVENTIONS", "status": "done"},
    {"step": "3", "action": "Add RiskSnapshot DB model for persistence", "status": "done"},
    {"step": "4", "action": "Expose /risk/ API with spec sheets", "status": "done"},
    {"step": "5", "action": "Version stress scenarios (deferred)", "status": "deferred_etape_14"},
    {"step": "6", "action": "Live Rf feed integration (deferred)", "status": "deferred_etape_14"},
]
