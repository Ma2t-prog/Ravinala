"""
tests/test_tier2_portfolio_features_boundaries.py

Boundary tests for the three Tier-2 portfolio features:
  - PC2.4  SleeveBreakdown  (sleeve architecture)
  - PC6.4  AllocationAlternatives  (near-alternative portfolios)
  - PC4.4  StressTestSummary  (stress / scenario layer)

Coverage (30 tests):
── PC2.4 Sleeves (10 tests) ─────────────────────────────────────────
 1. SleeveBreakdown schema has sleeves, method fields.
 2. PortfolioSleeve schema has sleeve_name, label, tickers, total_weight.
 3. equity asset with role=core → core_beta sleeve.
 4. equity asset with role=satellite → satellite sleeve.
 5. fixed_income asset → fixed_income sleeve.
 6. commodity / real_estate / crypto → alternatives sleeve.
 7. cash → cash sleeve.
 8. sleeve total_weight sums are correct.
 9. sleeve_expected_return is weight-averaged CMA return (%).
10. AllocationRecommendationResponse has sleeve_breakdown field.

── PC6.4 Alternatives (10 tests) ────────────────────────────────────
11. AllocationAlternatives schema fields present.
12. AlternativeAllocation schema fields present.
13. Selected candidate excluded from alternatives.
14. Non-selected candidates all present.
15. min_variance candidate gets label "More Defensive".
16. max_sharpe candidate gets label containing "Return" or "Adjusted".
17. return_diff = candidate_er − recommended_er.
18. volatility_diff = candidate_vol − recommended_vol.
19. Alternatives sorted by sharpe_ratio descending.
20. AllocationRecommendationResponse has alternatives field.

── PC4.4 Stress tests (10 tests) ────────────────────────────────────
21. StressTestSummary schema fields present.
22. StressScenarioResult schema fields present.
23. Four built-in scenarios: equity_crash, rate_shock, inflation_spike, stagflation.
24. portfolio_impact = Σ(w_i × shock_i) correct formula.
25. stressed_value = 1 + portfolio_impact.
26. equity_crash produces negative portfolio_impact for equity-only portfolio.
27. inflation_spike: commodity outperforms → positive impact for commodity portfolio.
28. worst_scenario_name is the scenario with the lowest portfolio_impact.
29. largest_detractor is the ticker with most negative contribution.
30. AllocationRecommendationResponse has stress_tests field.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import (
    AllocationAlternatives,
    AllocationRecommendationResponse,
    AlternativeAllocation,
    AssetCapitalMarketAssumption,
    PortfolioSleeve,
    RecommendedAsset,
    SleeveBreakdown,
    StressScenarioResult,
    StressTestSummary,
)
from app.services.allocation_recommendation_service import (
    _build_alternatives,
    _build_sleeve_breakdown,
    _build_stress_tests,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _asset(ticker: str, weight: float, role: str = "core") -> RecommendedAsset:
    return RecommendedAsset(
        ticker=ticker,
        name=ticker,
        target_weight=weight,
        target_amount=weight * 100_000,
        role=role,
        selection_reason="test",
    )


def _assumption(ticker: str, er: float = 0.08) -> AssetCapitalMarketAssumption:
    return AssetCapitalMarketAssumption(
        ticker=ticker,
        name=ticker,
        asset_class="equity",
        baseline_expected_return=er,
        expected_return=er,
        confidence=0.5,
        methodology="test",
    )


def _candidate(cid: str, er: float, vol: float, sharpe: float, selected: bool = False) -> dict:
    return {
        "candidate_id": cid,
        "objective": cid.split("_")[0],
        "expected_return": er,
        "expected_volatility": vol,
        "sharpe_ratio": sharpe,
        "tradeoff_summary": f"{cid} summary",
        "weights": [
            {"ticker": "AAPL", "weight": 0.6},
            {"ticker": "TLT", "weight": 0.4},
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# PC2.4 — SLEEVE BREAKDOWN
# ═══════════════════════════════════════════════════════════════════

def test_sleeve_breakdown_schema_fields() -> None:
    """SleeveBreakdown must have sleeves and method fields."""
    fields = SleeveBreakdown.model_fields
    assert "sleeves" in fields
    assert "method" in fields


def test_portfolio_sleeve_schema_fields() -> None:
    """PortfolioSleeve must have sleeve_name, label, tickers, total_weight."""
    fields = PortfolioSleeve.model_fields
    for f in ("sleeve_name", "label", "tickers", "total_weight"):
        assert f in fields


def test_equity_core_role_maps_to_core_beta() -> None:
    result = _build_sleeve_breakdown(
        recommended_assets=[_asset("AAPL", 0.6, role="core")],
        asset_class_by_ticker={"AAPL": "equity"},
        assumptions_by_ticker={"AAPL": _assumption("AAPL")},
    )
    names = {s.sleeve_name for s in result.sleeves}
    assert "core_beta" in names
    core = next(s for s in result.sleeves if s.sleeve_name == "core_beta")
    assert "AAPL" in core.tickers


def test_equity_satellite_role_maps_to_satellite() -> None:
    result = _build_sleeve_breakdown(
        recommended_assets=[_asset("NVDA", 0.3, role="satellite")],
        asset_class_by_ticker={"NVDA": "equity"},
        assumptions_by_ticker={"NVDA": _assumption("NVDA")},
    )
    names = {s.sleeve_name for s in result.sleeves}
    assert "satellite" in names


def test_fixed_income_maps_to_fixed_income_sleeve() -> None:
    result = _build_sleeve_breakdown(
        recommended_assets=[_asset("TLT", 0.4)],
        asset_class_by_ticker={"TLT": "fixed_income"},
        assumptions_by_ticker={"TLT": _assumption("TLT", 0.04)},
    )
    names = {s.sleeve_name for s in result.sleeves}
    assert "fixed_income" in names


def test_commodity_and_real_estate_map_to_alternatives() -> None:
    assets = [_asset("GLD", 0.1), _asset("VNQ", 0.1)]
    ac = {"GLD": "commodity", "VNQ": "real_estate"}
    result = _build_sleeve_breakdown(
        recommended_assets=assets,
        asset_class_by_ticker=ac,
        assumptions_by_ticker={t: _assumption(t) for t in ["GLD", "VNQ"]},
    )
    names = {s.sleeve_name for s in result.sleeves}
    assert "alternatives" in names
    alts = next(s for s in result.sleeves if s.sleeve_name == "alternatives")
    assert set(alts.tickers) == {"GLD", "VNQ"}


def test_cash_maps_to_cash_sleeve() -> None:
    result = _build_sleeve_breakdown(
        recommended_assets=[_asset("CASH", 0.05)],
        asset_class_by_ticker={"CASH": "cash"},
        assumptions_by_ticker={"CASH": _assumption("CASH", 0.01)},
    )
    names = {s.sleeve_name for s in result.sleeves}
    assert "cash" in names


def test_sleeve_total_weights_are_correct() -> None:
    assets = [
        _asset("AAPL", 0.50, role="core"),
        _asset("NVDA", 0.20, role="satellite"),
        _asset("TLT", 0.30),
    ]
    ac = {"AAPL": "equity", "NVDA": "equity", "TLT": "fixed_income"}
    result = _build_sleeve_breakdown(
        recommended_assets=assets,
        asset_class_by_ticker=ac,
        assumptions_by_ticker={t: _assumption(t) for t in ["AAPL", "NVDA", "TLT"]},
    )
    core = next(s for s in result.sleeves if s.sleeve_name == "core_beta")
    fi = next(s for s in result.sleeves if s.sleeve_name == "fixed_income")
    assert core.total_weight == pytest.approx(0.50, abs=1e-6)
    assert fi.total_weight == pytest.approx(0.30, abs=1e-6)


def test_sleeve_expected_return_is_weight_averaged_pct() -> None:
    """sleeve_er = Σ(w_i / total_sleeve_w × er_i) × 100."""
    assets = [_asset("AAPL", 0.6, role="core"), _asset("MSFT", 0.4, role="core")]
    ac = {"AAPL": "equity", "MSFT": "equity"}
    assumptions = {
        "AAPL": _assumption("AAPL", 0.10),  # 10%
        "MSFT": _assumption("MSFT", 0.08),  # 8%
    }
    result = _build_sleeve_breakdown(
        recommended_assets=assets,
        asset_class_by_ticker=ac,
        assumptions_by_ticker=assumptions,
    )
    core = next(s for s in result.sleeves if s.sleeve_name == "core_beta")
    # er = (0.6 × 0.10 + 0.4 × 0.08) / 1.0 × 100 = 9.2%
    assert core.sleeve_expected_return == pytest.approx(9.2, abs=1e-3)


def test_allocation_response_has_sleeve_breakdown_field() -> None:
    fields = AllocationRecommendationResponse.model_fields
    assert "sleeve_breakdown" in fields
    assert fields["sleeve_breakdown"].default is None


# ═══════════════════════════════════════════════════════════════════
# PC6.4 — ALLOCATION ALTERNATIVES
# ═══════════════════════════════════════════════════════════════════

def test_allocation_alternatives_schema_fields() -> None:
    fields = AllocationAlternatives.model_fields
    assert "alternatives" in fields
    assert "method" in fields


def test_alternative_allocation_schema_fields() -> None:
    fields = AlternativeAllocation.model_fields
    for f in ("candidate_id", "label", "description", "weights",
              "expected_return", "expected_volatility", "sharpe_ratio",
              "return_diff", "volatility_diff"):
        assert f in fields


def test_selected_candidate_excluded_from_alternatives() -> None:
    candidates = [
        _candidate("risk_parity_assumption_aware", 9.0, 18.0, 1.10),
        _candidate("min_variance_assumption_aware", 7.5, 14.0, 0.90),
        _candidate("max_sharpe_assumption_aware", 10.0, 20.0, 1.25),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="risk_parity_assumption_aware",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    ids = [a.candidate_id for a in result.alternatives]
    assert "risk_parity_assumption_aware" not in ids
    assert "min_variance_assumption_aware" in ids
    assert "max_sharpe_assumption_aware" in ids


def test_alternatives_contains_all_non_selected() -> None:
    candidates = [
        _candidate("risk_parity_aw", 9.0, 18.0, 1.10),
        _candidate("min_variance_aw", 7.5, 14.0, 0.90),
        _candidate("max_sharpe_aw", 10.0, 20.0, 1.25),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="risk_parity_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    assert len(result.alternatives) == 2


def test_min_variance_candidate_gets_defensive_label() -> None:
    candidates = [
        _candidate("risk_parity_aw", 9.0, 18.0, 1.0),
        _candidate("min_variance_assumption_aware", 7.5, 14.0, 0.85),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="risk_parity_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    mv = next(a for a in result.alternatives if "min_variance" in a.candidate_id)
    assert "defensive" in mv.label.lower() or "min" in mv.label.lower()


def test_max_sharpe_candidate_gets_return_focused_label() -> None:
    candidates = [
        _candidate("risk_parity_aw", 9.0, 18.0, 1.0),
        _candidate("max_sharpe_assumption_aware", 10.5, 21.0, 1.30),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="risk_parity_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    ms = next(a for a in result.alternatives if "max_sharpe" in a.candidate_id)
    assert any(word in ms.label.lower() for word in ("return", "adjusted", "sharpe", "higher"))


def test_alternatives_return_diff_formula() -> None:
    candidates = [
        _candidate("selected_aw", 9.0, 18.0, 1.0),
        _candidate("other_aw", 11.0, 22.0, 1.15),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="selected_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    alt = result.alternatives[0]
    assert alt.return_diff == pytest.approx(11.0 - 9.0, abs=1e-4)


def test_alternatives_volatility_diff_formula() -> None:
    candidates = [
        _candidate("selected_aw", 9.0, 18.0, 1.0),
        _candidate("other_aw", 7.5, 14.0, 0.85),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="selected_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    alt = result.alternatives[0]
    assert alt.volatility_diff == pytest.approx(14.0 - 18.0, abs=1e-4)


def test_alternatives_sorted_by_sharpe_descending() -> None:
    candidates = [
        _candidate("selected_aw", 9.0, 18.0, 1.10),
        _candidate("low_sharpe_aw", 7.0, 16.0, 0.70),
        _candidate("high_sharpe_aw", 10.5, 19.0, 1.40),
        _candidate("mid_sharpe_aw", 8.5, 17.0, 1.00),
    ]
    result = _build_alternatives(
        candidates=candidates,
        selected_candidate_id="selected_aw",
        recommended_expected_return=9.0,
        recommended_expected_volatility=18.0,
    )
    sharpes = [a.sharpe_ratio for a in result.alternatives]
    assert sharpes == sorted(sharpes, reverse=True)


def test_allocation_response_has_alternatives_field() -> None:
    fields = AllocationRecommendationResponse.model_fields
    assert "alternatives" in fields
    assert fields["alternatives"].default is None


# ═══════════════════════════════════════════════════════════════════
# PC4.4 — STRESS TESTS
# ═══════════════════════════════════════════════════════════════════

def test_stress_test_summary_schema_fields() -> None:
    fields = StressTestSummary.model_fields
    for f in ("scenarios", "worst_scenario_name", "worst_scenario_impact", "methodology"):
        assert f in fields


def test_stress_scenario_result_schema_fields() -> None:
    fields = StressScenarioResult.model_fields
    for f in ("scenario_name", "label", "description", "asset_class_shocks",
              "portfolio_impact", "stressed_value",
              "largest_detractor", "largest_detractor_contribution"):
        assert f in fields


def test_stress_tests_include_four_builtin_scenarios() -> None:
    result = _build_stress_tests(
        recommended_assets=[_asset("AAPL", 1.0)],
        asset_class_by_ticker={"AAPL": "equity"},
    )
    names = {s.scenario_name for s in result.scenarios}
    assert "equity_crash" in names
    assert "rate_shock" in names
    assert "inflation_spike" in names
    assert "stagflation" in names


def test_stress_portfolio_impact_formula() -> None:
    """portfolio_impact = Σ(w_i × shock(asset_class_i))."""
    # 60% equity, 40% bonds → equity_crash: 0.6×(-0.30) + 0.4×(+0.10) = -0.14
    assets = [_asset("AAPL", 0.6), _asset("TLT", 0.4)]
    ac = {"AAPL": "equity", "TLT": "fixed_income"}
    result = _build_stress_tests(recommended_assets=assets, asset_class_by_ticker=ac)
    crash = next(s for s in result.scenarios if s.scenario_name == "equity_crash")
    expected_impact = 0.6 * crash.asset_class_shocks["equity"] + 0.4 * crash.asset_class_shocks["fixed_income"]
    assert crash.portfolio_impact == pytest.approx(expected_impact, abs=1e-6)


def test_stressed_value_equals_one_plus_impact() -> None:
    assets = [_asset("AAPL", 1.0)]
    result = _build_stress_tests(
        recommended_assets=assets,
        asset_class_by_ticker={"AAPL": "equity"},
    )
    for scenario in result.scenarios:
        assert scenario.stressed_value == pytest.approx(1.0 + scenario.portfolio_impact, abs=1e-6)


def test_equity_crash_is_negative_for_equity_portfolio() -> None:
    """Pure equity portfolio should take a big hit in equity_crash."""
    assets = [_asset("AAPL", 0.5), _asset("MSFT", 0.5)]
    ac = {"AAPL": "equity", "MSFT": "equity"}
    result = _build_stress_tests(recommended_assets=assets, asset_class_by_ticker=ac)
    crash = next(s for s in result.scenarios if s.scenario_name == "equity_crash")
    assert crash.portfolio_impact < 0


def test_inflation_spike_positive_for_commodity_portfolio() -> None:
    """Commodity-only portfolio benefits from inflation spike scenario."""
    assets = [_asset("GLD", 0.5), _asset("USO", 0.5)]
    ac = {"GLD": "commodity", "USO": "commodity"}
    result = _build_stress_tests(recommended_assets=assets, asset_class_by_ticker=ac)
    inflation = next(s for s in result.scenarios if s.scenario_name == "inflation_spike")
    assert inflation.portfolio_impact > 0


def test_worst_scenario_has_lowest_portfolio_impact() -> None:
    assets = [_asset("AAPL", 1.0)]
    result = _build_stress_tests(
        recommended_assets=assets,
        asset_class_by_ticker={"AAPL": "equity"},
    )
    worst_impact = min(s.portfolio_impact for s in result.scenarios)
    worst = next(s for s in result.scenarios if s.scenario_name == result.worst_scenario_name)
    assert worst.portfolio_impact == pytest.approx(worst_impact, abs=1e-6)


def test_largest_detractor_has_most_negative_contribution() -> None:
    """The largest_detractor must be the ticker with the worst w × shock."""
    # Equity crash: AAPL (equity, 80%) vs TLT (fixed_income, 20%)
    # AAPL contrib = 0.8 × -0.30 = -0.24 (worst)
    # TLT contrib  = 0.2 × +0.10 = +0.02
    assets = [_asset("AAPL", 0.8), _asset("TLT", 0.2)]
    ac = {"AAPL": "equity", "TLT": "fixed_income"}
    result = _build_stress_tests(recommended_assets=assets, asset_class_by_ticker=ac)
    crash = next(s for s in result.scenarios if s.scenario_name == "equity_crash")
    assert crash.largest_detractor == "AAPL"
    assert crash.largest_detractor_contribution == pytest.approx(0.8 * -0.30, abs=1e-6)


def test_allocation_response_has_stress_tests_field() -> None:
    fields = AllocationRecommendationResponse.model_fields
    assert "stress_tests" in fields
    assert fields["stress_tests"].default is None
