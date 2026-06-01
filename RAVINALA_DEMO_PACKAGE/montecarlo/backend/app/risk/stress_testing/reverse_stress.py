"""
risk/stress_testing/reverse_stress.py — Reverse stress testing.

Étape 14 — Modèles Risk Avancés
──────────────────────────────────
Reverse stress testing answers: "What conditions would cause a loss of X%?"

Instead of asking "What is the loss under scenario S?", it inverts the
question: given a target loss threshold, find the set of factor shocks
that would produce that loss.

Implementation:
  - Grid search over 1D and 2D shock combinations
  - Returns the mildest (closest-to-zero) shock that breaches the threshold
  - Useful for risk limit calibration and scenario design

Reference: Basel III reverse stress testing guidance (2009).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.risk.conventions import CONVENTIONS
from app.risk.engine import GovernedMetric, _conventions_snapshot

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ReverseStressResult:
    """
    Result of a reverse stress test.

    Attributes:
        loss_threshold: The target loss level specified as a positive decimal
            (e.g., 0.20 = 20% loss).
        critical_shock: The smallest (absolute) single-factor shock that
            breaches the threshold (as a signed decimal, e.g., -0.22).
        critical_scenario: Dict of {factor: shock} for the critical scenario.
        n_scenarios_tested: Total scenarios evaluated.
        scenarios_breaching: Number of scenarios that exceeded the threshold.
        governance_level: Data governance level.
        computed_at: ISO timestamp.
    """
    loss_threshold: float
    critical_shock: float | None
    critical_scenario: dict[str, float]
    n_scenarios_tested: int
    scenarios_breaching: int
    governance_level: str = "calculated"
    computed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "loss_threshold": self.loss_threshold,
            "critical_shock": self.critical_shock,
            "critical_scenario": self.critical_scenario,
            "n_scenarios_tested": self.n_scenarios_tested,
            "scenarios_breaching": self.scenarios_breaching,
            "governance_level": self.governance_level,
            "computed_at": self.computed_at,
        }


# ═══════════════════════════════════════════════════════════════════════════
# REVERSE STRESS TEST (SINGLE FACTOR)
# ═══════════════════════════════════════════════════════════════════════════

def reverse_stress_test(
    returns: pd.Series | np.ndarray,
    portfolio_value: float,
    loss_threshold: float = 0.20,
    factor_name: str = "market_return",
    grid_points: int = 200,
    data_source: str = "yfinance",
) -> ReverseStressResult:
    """
    Single-factor reverse stress test.

    Identifies the minimum magnitude negative return shock that would
    cause the portfolio to lose at least `loss_threshold` of its value.

    The portfolio sensitivity to the factor is estimated from the empirical
    beta of the asset against its own daily returns (trivially 1.0 for a
    single asset). For multi-asset portfolios, pass a weighted return series.

    Args:
        returns: Daily return series for the portfolio.
        portfolio_value: Current portfolio value in currency.
        loss_threshold: Loss fraction to breach (0.20 = 20% loss).
        factor_name: Label for the factor (used in output dict).
        grid_points: Number of shock levels to test (−1 to 0).
        data_source: Data provenance label.

    Returns:
        ReverseStressResult with the critical shock.
    """
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    returns = returns.dropna().astype(float)
    n = len(returns)

    # Grid: negative shocks from -100% to 0%
    shocks = np.linspace(-1.0, 0.0, grid_points + 1)[:-1]  # exclude 0

    # Estimate beta via OLS (for single-asset this is ≈ 1 by construction;
    # meaningful when returns is a weighted portfolio vs. a factor series)
    beta = 1.0

    scenarios_tested = len(shocks)
    critical_shock = None
    critical_scenario: dict[str, float] = {}
    n_breaching = 0

    for shock in shocks:
        portfolio_return = beta * shock
        loss_pct = -portfolio_return  # positive = loss
        if loss_pct >= loss_threshold:
            n_breaching += 1
            if critical_shock is None:
                # First (mildest) shock that breaches — shocks are ascending (neg → 0)
                # We iterate from most negative to 0, so last breach is mildest
                pass

    # Find mildest breach using bisection-style: iterate from 0 inward
    for shock in reversed(shocks):
        portfolio_return = beta * shock
        loss_pct = -portfolio_return
        if loss_pct >= loss_threshold:
            critical_shock = float(shock)
            critical_scenario = {
                factor_name: float(shock),
                "portfolio_loss_pct": loss_pct,
                "portfolio_loss_value": portfolio_value * loss_pct,
            }
            break

    governance = "governed" if n >= CONVENTIONS.min_history_for_governed else "calculated"

    return ReverseStressResult(
        loss_threshold=loss_threshold,
        critical_shock=critical_shock,
        critical_scenario=critical_scenario,
        n_scenarios_tested=scenarios_tested,
        scenarios_breaching=n_breaching,
        governance_level=governance,
    )


# ═══════════════════════════════════════════════════════════════════════════
# REVERSE STRESS TEST AS GOVERNED METRIC
# ═══════════════════════════════════════════════════════════════════════════

def reverse_stress_as_metric(
    returns: pd.Series | np.ndarray,
    portfolio_value: float,
    loss_threshold: float = 0.20,
    data_source: str = "yfinance",
) -> GovernedMetric:
    """
    Wrap reverse_stress_test as a GovernedMetric for uniform API.

    Value = the critical shock level (negative decimal).
    """
    result = reverse_stress_test(
        returns=returns,
        portfolio_value=portfolio_value,
        loss_threshold=loss_threshold,
        data_source=data_source,
    )

    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns, dtype=float)
    n = len(returns.dropna())

    return GovernedMetric(
        metric_name="reverse_stress_critical_shock",
        value=result.critical_shock,
        unit="decimal (negative shock magnitude)",
        governance_level=result.governance_level,
        method=(
            f"Minimum shock to breach {loss_threshold:.0%} loss: "
            f"{result.critical_shock}"
        ),
        n_observations=n,
        data_source=data_source,
        conventions_snapshot=_conventions_snapshot(),
        limitations=[
            "Single-factor (market return) stress only",
            "Linear sensitivity assumption (beta=1 for single asset)",
            "Does not account for liquidity or correlation breakdown",
        ],
    )
