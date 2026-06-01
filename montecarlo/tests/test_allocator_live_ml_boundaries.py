"""
tests/test_allocator_live_ml_boundaries.py

Validates the live-ML → allocator fusion layer introduced in DELTA-20260324-31.

1.  AllocationLiveMLRequest accepts ml_run_ids / ml_horizon_days / ml_price_period.
2.  AllocationLiveMLRequest inherits all AllocationRecommendationRequest fields.
3.  build_live_ml_predictions() returns MLPredictionInput list from PredictionResult.
4.  build_live_ml_predictions() skips tickers whose prediction raises ArtifactNotFoundError.
5.  build_live_ml_predictions() skips tickers whose prediction raises PriceFetchError.
6.  build_live_ml_predictions() skips tickers whose prediction raises unexpected errors.
7.  build_live_ml_predictions() runs predictions concurrently (asyncio.gather).
8.  build_live_ml_predictions() returns empty list + no warnings when ml_run_ids is empty.
9.  Explicit ml_predictions override live-fetched ones for the same ticker (route merge).
10. Route /recommend/with-live-ml calls build_live_ml_predictions when ml_run_ids present.
11. Route /recommend/with-live-ml skips ML fetch when ml_run_ids empty.
12. live_warnings are appended to result.warnings.
13. PredictionResult → MLPredictionInput adapter maps fields correctly.
"""

