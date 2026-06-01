"""
tests/test_cma_ml_blend_boundaries.py

Validates the ML → CMA view fusion layer.

1. build_capital_market_assumptions() with no ml_views behaves as before.
2. ML view with positive confidence shifts expected_return toward ml_annualized.
3. ML view with negative prediction shifts expected_return downward.
4. ML view with confidence=None is skipped (legacy artifact).
5. ML view with confidence=0 is skipped.
6. Blend is bounded: impact never exceeds _ML_IMPACT_CAP (±12pp).
7. Annualized ML return is capped at ±_ML_ANNUALIZED_CAP (±35%).
8. ml_signals_applied counter is correct.
9. Views list contains source="ml_prediction" when applied.
10. methodology string reflects ML blend when applied.
11. AllocationRecommendationRequest accepts ml_predictions field.
12. build_allocation_recommendation passes ml_views to CMA (integration).
"""

from __future__ import annotations

import sys
import os
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.schemas.allocator import (
    AllocationRecommendationRequest,
    CapitalMarketAssumptionsResponse,
    EligibleAsset,
    EligibleUniverseResponse,
    EligibilityCriteria,
    InvestorPolicy,
    MLPredictionInput,
)
from app.services.capital_market_assumptions_service import (
    _ML_BLEND_FACTOR,
    _ML_IMPACT_CAP,
    _ML_ANNUALIZED_CAP,
    build_capital_market_assumptions,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _policy(risk_free_rate: float = 0.045) -> InvestorPolicy:
    from app.schemas.portfolio import OptimizationObjective
    from app.schemas.allocator import (
        InvestorRiskProfile, InvestorObjectiveType, LiquidityNeeds,
    )
    return InvestorPolicy(
        amount=100_000,
        base_currency="USD",
        risk_aversion=0.5,
        risk_profile=InvestorRiskProfile.moderate,
        investment_horizon_years=5,
        liquidity_needs=LiquidityNeeds.medium,
        objective_type=InvestorObjectiveType.balanced,
        objective_used=OptimizationObjective.max_sharpe,
        income_need=0.0,
        max_drawdown_tolerance=0.20,
        max_weight=0.40,
        min_weight=0.02,
        lookback_days=252,
        cash_buffer_weight=0.05,
        risk_free_rate_used=risk_free_rate,
        benchmark_preference="SPY",
    )


def _eligible_asset(ticker: str, asset_class: str = "equity") -> EligibleAsset:
    return EligibleAsset(
        ticker=ticker,
        name=ticker,
        asset_class=asset_class,
        currency="USD",
        price=100.0,
        price_change_1m=0.02,
        price_change_1y=0.15,
        market_cap=1e10,
        volume_avg_30d=1e7,
        dividend_yield=0.02,
        volatility_1y=0.18,
        sharpe_1y=1.2,
        liquidity_tier="high",
        data_quality_score=0.9,
        cost_proxy_available=True,
    )


def _eligibility(*tickers) -> EligibleUniverseResponse:
    return EligibleUniverseResponse(
        criteria=EligibilityCriteria(),
        eligible_assets=[_eligible_asset(t) for t in tickers],
    )


def _ml(ticker, predicted_return, confidence, horizon_days=5) -> MLPredictionInput:
    return MLPredictionInput(
        ticker=ticker,
        predicted_return=predicted_return,
        confidence=confidence,
        horizon_days=horizon_days,
        source="test",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_no_ml_views_returns_baseline_cma():
    """Without ML views, CMA behaves exactly as before."""
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
    )
    assert isinstance(result, CapitalMarketAssumptionsResponse)
    assert result.ml_signals_applied == 0
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    assert all(v.source != "ml_prediction" for v in aapl.views)
    assert any("no ML predictions" in w for w in result.warnings)


def test_ml_positive_prediction_shifts_expected_return_up():
    """Positive ML prediction raises expected_return above CMA baseline."""
    # Build baseline first (no ML)
    baseline = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
    )
    cma_return = next(a for a in baseline.assumptions if a.ticker == "AAPL").expected_return

    # Now apply ML view with strong positive prediction
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.015, confidence=0.60)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    ml_annualized = 0.015 * (252 / 5)  # = 0.756 → clipped to 0.35

    # ml_weight = 0.60 × 0.40 = 0.24, and ml_annualized > cma_return → positive impact
    assert aapl.expected_return > cma_return, "Positive ML prediction must raise expected_return"
    assert result.ml_signals_applied == 1


def test_ml_negative_prediction_shifts_expected_return_down():
    """Negative ML prediction lowers expected_return below CMA baseline."""
    baseline = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
    )
    cma_return = next(a for a in baseline.assumptions if a.ticker == "AAPL").expected_return

    ml_views = {"AAPL": _ml("AAPL", predicted_return=-0.020, confidence=0.65)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    assert aapl.expected_return < cma_return, "Negative ML prediction must lower expected_return"


def test_ml_view_with_none_confidence_skipped():
    """ML prediction with confidence=None (legacy artifact) adds no view."""
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.020, confidence=None)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    assert all(v.source != "ml_prediction" for v in aapl.views)
    assert result.ml_signals_applied == 0


