from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import allocator as allocator_routes
from app.schemas.allocator import (
    AllocationRecommendationResponse,
    CapitalMarketAssumptionsResponse,
    EligibleUniverseResponse,
    PortfolioRiskInputsResponse,
)
from app.services import allocation_recommendation_service, investor_policy_service


def test_allocator_route_stays_thin_and_delegates_to_service() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "allocator.py").read_text(encoding="utf-8")

    assert "run_portfolio_optimization_payload" not in source
    assert "build_allocation_recommendation" in source
    assert "build_capital_market_assumptions" in source
    assert "build_portfolio_risk_inputs" in source
    assert "save_allocation_run_sync" not in source


def test_investor_policy_normalization_produces_canonical_fields() -> None:
    policy = investor_policy_service.build_investor_policy(
        {
            "amount": 100_000,
            "base_currency": "usd",
            "risk_aversion": 0.65,
            "investment_horizon": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "income_need": 0.20,
            "allowed_asset_classes": ["equity", "bond"],
            "exclusions": ["BTC"],
            "max_selected_assets": 3,
            "asset_class_constraints": [
                {"asset_class": "equity", "max_weight": 0.80},
                {"asset_class": "bond", "min_weight": 0.20},
            ],
            "current_positions": [
                {"ticker": "AAPL", "weight": 0.50},
                {"ticker": "MSFT", "weight": 0.25},
            ],
            "max_drawdown_tolerance": 0.15,
            "benchmark_preference": "60_40",
            "tickers": ["AAPL", "MSFT", "TLT"],
        }
    )

    assert policy.amount == 100_000
    assert policy.base_currency == "USD"
    assert policy.risk_aversion == pytest.approx(0.65)
    assert policy.investment_horizon_years == 5
    assert policy.objective_used.value == "risk_parity"
    assert policy.benchmark_preference == "60_40"
    assert policy.excluded_tickers == ["BTC"]
    assert policy.max_selected_assets == 3
    assert len(policy.asset_class_constraints) == 2
    assert policy.current_position_weights["AAPL"] == pytest.approx(0.50)
    assert policy.current_position_weights["MSFT"] == pytest.approx(0.25)