from __future__ import annotations

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.schemas.allocator import (
    AllocationLiveMLRequest,
    AllocationRecommendationRequest,
    MLPredictionInput,
)
from app.services.allocation_recommendation_service import build_live_ml_predictions
from app.services.ml_service import (
    ArtifactNotFoundError,
    PriceFetchError,
    PredictionExecutionError,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prediction_result(
    asset: str = "AAPL",
    predicted_return: float = 0.012,
    confidence: float | None = 0.61,
    horizon_days: int = 5,
    run_id: str = "run-abc-123",
) -> object:
    from app.schemas.ml import PredictionResult
    return PredictionResult(
        asset=asset,
        predicted_return=predicted_return,
        predicted_direction="up" if predicted_return >= 0 else "down",
        confidence=confidence,
        prediction_date="2026-03-24",
        target_date="2026-03-31",
        horizon_days=horizon_days,
        run_id=run_id,
    )


def _stub_response(warnings: list[str] | None = None):
    """Build a minimal AllocationRecommendationResponse for route stubs."""
    from app.schemas.allocator import (
        AllocationRecommendationResponse, AllocationOptimizationSummary,
        AllocationConstraintSnapshot, InvestorPolicy, InvestorRiskProfile,
        InvestorObjectiveType, LiquidityNeeds, CapitalMarketAssumptionsResponse,
        EligibleUniverseResponse, PortfolioRiskInputsResponse,
    )
    from app.schemas.portfolio import OptimizationObjective
    import uuid
    return AllocationRecommendationResponse(
        recommendation_id=str(uuid.uuid4()), run_id=None, persistence_status="inactive",
        policy=InvestorPolicy(
            amount=10_000, base_currency="USD", risk_aversion=0.5,
            risk_profile=InvestorRiskProfile.moderate, investment_horizon_years=5,
            liquidity_needs=LiquidityNeeds.medium, objective_type=InvestorObjectiveType.balanced,
            objective_used=OptimizationObjective.max_sharpe, income_need=0.0,
            max_drawdown_tolerance=0.20, max_weight=0.40, min_weight=0.02, lookback_days=252,
            cash_buffer_weight=0.05, risk_free_rate_used=0.045, benchmark_preference="SPY",
        ),
        eligibility=EligibleUniverseResponse(criteria={}),
        assumptions=CapitalMarketAssumptionsResponse(
            methodology_version="cma_v1", risk_free_rate_used=0.045, investment_horizon_years=5,
        ),
        risk_inputs=PortfolioRiskInputsResponse(
            methodology_version="v1", risk_model_type="hist", data_source="yfinance",
            lookback_days=252, observation_count=252, annualization_factor=252,
            risk_free_rate_used=0.045, benchmark_preference="SPY",
            risk_budget={"target_volatility": None, "max_drawdown_tolerance": 0.20,
                         "max_single_name_weight": 0.40, "min_weight": 0.02,
                         "cash_buffer_weight": 0.05, "concentration_hhi_soft_limit": 0.18,
                         "effective_name_floor": 5.0},
            universe_risk_diagnostics={"asset_count": 1, "observation_count": 252},
            governance_summary={"model_type": "hist", "covariance_estimator": "ledoit_wolf",
                                "concentration_support": "post_optimization_only",
                                "scenario_support": "deferred", "limitations": []},
        ),
        eligible_tickers=[], recommended_assets=[], rejected_assets=[],
        optimization=AllocationOptimizationSummary(
            objective="max_sharpe", expected_return=0.09, expected_volatility=0.15,
            sharpe_ratio=1.1, risk_free_rate_used=0.045,
            constraint_snapshot=AllocationConstraintSnapshot(
                max_weight=0.40, min_weight=0.02, max_drawdown_tolerance=0.20,
                cash_buffer_weight=0.05, lookback_days=252,
            ),
        ),
        total_allocated_amount=10_000, cash_reserve_amount=0.0,
        warnings=warnings or [],
    )


# ── Schema contract tests ──────────────────────────────────────────────────────

def test_live_ml_request_accepts_ml_run_ids():
    req = AllocationLiveMLRequest(
        amount=50_000,
        risk_aversion=0.5,
        investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT"],
        ml_run_ids={"AAPL": "run-001", "MSFT": "run-002"},
    )
    assert req.ml_run_ids == {"AAPL": "run-001", "MSFT": "run-002"}


def test_live_ml_request_defaults():
    req = AllocationLiveMLRequest(
        amount=10_000,
        risk_aversion=0.4,
        investment_horizon_years=3,
        candidate_tickers=["AAPL", "MSFT"],
    )
    assert req.ml_run_ids == {}
    assert req.ml_horizon_days == 5
    assert req.ml_price_period == "3y"


def test_live_ml_request_is_allocation_request_subclass():
    req = AllocationLiveMLRequest(
        amount=10_000,
        risk_aversion=0.4,
        investment_horizon_years=3,
        candidate_tickers=["AAPL", "MSFT"],
    )
    assert isinstance(req, AllocationRecommendationRequest)


def test_live_ml_request_inherits_ml_predictions():
    req = AllocationLiveMLRequest(
        amount=10_000,
        risk_aversion=0.4,
        investment_horizon_years=3,
        candidate_tickers=["AAPL", "MSFT"],
        ml_predictions=[
            MLPredictionInput(ticker="AAPL", predicted_return=0.005, confidence=0.55)
        ],
    )
    assert len(req.ml_predictions) == 1
    assert req.ml_predictions[0].ticker == "AAPL"


# ── build_live_ml_predictions tests ──────────────────────────────────────────

def test_build_live_ml_predictions_maps_fields_correctly():
    """PredictionResult fields map correctly to MLPredictionInput."""
    pr = _prediction_result(asset="AAPL", predicted_return=0.012, confidence=0.61,
                            horizon_days=5, run_id="run-abc-123")

    async def _run():
        with patch("app.services.ml_service.run_prediction", new=AsyncMock(return_value=pr)):
            return await build_live_ml_predictions(
                {"AAPL": "run-abc-123"}, horizon_days=5, period="3y"
            )

    predictions, warnings = asyncio.run(_run())

    assert len(predictions) == 1
    p = predictions[0]
    assert p.ticker == "AAPL"
    assert p.predicted_return == pytest.approx(0.012)
    assert p.confidence == pytest.approx(0.61)
    assert p.horizon_days == 5
    assert p.source == "ml_run:run-abc-123"
    assert warnings == []


def test_build_live_ml_predictions_skips_artifact_not_found():
    """ArtifactNotFoundError → ticker skipped, warning appended."""
    async def _run():
        with patch(
            "app.services.ml_service.run_prediction",
            new=AsyncMock(side_effect=ArtifactNotFoundError("No artifact for run xyz")),
        ):
            return await build_live_ml_predictions({"AAPL": "run-xyz"}, horizon_days=5, period="3y")

    predictions, warnings = asyncio.run(_run())
    assert predictions == []
    assert len(warnings) == 1
    assert "AAPL" in warnings[0]


def test_build_live_ml_predictions_skips_price_fetch_error():
    """PriceFetchError → ticker skipped, warning appended."""
    async def _run():
        with patch(
            "app.services.ml_service.run_prediction",
            new=AsyncMock(side_effect=PriceFetchError("yfinance timeout")),
        ):
            return await build_live_ml_predictions({"MSFT": "run-msft-001"}, horizon_days=5, period="3y")

    predictions, warnings = asyncio.run(_run())
    assert predictions == []
    assert len(warnings) == 1
    assert "MSFT" in warnings[0]


def test_build_live_ml_predictions_skips_unexpected_error():
    """Unexpected exception → ticker skipped, warning appended."""
    async def _run():
        with patch(
            "app.services.ml_service.run_prediction",
            new=AsyncMock(side_effect=RuntimeError("unexpected")),
        ):
            return await build_live_ml_predictions({"GOOGL": "run-g-001"}, horizon_days=5, period="3y")

    predictions, warnings = asyncio.run(_run())
    assert predictions == []
    assert len(warnings) == 1
    assert "GOOGL" in warnings[0]


def test_build_live_ml_predictions_partial_success():
    """Some tickers succeed, others fail — only successes returned."""
    pr_aapl = _prediction_result(asset="AAPL", predicted_return=0.010, confidence=0.60)

    async def _side_effect(*, asset, run_id, horizon_days, period, executor=None):
        if asset == "AAPL":
            return pr_aapl
        raise ArtifactNotFoundError(f"no artifact for {asset}")

    async def _run():
        with patch("app.services.ml_service.run_prediction", new=AsyncMock(side_effect=_side_effect)):
            return await build_live_ml_predictions(
                {"AAPL": "run-aapl", "MSFT": "run-msft"}, horizon_days=5, period="3y"
            )

    predictions, warnings = asyncio.run(_run())
    assert len(predictions) == 1
    assert predictions[0].ticker == "AAPL"
    assert len(warnings) == 1
    assert "MSFT" in warnings[0]


def test_build_live_ml_predictions_empty_run_ids_returns_empty():
    """Empty ml_run_ids → no predictions, no warnings, no ML calls."""
    async def _run():
        with patch(
            "app.services.ml_service.run_prediction",
            new=AsyncMock(side_effect=AssertionError("should not be called")),
        ):
            return await build_live_ml_predictions({}, horizon_days=5, period="3y")

    predictions, warnings = asyncio.run(_run())
    assert predictions == []
    assert warnings == []


def test_build_live_ml_predictions_uses_asyncio_gather():
    """All tickers dispatched concurrently — all 3 return successfully."""
    call_log: list[str] = []

    async def _side_effect(*, asset, run_id, horizon_days, period, executor=None):
        call_log.append(asset)
        return _prediction_result(asset=asset, predicted_return=0.005, confidence=0.55, run_id=run_id)

    async def _run():
        with patch("app.services.ml_service.run_prediction", new=AsyncMock(side_effect=_side_effect)):
            return await build_live_ml_predictions(
                {"AAPL": "r1", "MSFT": "r2", "GOOGL": "r3"}, horizon_days=5, period="3y"
            )

    predictions, warnings = asyncio.run(_run())
    assert len(predictions) == 3
    assert set(p.ticker for p in predictions) == {"AAPL", "MSFT", "GOOGL"}
    assert warnings == []


# ── Route integration tests ───────────────────────────────────────────────────

def test_route_calls_build_live_ml_when_run_ids_present(monkeypatch):
    """Route calls build_live_ml_predictions when ml_run_ids is non-empty."""
    import app.routes.allocator as allocator_routes

    live_ml_called_with: dict = {}

    async def _fake_live_ml(run_ids, *, horizon_days, period, executor=None):
        live_ml_called_with["run_ids"] = run_ids
        live_ml_called_with["horizon_days"] = horizon_days
        return (
            [MLPredictionInput(ticker="AAPL", predicted_return=0.010, confidence=0.60,
                               horizon_days=horizon_days, source="ml_run:run-001")],
            [],
        )

    monkeypatch.setattr(allocator_routes, "build_live_ml_predictions", _fake_live_ml)

    captured_req: dict = {}

    def _fake_recommend_sync(req):
        captured_req["ml_predictions"] = list(req.ml_predictions)
        return _stub_response()

    monkeypatch.setattr(allocator_routes, "_recommend_sync", _fake_recommend_sync)

    req = AllocationLiveMLRequest(
        amount=10_000, risk_aversion=0.5, investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT"],
        ml_run_ids={"AAPL": "run-001"},
        ml_horizon_days=5,
    )

    asyncio.run(allocator_routes.recommend_allocation_with_live_ml(req))

    assert live_ml_called_with["run_ids"] == {"AAPL": "run-001"}
    assert live_ml_called_with["horizon_days"] == 5
    assert len(captured_req["ml_predictions"]) == 1
    assert captured_req["ml_predictions"][0].ticker == "AAPL"


def test_route_skips_live_ml_when_run_ids_empty(monkeypatch):
    """Route does NOT call build_live_ml_predictions when ml_run_ids is empty."""
    import app.routes.allocator as allocator_routes

    async def _should_not_be_called(*args, **kwargs):
        raise AssertionError("build_live_ml_predictions must not be called with empty ml_run_ids")

    monkeypatch.setattr(allocator_routes, "build_live_ml_predictions", _should_not_be_called)

    captured_req: dict = {}

    def _fake_recommend_sync(req):
        captured_req["ml_predictions"] = list(req.ml_predictions)
        return _stub_response()

    monkeypatch.setattr(allocator_routes, "_recommend_sync", _fake_recommend_sync)

    req = AllocationLiveMLRequest(
        amount=10_000, risk_aversion=0.5, investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT"],
        # ml_run_ids intentionally empty
    )

    asyncio.run(allocator_routes.recommend_allocation_with_live_ml(req))
    assert captured_req["ml_predictions"] == []


def test_route_explicit_ml_overrides_live_fetched(monkeypatch):
    """Explicit ml_predictions entry for AAPL wins over live-fetched AAPL prediction."""
    import app.routes.allocator as allocator_routes

    async def _fake_live_ml(run_ids, *, horizon_days, period, executor=None):
        return (
            [MLPredictionInput(ticker="AAPL", predicted_return=0.999, confidence=0.99,
                               horizon_days=5, source="live")],
            [],
        )

    monkeypatch.setattr(allocator_routes, "build_live_ml_predictions", _fake_live_ml)

    captured_req: dict = {}

    def _fake_recommend_sync(req):
        captured_req["ml_predictions"] = list(req.ml_predictions)
        return _stub_response()

    monkeypatch.setattr(allocator_routes, "_recommend_sync", _fake_recommend_sync)

    explicit_pred = MLPredictionInput(
        ticker="AAPL", predicted_return=0.012, confidence=0.60,
        horizon_days=5, source="explicit"
    )
    req = AllocationLiveMLRequest(
        amount=10_000, risk_aversion=0.5, investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT"],
        ml_predictions=[explicit_pred],
        ml_run_ids={"AAPL": "run-001"},
    )

    asyncio.run(allocator_routes.recommend_allocation_with_live_ml(req))

    aapl_preds = [p for p in captured_req["ml_predictions"] if p.ticker == "AAPL"]
    assert len(aapl_preds) == 1
    assert aapl_preds[0].predicted_return == pytest.approx(0.012)
    assert aapl_preds[0].source == "explicit"


def test_route_live_warnings_appended_to_result(monkeypatch):
    """Live ML fetch warnings are appended to result.warnings."""
    import app.routes.allocator as allocator_routes

    async def _fake_live_ml(run_ids, *, horizon_days, period, executor=None):
        return ([], ["live ML prediction skipped for MSFT: No artifact found for run xyz"])

    monkeypatch.setattr(allocator_routes, "build_live_ml_predictions", _fake_live_ml)

    def _fake_recommend_sync(req):
        return _stub_response(warnings=["base warning"])

    monkeypatch.setattr(allocator_routes, "_recommend_sync", _fake_recommend_sync)

    req = AllocationLiveMLRequest(
        amount=10_000, risk_aversion=0.5, investment_horizon_years=5,
        candidate_tickers=["MSFT", "AAPL"],
        ml_run_ids={"MSFT": "run-xyz"},
    )

    response = asyncio.run(allocator_routes.recommend_allocation_with_live_ml(req))
    assert any("MSFT" in w for w in response.data.warnings)
    assert "base warning" in response.data.warnings
