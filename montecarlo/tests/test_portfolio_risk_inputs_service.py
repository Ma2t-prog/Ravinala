from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import (
    EligibleUniverseResponse,
    PortfolioRiskInputsResponse,
)
from app.services import investor_policy_service, portfolio_risk_inputs_service


def _policy():
    return investor_policy_service.build_investor_policy(
        {
            "amount": 100_000,
            "base_currency": "USD",
            "risk_aversion": 0.60,
            "investment_horizon_years": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "candidate_tickers": ["AAPL", "MSFT", "TLT"],
            "benchmark_preference": "60_40",
        }
    )


def _eligibility() -> EligibleUniverseResponse:
    return EligibleUniverseResponse(
        criteria={
            "heuristic_version": "v1",
            "min_market_cap": 750_000_000.0,
            "min_volume_avg_30d": 750_000.0,
            "allowed_asset_classes": ["equity", "bond"],
            "allowed_currencies": [],
            "require_price": True,
            "require_market_cap_for_equities": True,
            "require_volume_proxy": True,
            "require_cost_proxy": False,
        },
        eligible_assets=[
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_class": "equity",
                "currency": "USD",
                "price": 190.0,
                "liquidity_tier": "deep",
                "data_quality_score": 1.0,
                "cost_proxy_available": True,
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "asset_class": "equity",
                "currency": "USD",
                "price": 420.0,
                "liquidity_tier": "deep",
                "data_quality_score": 1.0,
                "cost_proxy_available": True,
            },
            {
                "ticker": "TLT",
                "name": "iShares 20+ Year Treasury Bond ETF",
                "asset_class": "bond",
                "currency": "USD",
                "price": 95.0,
                "liquidity_tier": "deep",
                "data_quality_score": 1.0,
                "cost_proxy_available": True,
            },
        ],
        rejected_assets=[],
        warnings=[],
    )


def test_build_portfolio_risk_inputs_returns_typed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    returns = pd.DataFrame(
        {
            "AAPL": [0.01, -0.02, 0.015, 0.012, -0.008],
            "MSFT": [0.008, -0.015, 0.011, 0.010, -0.006],
            "TLT": [0.002, 0.003, -0.001, 0.002, 0.001],
        }
    )
    individual_vols = pd.Series({"AAPL": 0.22, "MSFT": 0.18, "TLT": 0.07}, dtype=float)
    cov_matrix = pd.DataFrame(
        {
            "AAPL": {"AAPL": 0.0484, "MSFT": 0.0280, "TLT": 0.0040},
            "MSFT": {"AAPL": 0.0280, "MSFT": 0.0324, "TLT": 0.0035},
            "TLT": {"AAPL": 0.0040, "MSFT": 0.0035, "TLT": 0.0049},
        }
    )

    monkeypatch.setattr(
        portfolio_risk_inputs_service,
        "load_market_risk_inputs_frame",
        lambda tickers, lookback_days: (returns[tickers], individual_vols.loc[tickers], cov_matrix.loc[tickers, tickers]),
    )
    monkeypatch.setattr(
        portfolio_risk_inputs_service,
        "covariance_estimator_name",
        lambda: "ledoit_wolf",
    )

    result = portfolio_risk_inputs_service.build_portfolio_risk_inputs(
        eligibility=_eligibility(),
        policy=_policy(),
    )

    assert result.methodology_version == "portfolio_risk_inputs_v1"
    assert result.risk_model_type == "historical_covariance_allocator_v1"
    assert result.tickers_used == ["AAPL", "MSFT", "TLT"]
    assert result.asset_risk_inputs[0].ticker == "AAPL"
    assert result.covariance_matrix["AAPL"]["MSFT"] == pytest.approx(0.0280)
    assert result.correlation_matrix["AAPL"]["MSFT"] == pytest.approx(returns.corr().loc["AAPL", "MSFT"])
    assert result.risk_budget.max_single_name_weight == pytest.approx(_policy().max_weight)
    assert result.governance_summary.scenario_support == "deferred"


def test_candidate_risk_diagnostics_flags_budget_breaches() -> None:
    risk_inputs = PortfolioRiskInputsResponse(
        methodology_version="portfolio_risk_inputs_v1",
        risk_model_type="historical_covariance_allocator_v1",
        data_source="yfinance",
        lookback_days=504,
        observation_count=252,
        annualization_factor=252,
        risk_free_rate_used=0.03,
        benchmark_preference="60_40",
        tickers_used=["AAPL", "MSFT"],
        dropped_tickers=[],
        asset_risk_inputs=[
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_class": "equity",
                "annualized_volatility": 0.22,
                "downside_volatility": 0.18,
                "max_drawdown_proxy": 0.24,
                "var_95_1d": 0.02,
                "cvar_95_1d": 0.03,
                "data_points_used": 252,
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "asset_class": "equity",
                "annualized_volatility": 0.18,
                "downside_volatility": 0.15,
                "max_drawdown_proxy": 0.20,
                "var_95_1d": 0.018,
                "cvar_95_1d": 0.026,
                "data_points_used": 252,
            },
        ],
        covariance_matrix={
            "AAPL": {"AAPL": 0.0484, "MSFT": 0.0280},
            "MSFT": {"AAPL": 0.0280, "MSFT": 0.0324},
        },
        correlation_matrix={
            "AAPL": {"AAPL": 1.0, "MSFT": 0.71},
            "MSFT": {"AAPL": 0.71, "MSFT": 1.0},
        },
        top_correlation_pairs=[],
        risk_budget={
            "target_volatility": 0.14,
            "max_drawdown_tolerance": 0.20,
            "max_single_name_weight": 0.35,
            "min_weight": 0.0,
            "cash_buffer_weight": 0.05,
            "concentration_hhi_soft_limit": 0.18,
            "effective_name_floor": 5.56,
        },
        universe_risk_diagnostics={
            "asset_count": 2,
            "observation_count": 252,
            "average_pairwise_correlation": 0.71,
            "max_pairwise_correlation": 0.71,
            "volatility_dispersion": 0.04,
        },
        governance_summary={
            "model_type": "historical_covariance_allocator_v1",
            "covariance_estimator": "ledoit_wolf",
            "concentration_support": "post_optimization_only",
            "scenario_support": "deferred",
            "limitations": ["historical covariance only"],
        },
        warnings=[],
    )

    diagnostics = portfolio_risk_inputs_service.build_candidate_risk_diagnostics(
        candidate_weights={"AAPL": 0.7, "MSFT": 0.3},
        risk_inputs=risk_inputs,
    )

    assert diagnostics.max_single_name_weight == pytest.approx(0.7)
    assert diagnostics.concentration_hhi == pytest.approx(0.58)
    assert "max_single_name_weight" in diagnostics.risk_budget_breaches
    assert "concentration_hhi_soft_limit" in diagnostics.risk_budget_breaches