def test_allocation_recommendation_delegates_to_optimizer_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_optimize(**kwargs):
        captured["kwargs"] = kwargs
        return {
            "selected_candidate_id": "risk_parity_assumption_aware",
            "selected_objective": kwargs["selected_objective"],
            "selected_payload": {
                "candidate_id": "risk_parity_assumption_aware",
                "objective": kwargs["selected_objective"],
                "tradeoff_summary": "balanced risk-contribution candidate",
                "weights": [
                    {"ticker": "AAPL", "weight": 0.6, "expected_return": 11.0, "volatility": 20.0},
                    {"ticker": "MSFT", "weight": 0.4, "expected_return": 10.0, "volatility": 18.0},
                ],
                "expected_return": 9.2,
                "expected_volatility": 19.0,
                "sharpe_ratio": 1.15,
                "risk_free_rate_used": 0.03,
                "diversification_ratio": 1.08,
                "efficient_frontier": [],
            },
            "candidates": [
                {
                    "candidate_id": "max_sharpe_assumption_aware",
                    "objective": "max_sharpe",
                    "tradeoff_summary": "best risk-adjusted expected return candidate",
                    "weights": [
                        {"ticker": "AAPL", "weight": 0.7, "expected_return": 11.0, "volatility": 20.0},
                        {"ticker": "MSFT", "weight": 0.3, "expected_return": 10.0, "volatility": 18.0},
                    ],
                    "expected_return": 9.8,
                    "expected_volatility": 21.0,
                    "sharpe_ratio": 1.20,
                    "risk_free_rate_used": 0.03,
                    "diversification_ratio": 1.02,
                    "efficient_frontier": [],
                },
                {
                    "candidate_id": "risk_parity_assumption_aware",
                    "objective": "risk_parity",
                    "tradeoff_summary": "balanced risk-contribution candidate",
                    "weights": [
                        {"ticker": "AAPL", "weight": 0.6, "expected_return": 11.0, "volatility": 20.0},
                        {"ticker": "MSFT", "weight": 0.4, "expected_return": 10.0, "volatility": 18.0},
                    ],
                    "expected_return": 9.2,
                    "expected_volatility": 19.0,
                    "sharpe_ratio": 1.15,
                    "risk_free_rate_used": 0.03,
                    "diversification_ratio": 1.08,
                    "efficient_frontier": [],
                },
                {
                    "candidate_id": "min_variance_assumption_aware",
                    "objective": "min_variance",
                    "tradeoff_summary": "lowest expected volatility candidate",
                    "weights": [
                        {"ticker": "AAPL", "weight": 0.45, "expected_return": 11.0, "volatility": 20.0},
                        {"ticker": "MSFT", "weight": 0.55, "expected_return": 10.0, "volatility": 18.0},
                    ],
                    "expected_return": 8.5,
                    "expected_volatility": 16.0,
                    "sharpe_ratio": 1.05,
                    "risk_free_rate_used": 0.03,
                    "diversification_ratio": 1.12,
                    "efficient_frontier": [],
                },
            ],
            "warnings": [],
        }

    monkeypatch.setattr(
        allocation_recommendation_service,
        "run_allocator_candidate_optimizations_payload",
        _fake_optimize,
    )
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_eligible_universe",
        lambda req, policy: EligibleUniverseResponse(
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
                    "market_cap": 2_800_000_000_000.0,
                    "volume_avg_30d": 50_000_000.0,
                    "liquidity_tier": "deep",
                    "data_quality_score": 1.0,
                    "cost_proxy_available": True,
                    "notes": [],
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corp.",
                    "asset_class": "equity",
                    "currency": "USD",
                    "price": 420.0,
                    "market_cap": 2_500_000_000_000.0,
                    "volume_avg_30d": 30_000_000.0,
                    "liquidity_tier": "deep",
                    "data_quality_score": 1.0,
                    "cost_proxy_available": True,
                    "notes": [],
                },
            ],
            rejected_assets=[
                {
                    "ticker": "BTC",
                    "name": "BTC",
                    "asset_class": "crypto",
                    "currency": "USD",
                    "price": None,
                    "market_cap": None,
                    "volume_avg_30d": None,
                    "liquidity_tier": "unknown",
                    "data_quality_score": 0.0,
                    "cost_proxy_available": False,
                    "notes": ["instrument_not_found"],
                    "rejection_reasons": ["instrument_not_found_in_canonical_universe"],
                }
            ],
            warnings=[],
        ),
    )
    monkeypatch.setattr(
        allocation_recommendation_service,
        "save_allocation_run_sync",
        lambda payload: {"run_id": "run-123", "created_at": "2026-03-24T12:00:00+00:00"},
    )
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_capital_market_assumptions",
        lambda eligibility, policy, ml_views=None: CapitalMarketAssumptionsResponse(
            methodology_version="cma_v1",
            risk_free_rate_used=0.03,
            investment_horizon_years=5,
            assumptions=[
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "asset_class": "equity",
                    "baseline_expected_return": 0.08,
                    "expected_return": 0.11,
                    "confidence": 0.72,
                    "volatility_proxy": 0.2,
                    "methodology": "baseline_risk_free_plus_asset_class_premium_with_light_views_v1",
                    "views": [],
                    "warnings": [],
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corp.",
                    "asset_class": "equity",
                    "baseline_expected_return": 0.08,
                    "expected_return": 0.10,
                    "confidence": 0.68,
                    "volatility_proxy": 0.18,
                    "methodology": "baseline_risk_free_plus_asset_class_premium_with_light_views_v1",
                    "views": [],
                    "warnings": [],
                },
            ],
            warnings=[
                "capital market assumptions v1 are explanatory and preparatory; the legacy optimizer does not yet ingest these views directly"
            ],
        ),
    )
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_portfolio_risk_inputs",
        lambda eligibility, policy: PortfolioRiskInputsResponse(
            methodology_version="portfolio_risk_inputs_v1",
            risk_model_type="historical_covariance_allocator_v1",
            data_source="yfinance",
            lookback_days=policy.lookback_days,
            observation_count=252,
            annualization_factor=252,
            risk_free_rate_used=policy.risk_free_rate_used,
            benchmark_preference=policy.benchmark_preference,
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
            top_correlation_pairs=[
                {
                    "left_ticker": "AAPL",
                    "right_ticker": "MSFT",
                    "correlation": 0.71,
                    "absolute_correlation": 0.71,
                }
            ],
            risk_budget={
                "target_volatility": 0.14,
                "max_drawdown_tolerance": 0.2,
                "max_single_name_weight": 0.35,
                "min_weight": 0.0,
                "cash_buffer_weight": policy.cash_buffer_weight,
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
            warnings=["risk inputs preview warning"],
        ),
    )
    monkeypatch.setattr(
        allocation_recommendation_service,
        "build_candidate_risk_diagnostics",
        lambda candidate_weights, risk_inputs: {
            "portfolio_volatility": 0.15,
            "concentration_hhi": 0.52,
            "effective_number_of_names": 1.92,
            "max_single_name_weight": max(candidate_weights.values()),
            "weighted_drawdown_proxy": 0.22,
            "target_volatility_gap": 0.01,
            "risk_budget_breaches": ["max_single_name_weight", "weighted_drawdown_proxy"],
        },
    )

    result = allocation_recommendation_service.build_allocation_recommendation(
        {
            "amount": 100_000,
            "base_currency": "USD",
            "risk_aversion": 0.65,
            "investment_horizon": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "income_need": 0.10,
            "allowed_asset_classes": ["equity", "bond"],
            "exclusions": ["BTC"],
            "preferred_tickers": ["AAPL"],
            "max_selected_assets": 2,
            "asset_class_constraints": [
                {"asset_class": "equity", "max_weight": 0.80},
                {"asset_class": "bond", "min_weight": 0.20},
            ],
            "current_positions": [
                {"ticker": "AAPL", "weight": 0.50},
                {"ticker": "MSFT", "weight": 0.50},
            ],
            "benchmark_preference": "60_40",
            "tickers": ["AAPL", "MSFT", "BTC"],
        }
    )

    assert isinstance(result, AllocationRecommendationResponse)
    assert captured["kwargs"]["tickers"] == ["AAPL", "MSFT"]
    assert captured["kwargs"]["selected_objective"] == "risk_parity"
    assert captured["kwargs"]["risk_inputs"].methodology_version == "portfolio_risk_inputs_v1"
    assert captured["kwargs"]["max_selected_assets"] == 2
    assert len(captured["kwargs"]["asset_class_constraints"]) == 2
    assert captured["kwargs"]["asset_class_by_ticker"] == {"AAPL": "equity", "MSFT": "equity"}
    assert result.policy.amount == 100_000
    assert result.policy.base_currency == "USD"
    assert result.eligibility.eligible_assets[0].name == "Apple Inc."
    assert result.assumptions.assumptions[0].expected_return == pytest.approx(0.11)
    assert result.risk_inputs.methodology_version == "portfolio_risk_inputs_v1"
    assert result.run_id == "run-123"
    assert result.persistence_status.value == "persisted"
    assert len(result.recommended_assets) == 2
    assert len(result.optimization.candidate_portfolios) == 3
    assert result.optimization.selected_candidate_id == "risk_parity_assumption_aware"
    assert result.optimization.selected_risk_diagnostics is not None
    assert result.optimization.selected_risk_diagnostics.max_single_name_weight == pytest.approx(0.6)
    assert result.optimization.selected_constraint_diagnostics is not None
    assert result.optimization.selected_constraint_diagnostics.max_selected_assets == 2
    assert result.optimization.selected_constraint_diagnostics.turnover_from_current == pytest.approx(0.10)
    assert "max_selected_assets" in result.optimization.selected_constraint_diagnostics.active_constraints
    assert "asset_class:equity" in result.optimization.selected_constraint_diagnostics.active_constraints
    assert "turnover_reporting" in result.optimization.selected_constraint_diagnostics.active_constraints
    assert result.optimization.candidate_portfolios[1].risk_diagnostics is not None
    assert result.optimization.candidate_portfolios[1].constraint_diagnostics is not None
    assert "max_single_name_weight" in result.optimization.candidate_portfolios[1].risk_diagnostics.risk_budget_breaches
    assert result.recommended_assets[0].ticker == "AAPL"
    assert result.recommended_assets[0].name == "Apple Inc."
    assert result.recommended_assets[0].expected_return == pytest.approx(0.11)
    assert result.recommended_assets[0].target_amount == pytest.approx(60_000)
    assert result.rejected_assets[0].ticker == "BTC"
    assert result.rejected_assets[0].stage == "policy"


