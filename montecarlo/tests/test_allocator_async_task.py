from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import AllocationRecommendationResponse
from app.services import allocation_recommendation_service, investor_policy_service
from app.workers.tasks import allocator_task


def _sample_recommendation() -> AllocationRecommendationResponse:
    return AllocationRecommendationResponse(
        recommendation_id="rec-123",
        run_id="run-123",
        persistence_status="persisted",
        policy=investor_policy_service.build_investor_policy(
            {
                "amount": 10_000,
                "base_currency": "USD",
                "risk_aversion": 0.5,
                "investment_horizon_years": 3,
                "liquidity_needs": "medium",
                "objective_type": "balanced",
                "candidate_tickers": ["AAPL", "MSFT"],
            }
        ),
        eligibility={
            "criteria": {
                "heuristic_version": "v1",
                "min_market_cap": 750_000_000.0,
                "min_volume_avg_30d": 750_000.0,
                "allowed_asset_classes": [],
                "allowed_currencies": [],
                "require_price": True,
                "require_market_cap_for_equities": True,
                "require_volume_proxy": True,
                "require_cost_proxy": False,
            },
            "eligible_assets": [],
            "rejected_assets": [],
            "warnings": [],
        },
        assumptions={
            "methodology_version": "cma_v1",
            "risk_free_rate_used": 0.03,
            "investment_horizon_years": 3,
            "assumptions": [],
            "warnings": [],
        },
        risk_inputs={
            "methodology_version": "portfolio_risk_inputs_v1",
            "risk_model_type": "historical_covariance_allocator_v1",
            "data_source": "yfinance",
            "lookback_days": 252,
            "observation_count": 252,
            "annualization_factor": 252,
            "risk_free_rate_used": 0.03,
            "benchmark_preference": "60_40",
            "tickers_used": ["AAPL", "MSFT"],
            "dropped_tickers": [],
            "asset_risk_inputs": [],
            "covariance_matrix": {
                "AAPL": {"AAPL": 0.04, "MSFT": 0.02},
                "MSFT": {"AAPL": 0.02, "MSFT": 0.03},
            },
            "correlation_matrix": {
                "AAPL": {"AAPL": 1.0, "MSFT": 0.6},
                "MSFT": {"AAPL": 0.6, "MSFT": 1.0},
            },
            "top_correlation_pairs": [],
            "risk_budget": {
                "target_volatility": 0.14,
                "max_drawdown_tolerance": 0.2,
                "max_single_name_weight": 0.4,
                "min_weight": 0.0,
                "cash_buffer_weight": 0.0,
                "concentration_hhi_soft_limit": 0.2,
                "effective_name_floor": 5.0,
            },
            "universe_risk_diagnostics": {
                "asset_count": 2,
                "observation_count": 252,
                "average_pairwise_correlation": 0.6,
                "max_pairwise_correlation": 0.6,
                "volatility_dispersion": 0.01,
            },
            "governance_summary": {
                "model_type": "historical_covariance_allocator_v1",
                "covariance_estimator": "ledoit_wolf",
                "concentration_support": "post_optimization_only",
                "scenario_support": "deferred",
                "limitations": ["historical covariance only"],
            },
            "warnings": [],
        },
        eligible_tickers=["AAPL", "MSFT"],
        recommended_assets=[],
        rejected_assets=[],
        optimization={
            "objective": "risk_parity",
            "expected_return": 0.08,
            "expected_volatility": 0.12,
            "sharpe_ratio": 1.0,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.1,
            "selected_candidate_id": "risk_parity_assumption_aware",
            "constraint_snapshot": {
                "max_weight": 0.4,
                "min_weight": 0.0,
                "target_volatility": 0.14,
                "max_drawdown_tolerance": 0.2,
                "cash_buffer_weight": 0.0,
                "lookback_days": 252,
            },
            "selected_risk_diagnostics": {
                "portfolio_volatility": 0.12,
                "concentration_hhi": 0.5,
                "effective_number_of_names": 2.0,
                "max_single_name_weight": 0.5,
                "weighted_drawdown_proxy": 0.18,
                "target_volatility_gap": -0.02,
                "risk_budget_breaches": [],
            },
            "selected_constraint_diagnostics": {
                "selected_asset_count": 2,
                "max_selected_assets": 2,
                "cardinality_breach": False,
                "turnover_from_current": 0.10,
                "asset_class_exposures": [],
                "asset_class_breaches": [],
                "active_constraints": ["max_selected_assets"],
            },
            "candidate_portfolios": [],
            "efficient_frontier": [],
        },
        total_allocated_amount=10_000,
        cash_reserve_amount=0.0,
        warnings=[],
    )


def test_allocator_task_serializes_service_response(monkeypatch) -> None:
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_allocation_recommendation",
        lambda payload: _sample_recommendation(),
    )

    result = allocator_task.recommend_allocation.run(
        amount=10_000,
        base_currency="USD",
        risk_aversion=0.5,
        investment_horizon_years=3,
        liquidity_needs="medium",
        objective_type="balanced",
        candidate_tickers=["AAPL", "MSFT"],
    )

    assert result["status"] == "ok"
    assert result["recommendation"]["recommendation_id"] == "rec-123"
    assert result["recommendation"]["run_id"] == "run-123"


def test_allocator_task_returns_error_payload_on_invalid_request(monkeypatch) -> None:
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_allocation_recommendation",
        lambda payload: (_ for _ in ()).throw(ValueError("invalid allocator request")),
    )

    result = allocator_task.recommend_allocation.run(candidate_tickers=["AAPL"])

    assert result == {"status": "error", "detail": "invalid allocator request"}
