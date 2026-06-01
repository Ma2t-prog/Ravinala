"""
risk/stress_testing/conditional_stress.py — Conditional stress scenarios.

Étape 14 — Modèles Risk Avancés
──────────────────────────────────
Conditional stress testing evaluates portfolio performance under scenarios
conditioned on specific macro factor realisations.

Unlike simple stress tests (apply fixed % shock), conditional stress uses
historical data to condition on macro regimes. It answers:
  "What was our average return during periods when rates rose > 50bps?"
  "How did we perform when inflation was > 4%?"
  "What is our expected loss during equity drawdowns > 15%?"

Implementation:
  macro_stress_scenarios  — Named macro scenario catalogue
  conditional_stress_test — Apply a named or custom scenario and estimate P&L

Reference: BIS Working Paper #275 (2009) — "The use of stress tests"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.risk.conventions import CONVENTIONS
from app.risk.engine import GovernedMetric, _conventions_snapshot

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PREDEFINED MACRO STRESS SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

# Each scenario is a dict of {factor: shock_decimal}
# Shocks are applied as instantaneous portfolio return shocks.
# Sources: IMF, Basel III, historical crisis periods.

_SCENARIOS: dict[str, dict[str, Any]] = {
    "covid_crash_2020": {
        "label": "COVID-19 Crash (Feb-Mar 2020)",
        "equity_shock": -0.34,
        "credit_spread_bps": +350,
        "vol_spike": +40,  # VIX-equivalent
        "description": "S&P 500 fell 34% peak-to-trough in 33 days",
        "source": "Historical (2020-02-19 to 2020-03-23)",
    },
    "gfc_2008": {
        "label": "GFC — Lehman Collapse (Sep-Dec 2008)",
        "equity_shock": -0.45,
        "credit_spread_bps": +600,
        "vol_spike": +60,
        "description": "S&P 500 fell 45% from peak, credit markets froze",
        "source": "Historical (2008-09-15 to 2008-12-31)",
    },
    "dotcom_burst_2000": {
        "label": "Dot-com Burst (Mar 2000 - Oct 2002)",
        "equity_shock": -0.49,
        "credit_spread_bps": +200,
        "vol_spike": +25,
        "description": "NASDAQ fell 78%, S&P 500 fell 49%",
        "source": "Historical (2000-03-10 to 2002-10-09)",
    },
    "rate_shock_200bps": {
        "label": "Rate Shock +200bps",
        "equity_shock": -0.12,
        "rate_shock_bps": +200,
        "credit_spread_bps": +80,
        "description": "Instantaneous parallel shift of yield curve +200bps",
        "source": "Basel III interest rate stress test",
    },
    "rate_shock_400bps": {
        "label": "Rate Shock +400bps (Volcker-style)",
        "equity_shock": -0.20,
        "rate_shock_bps": +400,
        "credit_spread_bps": +150,
        "description": "Severe rate spike as seen in 1979-1981 Volcker tightening",
        "source": "Basel III / DFAST severe adverse scenario",
    },
    "stagflation": {
        "label": "Stagflation (1970s style)",
        "equity_shock": -0.25,
        "inflation_shock_pct": +5.0,
        "rate_shock_bps": +300,
        "description": "High inflation + recession + rising rates",
        "source": "1973-1975 / 1979-1982 analogy",
    },
    "flash_crash": {
        "label": "Flash Crash (1-day event)",
        "equity_shock": -0.10,
        "vol_spike": +30,
        "description": "Intraday liquidity crisis, rapid recovery likely",
        "source": "2010-05-06 Flash Crash (S&P -10% intraday)",
    },
    "mild_recession": {
        "label": "Mild Recession",
        "equity_shock": -0.15,
        "credit_spread_bps": +120,
        "description": "Mild economic contraction, no financial crisis",
        "source": "DFAST adverse scenario",
    },
}


def macro_stress_scenarios() -> dict[str, dict[str, Any]]:
    """Return the full catalogue of predefined macro stress scenarios."""
    return {k: {**v} for k, v in _SCENARIOS.items()}


# ═══════════════════════════════════════════════════════════════════════════
# CONDITIONAL STRESS TEST
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConditionalStressResult:
    scenario_name: str
    scenario_label: str
    equity_shock: float
    portfolio_loss_pct: float
    portfolio_loss_value: float
    portfolio_value: float
    factors_applied: dict[str, Any]
    governance_level: str = "calculated"
    computed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "scenario_label": self.scenario_label,
            "equity_shock": self.equity_shock,
            "portfolio_loss_pct": self.portfolio_loss_pct,
            "portfolio_loss_value": round(self.portfolio_loss_value, 2),
            "portfolio_value": self.portfolio_value,
            "factors_applied": self.factors_applied,
            "governance_level": self.governance_level,
            "computed_at": self.computed_at,
        }


def conditional_stress_test(
    portfolio_value: float,
    returns: pd.Series | np.ndarray | None = None,
    scenario_name: str = "covid_crash_2020",
    custom_equity_shock: float | None = None,
    equity_beta: float = 1.0,
    data_source: str = "yfinance",
) -> list[ConditionalStressResult]:
    """
    Apply a predefined or custom macro stress scenario to a portfolio.

    For each scenario, computes the estimated portfolio P&L using:
        portfolio_return ≈ equity_beta × equity_shock

    Args:
        portfolio_value: Current portfolio value.
        returns: Historical returns (used to estimate equity_beta if None).
        scenario_name: Key from macro_stress_scenarios() catalogue,
            or "all" to run all predefined scenarios.
        custom_equity_shock: Override the scenario's equity shock.
        equity_beta: Portfolio sensitivity to equity market (1.0 = fully correlated).
        data_source: Data provenance label.

    Returns:
        List of ConditionalStressResult (one per scenario applied).
    """
    if isinstance(returns, np.ndarray) and returns is not None:
        returns = pd.Series(returns, dtype=float)
    n = len(returns.dropna()) if returns is not None else 0

    governance = "governed" if n >= CONVENTIONS.min_history_for_governed else "calculated"

    if scenario_name == "all":
        scenarios_to_run = list(_SCENARIOS.keys())
    elif scenario_name in _SCENARIOS:
        scenarios_to_run = [scenario_name]
    else:
        logger.warning("Unknown scenario '%s', falling back to 'all'", scenario_name)
        scenarios_to_run = list(_SCENARIOS.keys())

    results = []
    for key in scenarios_to_run:
        scenario = _SCENARIOS[key]
        eq_shock = custom_equity_shock if custom_equity_shock is not None else float(scenario.get("equity_shock", 0.0))

        portfolio_return = equity_beta * eq_shock
        loss_pct = -portfolio_return
        loss_value = portfolio_value * loss_pct

        factors = {k: v for k, v in scenario.items() if k not in ("label", "description", "source")}

        results.append(ConditionalStressResult(
            scenario_name=key,
            scenario_label=str(scenario.get("label", key)),
            equity_shock=eq_shock,
            portfolio_loss_pct=round(loss_pct, 6),
            portfolio_loss_value=round(loss_value, 2),
            portfolio_value=portfolio_value,
            factors_applied=factors,
            governance_level=governance,
        ))

    return results


def conditional_stress_as_metrics(
    portfolio_value: float,
    returns: pd.Series | np.ndarray | None = None,
    scenario_name: str = "all",
    equity_beta: float = 1.0,
    data_source: str = "yfinance",
) -> list[GovernedMetric]:
    """
    Return conditional stress results as GovernedMetric list.
    Suitable for inclusion in the full risk report.
    """
    stress_results = conditional_stress_test(
        portfolio_value=portfolio_value,
        returns=returns,
        scenario_name=scenario_name,
        equity_beta=equity_beta,
        data_source=data_source,
    )

    if isinstance(returns, np.ndarray) and returns is not None:
        returns = pd.Series(returns, dtype=float)
    n = len(returns.dropna()) if returns is not None else 0

    metrics = []
    for sr in stress_results:
        metrics.append(GovernedMetric(
            metric_name=f"conditional_stress_{sr.scenario_name}",
            value=round(sr.portfolio_loss_pct, 6),
            unit="decimal (loss fraction)",
            governance_level=sr.governance_level,
            method=f"{sr.scenario_label}: equity_shock={sr.equity_shock:.2%}, β={equity_beta}",
            n_observations=n,
            data_source=data_source,
            conventions_snapshot=_conventions_snapshot(),
            limitations=[
                "Linear sensitivity (equity_beta) — ignores non-linearity and basis risk",
                "Does not account for credit spread or rate impacts beyond equity",
            ],
        ))

    return metrics