@pytest.mark.asyncio
async def test_allocator_route_returns_typed_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Loop:
        async def run_in_executor(self, executor, fn, *args):
            return fn(*args)

    monkeypatch.setattr(allocator_routes.asyncio, "get_event_loop", lambda: _Loop())
    monkeypatch.setattr(
        allocator_routes,
        "_recommend_sync",
        lambda req: AllocationRecommendationResponse(
            recommendation_id="rec-123",
            run_id=None,
            persistence_status="inactive",
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
                    "risk_budget_breaches": ["max_single_name_weight"],
                },
                "selected_constraint_diagnostics": {
                    "selected_asset_count": 2,
                    "max_selected_assets": 2,
                    "cardinality_breach": False,
                    "turnover_from_current": 0.10,
                    "asset_class_exposures": [
                        {
                            "asset_class": "equity",
                            "weight": 1.0,
                            "min_weight": None,
                            "max_weight": 0.8,
                            "within_bounds": False,
                        }
                    ],
                    "asset_class_breaches": ["asset_class_max:equity"],
                    "active_constraints": ["max_selected_assets", "asset_class:equity"],
                },
                "candidate_portfolios": [],
                "efficient_frontier": [],
            },
            total_allocated_amount=10_000,
            cash_reserve_amount=0.0,
            warnings=[],
        ),
    )

    response = await allocator_routes.recommend_allocation(
        allocator_routes.AllocationRecommendationRequest(
            amount=10_000,
            base_currency="USD",
            risk_aversion=0.5,
            investment_horizon_years=3,
            liquidity_needs="medium",
            objective_type="balanced",
            candidate_tickers=["AAPL", "MSFT"],
        )
    )

    assert response.data.recommendation_id == "rec-123"
    assert response.data.policy.base_currency == "USD"
    assert response.data.optimization.selected_risk_diagnostics is not None
    assert "max_single_name_weight" in response.data.optimization.selected_risk_diagnostics.risk_budget_breaches