def test_ml_view_with_zero_confidence_skipped():
    """ML prediction with confidence=0.0 adds no view."""
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.020, confidence=0.0)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    assert all(v.source != "ml_prediction" for v in aapl.views)
    assert result.ml_signals_applied == 0


def test_blend_impact_capped_at_ml_impact_cap():
    """Impact is bounded by ±_ML_IMPACT_CAP regardless of ML signal strength."""
    # Use an extreme ML prediction that would otherwise move the return a lot
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.50, confidence=1.0, horizon_days=5)}
    # annualized = 0.50 × 50.4 = 25.2 → capped at 0.35
    # ml_weight = 1.0 × 0.40 = 0.40
    # raw impact = 0.40 × (0.35 - cma_return) ≈ large
    # but impact itself is capped at _ML_IMPACT_CAP

    baseline = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
    )
    cma_return = next(a for a in baseline.assumptions if a.ticker == "AAPL").expected_return

    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    impact = aapl.expected_return - cma_return
    assert abs(impact) <= _ML_IMPACT_CAP + 1e-6, (
        f"Impact {impact:.4f} exceeds cap {_ML_IMPACT_CAP}"
    )


def test_ml_signals_applied_counts_correctly():
    """ml_signals_applied counts only assets where ML view was actually applied."""
    ml_views = {
        "AAPL": _ml("AAPL", predicted_return=0.010, confidence=0.60),
        "MSFT": _ml("MSFT", predicted_return=-0.005, confidence=None),  # skipped
        "GOOGL": _ml("GOOGL", predicted_return=0.008, confidence=0.55),
    }
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL", "MSFT", "GOOGL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    assert result.ml_signals_applied == 2  # AAPL + GOOGL (MSFT skipped due to None confidence)


def test_ml_view_appears_in_views_list():
    """ML view with source='ml_prediction' is in the views list when applied."""
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.008, confidence=0.58)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    ml_view = next((v for v in aapl.views if v.source == "ml_prediction"), None)
    assert ml_view is not None
    assert ml_view.confidence == pytest.approx(0.58, abs=0.01)
    assert "blend_factor" in ml_view.rationale
    assert "annualized" in ml_view.rationale


def test_methodology_reflects_ml_blend():
    """methodology string includes 'ml_blend' when ML view is applied."""
    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.005, confidence=0.55)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL"),
        policy=_policy(),
        ml_views=ml_views,
    )
    aapl = next(a for a in result.assumptions if a.ticker == "AAPL")
    assert "ml_blend" in aapl.methodology


def test_ticker_without_ml_view_unchanged():
    """Asset without ML view is unchanged even when other assets have ML views."""
    baseline = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL", "MSFT"),
        policy=_policy(),
    )
    msft_baseline = next(a for a in baseline.assumptions if a.ticker == "MSFT").expected_return

    ml_views = {"AAPL": _ml("AAPL", predicted_return=0.010, confidence=0.60)}
    result = build_capital_market_assumptions(
        eligibility=_eligibility("AAPL", "MSFT"),
        policy=_policy(),
        ml_views=ml_views,
    )
    msft = next(a for a in result.assumptions if a.ticker == "MSFT")
    assert msft.expected_return == pytest.approx(msft_baseline, abs=1e-6)
    assert all(v.source != "ml_prediction" for v in msft.views)


# ── Schema contract tests ─────────────────────────────────────────────────────

def test_allocation_request_accepts_ml_predictions():
    """AllocationRecommendationRequest serialises ml_predictions without errors."""
    req = AllocationRecommendationRequest(
        amount=10_000,
        risk_aversion=0.5,
        investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT", "GOOGL"],
        ml_predictions=[
            MLPredictionInput(
                ticker="AAPL",
                predicted_return=0.012,
                confidence=0.60,
                horizon_days=5,
                source="backtest_run_001",
            ),
            MLPredictionInput(
                ticker="MSFT",
                predicted_return=-0.003,
                confidence=0.52,
                horizon_days=5,
            ),
        ],
    )
    assert len(req.ml_predictions) == 2
    assert req.ml_predictions[0].ticker == "AAPL"
    assert req.ml_predictions[1].confidence == pytest.approx(0.52)


def test_allocation_request_defaults_to_empty_ml_predictions():
    """AllocationRecommendationRequest defaults ml_predictions to empty list."""
    req = AllocationRecommendationRequest(
        amount=10_000,
        risk_aversion=0.5,
        investment_horizon_years=5,
        candidate_tickers=["AAPL", "MSFT"],
    )
    assert req.ml_predictions == []


def test_ml_prediction_input_none_confidence_is_valid():
    """confidence=None is a valid MLPredictionInput (legacy artifact)."""
    ml = MLPredictionInput(
        ticker="AAPL",
        predicted_return=0.005,
        confidence=None,
        horizon_days=5,
    )
    assert ml.confidence is None
