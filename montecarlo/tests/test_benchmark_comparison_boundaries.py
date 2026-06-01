"""
tests/test_benchmark_comparison_boundaries.py

Boundary tests for the BenchmarkComparison feature (chantier E / PC7.1).

Coverage:
1.  BenchmarkComparison schema fields present (active_return, active_risk, IR, weights, …).
2.  AllocationRecommendationResponse has benchmark_comparison field (optional).
3.  equal_weight → 1/N for every eligible ticker.
4.  60_40 → 60% to equity tickers, 40% to bond tickers.
5.  60_40 fallback to equal_weight when no bond tickers present.
6.  60_40 fallback to equal_weight when no equity tickers present.
7.  acwi → only equity tickers, equal weight.
8.  global_agg → only bond tickers, equal weight.
9.  income_blend → 50% bonds + 30% equity + 20% real_estate (renormalized when a class absent).
10. short_duration_treasuries → bonds + cash tickers equal weight.
11. unknown benchmark_preference → equal_weight fallback.
12. _portfolio_stats_from_weights: expected_return (%) correct formula.
13. _portfolio_stats_from_weights: zero covariance → vol = 0, sharpe = 0.
14. active_return = recommended_er - benchmark_er.
15. active_risk (tracking error) is non-negative.
16. information_ratio = active_return / active_risk when active_risk > 0.
17. information_ratio is None when active_risk is None or zero.
18. BenchmarkComparison returns None when eligible_tickers is empty.
19. benchmark_weights sum to ≈ 1.0 for each benchmark type.
20. method field describes how weights were derived.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import (
    AllocationRecommendationResponse,
    AssetCapitalMarketAssumption,
    BenchmarkComparison,
)
from app.services.allocation_recommendation_service import (
    _benchmark_weights,
    _build_benchmark_comparison,
    _portfolio_stats_from_weights,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assumption(ticker: str, expected_return: float) -> AssetCapitalMarketAssumption:
    return AssetCapitalMarketAssumption(
        ticker=ticker,
        name=ticker,
        asset_class="equity",
        baseline_expected_return=expected_return,
        expected_return=expected_return,
        confidence=0.5,
        methodology="test",
    )


def _simple_cov(tickers: list[str], vol: float = 0.15) -> dict[str, dict[str, float]]:
    """Diagonal covariance matrix (fraction² units, annualized)."""
    return {t: {t2: vol ** 2 if t == t2 else 0.0 for t2 in tickers} for t in tickers}


# ── 1. Schema fields ──────────────────────────────────────────────────────────

def test_benchmark_comparison_schema_has_required_fields() -> None:
    fields = BenchmarkComparison.model_fields
    for f in (
        "benchmark_name", "benchmark_weights",
        "benchmark_expected_return", "benchmark_expected_volatility", "benchmark_sharpe_ratio",
        "recommended_expected_return", "recommended_expected_volatility",
        "active_return", "active_risk", "information_ratio", "method",
    ):
        assert f in fields, f"Missing field: {f}"


# ── 2. AllocationRecommendationResponse contract ─────────────────────────────

def test_allocation_recommendation_response_has_benchmark_comparison_field() -> None:
    fields = AllocationRecommendationResponse.model_fields
    assert "benchmark_comparison" in fields
    assert fields["benchmark_comparison"].default is None


# ── 3. equal_weight ───────────────────────────────────────────────────────────

def test_equal_weight_distributes_uniformly() -> None:
    tickers = ["AAPL", "MSFT", "TLT"]
    weights, method = _benchmark_weights(
        benchmark_preference="equal_weight",
        eligible_tickers=tickers,
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity", "TLT": "fixed_income"},
    )
    assert set(weights.keys()) == set(tickers)
    for t in tickers:
        assert weights[t] == pytest.approx(1 / 3, abs=1e-6)
    assert "equal_weight" in method


# ── 4. 60_40 split ───────────────────────────────────────────────────────────

def test_60_40_assigns_correct_class_weights() -> None:
    tickers = ["AAPL", "MSFT", "TLT", "IEF"]
    ac = {"AAPL": "equity", "MSFT": "equity", "TLT": "fixed_income", "IEF": "fixed_income"}
    weights, _ = _benchmark_weights(
        benchmark_preference="60_40",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    equity_total = weights["AAPL"] + weights["MSFT"]
    bond_total = weights["TLT"] + weights["IEF"]
    assert equity_total == pytest.approx(0.60, abs=1e-4)
    assert bond_total == pytest.approx(0.40, abs=1e-4)
    # Equal within class
    assert weights["AAPL"] == pytest.approx(weights["MSFT"], abs=1e-6)
    assert weights["TLT"] == pytest.approx(weights["IEF"], abs=1e-6)


# ── 5-6. 60_40 fallbacks ──────────────────────────────────────────────────────

def test_60_40_falls_back_when_no_bonds() -> None:
    """Without bond tickers, 60/40 cannot be constructed → equal_weight fallback."""
    tickers = ["AAPL", "MSFT"]
    weights, method = _benchmark_weights(
        benchmark_preference="60_40",
        eligible_tickers=tickers,
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity"},
    )
    assert set(weights.keys()) == set(tickers)
    assert "fallback" in method.lower() or "equal" in method.lower()


def test_60_40_falls_back_when_no_equity() -> None:
    """Without equity tickers, 60/40 cannot be constructed → equal_weight fallback."""
    tickers = ["TLT", "IEF"]
    weights, method = _benchmark_weights(
        benchmark_preference="60_40",
        eligible_tickers=tickers,
        asset_class_by_ticker={"TLT": "fixed_income", "IEF": "fixed_income"},
    )
    assert "fallback" in method.lower() or "equal" in method.lower()


# ── 7. acwi ───────────────────────────────────────────────────────────────────

def test_acwi_includes_only_equity_tickers() -> None:
    tickers = ["AAPL", "MSFT", "TLT"]
    ac = {"AAPL": "equity", "MSFT": "equity", "TLT": "fixed_income"}
    weights, method = _benchmark_weights(
        benchmark_preference="acwi",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert "TLT" not in weights
    assert set(weights.keys()) == {"AAPL", "MSFT"}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)


# ── 8. global_agg ────────────────────────────────────────────────────────────

def test_global_agg_includes_only_bond_tickers() -> None:
    tickers = ["AAPL", "TLT", "IEF"]
    ac = {"AAPL": "equity", "TLT": "fixed_income", "IEF": "fixed_income"}
    weights, method = _benchmark_weights(
        benchmark_preference="global_agg",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert "AAPL" not in weights
    assert set(weights.keys()) == {"TLT", "IEF"}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)


# ── 9. income_blend ──────────────────────────────────────────────────────────

def test_income_blend_uses_class_proportions() -> None:
    tickers = ["AAPL", "TLT", "VNQ"]
    ac = {"AAPL": "equity", "TLT": "fixed_income", "VNQ": "real_estate"}
    weights, method = _benchmark_weights(
        benchmark_preference="income_blend",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)
    # Bonds > Equity > Real Estate (50/30/20)
    assert weights["TLT"] > weights["AAPL"] > weights["VNQ"]


def test_income_blend_renormalizes_when_class_absent() -> None:
    """Without real_estate tickers, bonds (50) + equity (30) → renormalize to 1.0."""
    tickers = ["AAPL", "TLT"]
    ac = {"AAPL": "equity", "TLT": "fixed_income"}
    weights, method = _benchmark_weights(
        benchmark_preference="income_blend",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)


# ── 10. short_duration_treasuries ────────────────────────────────────────────

def test_short_duration_treasuries_includes_bonds_and_cash() -> None:
    tickers = ["AAPL", "TLT", "CASH"]
    ac = {"AAPL": "equity", "TLT": "fixed_income", "CASH": "cash"}
    weights, _ = _benchmark_weights(
        benchmark_preference="short_duration_treasuries",
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert "AAPL" not in weights
    assert "TLT" in weights
    assert "CASH" in weights
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)


# ── 11. Unknown preference ───────────────────────────────────────────────────

def test_unknown_benchmark_preference_falls_back_to_equal_weight() -> None:
    tickers = ["AAPL", "MSFT"]
    weights, method = _benchmark_weights(
        benchmark_preference="nonexistent_benchmark",
        eligible_tickers=tickers,
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity"},
    )
    for t in tickers:
        assert weights[t] == pytest.approx(0.5, abs=1e-6)
    assert "equal_weight" in method.lower()


# ── 12. _portfolio_stats_from_weights expected return formula ─────────────────

def test_portfolio_stats_expected_return_is_weighted_average_pct() -> None:
    """expected_return = Σ(w_i × er_i) × 100."""
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),  # 10%
        "TLT": _assumption("TLT", 0.04),    # 4%
    }
    cov = _simple_cov(["AAPL", "TLT"])
    er, vol, sharpe = _portfolio_stats_from_weights(
        {"AAPL": 0.6, "TLT": 0.4},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        risk_free_rate=0.03,
    )
    expected_er = (0.6 * 0.10 + 0.4 * 0.04) * 100  # = 7.6%
    assert er == pytest.approx(expected_er, abs=1e-4)


# ── 13. Zero covariance ───────────────────────────────────────────────────────

def test_portfolio_stats_zero_cov_returns_zero_vol() -> None:
    assumptions = {"AAPL": _assumption("AAPL", 0.08), "MSFT": _assumption("MSFT", 0.09)}
    zero_cov = {"AAPL": {"AAPL": 0.0, "MSFT": 0.0}, "MSFT": {"AAPL": 0.0, "MSFT": 0.0}}
    er, vol, sharpe = _portfolio_stats_from_weights(
        {"AAPL": 0.5, "MSFT": 0.5},
        assumptions_by_ticker=assumptions,
        covariance_matrix=zero_cov,
        risk_free_rate=0.03,
    )
    assert vol == pytest.approx(0.0, abs=1e-6)
    assert sharpe == pytest.approx(0.0, abs=1e-6)


# ── 14. active_return formula ────────────────────────────────────────────────

def test_active_return_equals_rec_minus_bm() -> None:
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),
        "TLT": _assumption("TLT", 0.04),
    }
    cov = _simple_cov(["AAPL", "TLT"])
    result = _build_benchmark_comparison(
        benchmark_preference="equal_weight",
        eligible_tickers=["AAPL", "TLT"],
        asset_class_by_ticker={"AAPL": "equity", "TLT": "fixed_income"},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        recommended_weights={"AAPL": 0.8, "TLT": 0.2},
        recommended_expected_return=8.4,  # percent
        recommended_expected_volatility=14.0,
        risk_free_rate=0.03,
    )
    assert result is not None
    # benchmark = 50% AAPL + 50% TLT → er = (0.5×0.10 + 0.5×0.04)×100 = 7.0%
    expected_active_return = 8.4 - (0.5 * 0.10 + 0.5 * 0.04) * 100
    assert result.active_return == pytest.approx(expected_active_return, abs=1e-3)


# ── 15. active_risk is non-negative ──────────────────────────────────────────

def test_active_risk_is_non_negative() -> None:
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),
        "TLT": _assumption("TLT", 0.04),
    }
    cov = _simple_cov(["AAPL", "TLT"])
    result = _build_benchmark_comparison(
        benchmark_preference="equal_weight",
        eligible_tickers=["AAPL", "TLT"],
        asset_class_by_ticker={"AAPL": "equity", "TLT": "fixed_income"},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        recommended_weights={"AAPL": 0.7, "TLT": 0.3},
        recommended_expected_return=8.2,
        recommended_expected_volatility=13.5,
        risk_free_rate=0.03,
    )
    assert result is not None
    if result.active_risk is not None:
        assert result.active_risk >= 0.0


# ── 16. information_ratio formula ────────────────────────────────────────────

def test_information_ratio_equals_active_return_over_active_risk() -> None:
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),
        "TLT": _assumption("TLT", 0.04),
    }
    cov = _simple_cov(["AAPL", "TLT"], vol=0.20)
    result = _build_benchmark_comparison(
        benchmark_preference="equal_weight",
        eligible_tickers=["AAPL", "TLT"],
        asset_class_by_ticker={"AAPL": "equity", "TLT": "fixed_income"},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        recommended_weights={"AAPL": 0.9, "TLT": 0.1},
        recommended_expected_return=9.6,
        recommended_expected_volatility=18.0,
        risk_free_rate=0.03,
    )
    assert result is not None
    if result.information_ratio is not None and result.active_risk is not None and result.active_risk > 0:
        assert result.information_ratio == pytest.approx(
            result.active_return / result.active_risk, abs=1e-4
        )


# ── 17. IR is None when active_risk is zero ───────────────────────────────────

def test_information_ratio_is_none_when_active_risk_is_zero() -> None:
    """When rec weights == benchmark weights, active risk = 0 → IR = None."""
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),
        "TLT": _assumption("TLT", 0.04),
    }
    cov = _simple_cov(["AAPL", "TLT"])
    result = _build_benchmark_comparison(
        benchmark_preference="equal_weight",
        eligible_tickers=["AAPL", "TLT"],
        asset_class_by_ticker={"AAPL": "equity", "TLT": "fixed_income"},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        # Recommended weights = equal_weight → active = 0 → TE ≈ 0
        recommended_weights={"AAPL": 0.5, "TLT": 0.5},
        recommended_expected_return=7.0,
        recommended_expected_volatility=11.0,
        risk_free_rate=0.03,
    )
    assert result is not None
    assert result.active_risk == pytest.approx(0.0, abs=1e-6)
    assert result.information_ratio is None


# ── 18. Empty eligible_tickers → returns None ─────────────────────────────────

def test_build_benchmark_comparison_returns_none_for_empty_universe() -> None:
    result = _build_benchmark_comparison(
        benchmark_preference="equal_weight",
        eligible_tickers=[],
        asset_class_by_ticker={},
        assumptions_by_ticker={},
        covariance_matrix={},
        recommended_weights={},
        recommended_expected_return=8.0,
        recommended_expected_volatility=12.0,
        risk_free_rate=0.03,
    )
    assert result is None


# ── 19. Benchmark weights sum to 1.0 ─────────────────────────────────────────

@pytest.mark.parametrize("pref", [
    "equal_weight", "60_40", "acwi", "global_agg", "income_blend", "short_duration_treasuries",
])
def test_benchmark_weights_sum_to_one(pref: str) -> None:
    tickers = ["AAPL", "MSFT", "TLT", "IEF", "VNQ", "CASH"]
    ac = {
        "AAPL": "equity", "MSFT": "equity",
        "TLT": "fixed_income", "IEF": "fixed_income",
        "VNQ": "real_estate",
        "CASH": "cash",
    }
    weights, _ = _benchmark_weights(
        benchmark_preference=pref,
        eligible_tickers=tickers,
        asset_class_by_ticker=ac,
    )
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-4)


# ── 20. method field ─────────────────────────────────────────────────────────

def test_benchmark_comparison_method_is_non_empty_string() -> None:
    assumptions = {"AAPL": _assumption("AAPL", 0.10), "TLT": _assumption("TLT", 0.04)}
    cov = _simple_cov(["AAPL", "TLT"])
    result = _build_benchmark_comparison(
        benchmark_preference="60_40",
        eligible_tickers=["AAPL", "TLT"],
        asset_class_by_ticker={"AAPL": "equity", "TLT": "fixed_income"},
        assumptions_by_ticker=assumptions,
        covariance_matrix=cov,
        recommended_weights={"AAPL": 0.6, "TLT": 0.4},
        recommended_expected_return=7.6,
        recommended_expected_volatility=12.0,
        risk_free_rate=0.03,
    )
    assert result is not None
    assert isinstance(result.method, str)
    assert len(result.method) > 0