@pytest.mark.asyncio
async def test_allocator_async_route_dispatches_to_celery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Task:
        id = "job-allocator-123"

    class _AllocatorTask:
        @staticmethod
        def delay(**payload):
            assert payload["amount"] == 25_000
            assert payload["candidate_tickers"] == ["AAPL", "MSFT"]
            return _Task()

    fake_module = types.SimpleNamespace(recommend_allocation=_AllocatorTask())
    monkeypatch.setitem(sys.modules, "app.workers.tasks.allocator_task", fake_module)

    response = await allocator_routes.recommend_allocation_async(
        allocator_routes.AllocationRecommendationRequest(
            amount=25_000,
            base_currency="USD",
            risk_aversion=0.4,
            investment_horizon_years=4,
            liquidity_needs="medium",
            objective_type="balanced",
            candidate_tickers=["AAPL", "MSFT"],
        )
    )

    assert response.data.job_id == "job-allocator-123"
    assert response.data.status == "PENDING"


@pytest.mark.asyncio
async def test_allocator_async_route_returns_503_when_celery_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _AllocatorTask:
        @staticmethod
        def delay(**payload):
            raise RuntimeError("broker unavailable")

    fake_module = types.SimpleNamespace(recommend_allocation=_AllocatorTask())
    monkeypatch.setitem(sys.modules, "app.workers.tasks.allocator_task", fake_module)

    with pytest.raises(HTTPException) as exc:
        await allocator_routes.recommend_allocation_async(
            allocator_routes.AllocationRecommendationRequest(
                amount=25_000,
                base_currency="USD",
                risk_aversion=0.4,
                investment_horizon_years=4,
                liquidity_needs="medium",
                objective_type="balanced",
                candidate_tickers=["AAPL", "MSFT"],
            )
        )

    assert exc.value.status_code == 503
    assert "Celery unavailable" in str(exc.value.detail)
