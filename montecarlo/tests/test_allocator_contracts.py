from __future__ import annotations

import sys
from pathlib import Path

from fastapi.routing import APIRoute

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import allocator as allocator_routes
from app.schemas.allocator import (
    AllocationRecommendationAsyncResponse,
    AllocationRecommendationRequest,
    AllocationRecommendationResponse,
    AllocationRunDetail,
    AllocationOptimizationSummary,
    CapitalMarketAssumptionsResponse,
    InvestorPolicy,
    PortfolioRiskInputsResponse,
)
from app.workers.celery_app import celery_app


def _route(path: str, method: str) -> APIRoute:
    for candidate in allocator_routes.router.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"Route not found for {method} {path}")


def test_allocator_router_exposes_typed_recommend_and_run_routes() -> None:
    eligibility_route = _route("/api/v1/allocator/eligible-universe", "POST")
    assumptions_route = _route("/api/v1/allocator/assumptions", "POST")
    risk_inputs_route = _route("/api/v1/allocator/risk-inputs", "POST")
    recommend_route = _route("/api/v1/allocator/recommend", "POST")
    recommend_async_route = _route("/api/v1/allocator/recommend/async", "POST")
    list_route = _route("/api/v1/allocator/runs", "GET")
    detail_route = _route("/api/v1/allocator/runs/{run_id}", "GET")

    assert "ApiResponse" in str(eligibility_route.response_model)
    assert "EligibleUniverseResponse" in str(eligibility_route.response_model)
    assert "ApiResponse" in str(assumptions_route.response_model)
    assert "CapitalMarketAssumptionsResponse" in str(assumptions_route.response_model)
    assert "ApiResponse" in str(risk_inputs_route.response_model)
    assert "PortfolioRiskInputsResponse" in str(risk_inputs_route.response_model)
    assert "ApiResponse" in str(recommend_route.response_model)
    assert "AllocationRecommendationResponse" in str(recommend_route.response_model)
    assert "ApiResponse" in str(recommend_async_route.response_model)
    assert "AllocationRecommendationAsyncResponse" in str(recommend_async_route.response_model)
    assert "ApiResponse" in str(list_route.response_model)
    assert "AllocationRunSummary" in str(list_route.response_model)
    assert "ApiResponse" in str(detail_route.response_model)
    assert "AllocationRunDetail" in str(detail_route.response_model)


def test_allocator_policy_schema_includes_canonical_investor_inputs() -> None:
    policy_fields = set(InvestorPolicy.model_fields)

    assert {
        "amount",
        "base_currency",
        "risk_aversion",
        "investment_horizon_years",
        "liquidity_needs",
        "objective_type",
        "allowed_asset_classes",
        "excluded_tickers",
        "max_selected_assets",
        "asset_class_constraints",
        "current_position_weights",
        "benchmark_preference",
    }.issubset(policy_fields)


def test_allocator_recommendation_schema_carries_explanation_payload() -> None:
    recommendation_fields = set(AllocationRecommendationResponse.model_fields)

    assert {
        "assumptions",
        "eligibility",
        "policy",
        "risk_inputs",
        "recommended_assets",
        "rejected_assets",
        "optimization",
        "warnings",
        "run_id",
    }.issubset(recommendation_fields)

    assert "created_at" in AllocationRunDetail.model_fields
    assert "assumptions" in AllocationRunDetail.model_fields
    assert {
        "selected_candidate_id",
        "constraint_snapshot",
        "selected_risk_diagnostics",
        "selected_constraint_diagnostics",
        "candidate_portfolios",
    }.issubset(
        set(AllocationOptimizationSummary.model_fields)
    )


def test_allocator_async_schema_is_explicit() -> None:
    payload = AllocationRecommendationAsyncResponse(job_id="job-123")

    assert payload.job_id == "job-123"
    assert payload.status == "PENDING"


def test_capital_market_assumptions_schema_is_typed() -> None:
    fields = set(CapitalMarketAssumptionsResponse.model_fields)

    assert {
        "methodology_version",
        "risk_free_rate_used",
        "investment_horizon_years",
        "assumptions",
        "warnings",
    }.issubset(fields)


def test_portfolio_risk_inputs_schema_is_typed() -> None:
    fields = set(PortfolioRiskInputsResponse.model_fields)

    assert {
        "methodology_version",
        "risk_model_type",
        "lookback_days",
        "risk_free_rate_used",
        "tickers_used",
        "asset_risk_inputs",
        "covariance_matrix",
        "correlation_matrix",
        "risk_budget",
        "governance_summary",
    }.issubset(fields)


def test_allocator_request_accepts_compatibility_aliases() -> None:
    request = AllocationRecommendationRequest(
        amount=100_000,
        base_currency="usd",
        risk_aversion=0.65,
        investment_horizon=5,
        liquidity_needs="medium",
        objective_type="balanced",
        tickers=["AAPL", "MSFT"],
    )

    assert request.investment_horizon_years == 5
    assert request.candidate_tickers == ["AAPL", "MSFT"]


def test_allocator_task_is_registered_in_celery_app() -> None:
    includes = set(celery_app.conf.include)
    assert "app.workers.tasks.allocator_task" in includes
