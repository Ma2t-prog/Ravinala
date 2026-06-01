"""
tests/test_rebalancing_delta_boundaries.py

Boundary tests for the RebalancingDelta feature (chantier D / PC6 allocation response).

Coverage:
1.  RebalancingDelta schema fields and types.
2.  RebalancingTradeInstruction schema fields.
3.  No current positions → available=False, all actions="open", turnover=0.5*sum(weights).
4.  Full overlap (same weights) → available=True, actions="hold", turnover≈0.
5.  Partial overlap — buy/sell/open/close actions correctly assigned.
6.  Hold band: |delta| < 0.001 → action="hold".
7.  one_way_turnover formula: 0.5 × Σ|delta_weight|.
8.  new_positions: tickers in target but not in current.
9.  closed_positions: tickers in current but not in target.
10. Trades sorted by |delta_weight| descending.
11. AllocationRecommendationResponse has rebalancing_delta field (schema contract).
12. _build_rebalancing_delta returns RebalancingDelta instance.
13. From-scratch (no current positions) — turnover = 0.5 × total_recommended_weight.
14. Full liquidation (current positions, no recommendation) → all "close", turnover = 0.5 × sum(current).
15. Negative delta → action="sell".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import (
    AllocationRecommendationResponse,
    RebalancingDelta,
    RebalancingTradeInstruction,
    RecommendedAsset,
)
from app.services.allocation_recommendation_service import _build_rebalancing_delta


# ── Helpers ───────────────────────────────────────────────────────────────────

def _asset(ticker: str, weight: float) -> RecommendedAsset:
    return RecommendedAsset(
        ticker=ticker,
        name=ticker,
        target_weight=weight,
        target_amount=weight * 100_000,
        role="core",
        selection_reason="test",
    )


# ── 1–2. Schema contracts ─────────────────────────────────────────────────────

def test_rebalancing_delta_schema_fields() -> None:
    """RebalancingDelta must expose available, one_way_turnover, trades, new/closed_positions."""
    fields = RebalancingDelta.model_fields
    assert "available" in fields
    assert "one_way_turnover" in fields
    assert "trades" in fields
    assert "new_positions" in fields
    assert "closed_positions" in fields


def test_rebalancing_trade_instruction_schema_fields() -> None:
    """RebalancingTradeInstruction must expose ticker, weights, delta, action."""
    fields = RebalancingTradeInstruction.model_fields
    assert "ticker" in fields
    assert "current_weight" in fields
    assert "target_weight" in fields
    assert "delta_weight" in fields
    assert "action" in fields


# ── 3. No current positions ───────────────────────────────────────────────────

def test_no_current_positions_available_false() -> None:
    """Without current_positions, available must be False."""
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.6), _asset("MSFT", 0.4)],
        current_position_weights={},
    )
    assert result.available is False


def test_no_current_positions_all_actions_open() -> None:
    """Without current_positions, every trade action must be 'open'."""
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.6), _asset("MSFT", 0.4)],
        current_position_weights={},
    )
    assert all(t.action == "open" for t in result.trades)


def test_no_current_positions_turnover_equals_half_target_sum() -> None:
    """Without current_positions, one_way_turnover = 0.5 × sum(target_weights)."""
    assets = [_asset("AAPL", 0.6), _asset("MSFT", 0.4)]
    result = _build_rebalancing_delta(
        recommended_assets=assets,
        current_position_weights={},
    )
    expected = 0.5 * sum(a.target_weight for a in assets)
    assert result.one_way_turnover == pytest.approx(expected, abs=1e-6)


# ── 4. Full overlap, same weights ────────────────────────────────────────────

def test_identical_weights_produce_hold_actions() -> None:
    """Exact same weights → all actions 'hold', turnover ≈ 0."""
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.6), _asset("MSFT", 0.4)],
        current_position_weights={"AAPL": 0.6, "MSFT": 0.4},
    )
    assert result.available is True
    assert all(t.action == "hold" for t in result.trades)
    assert result.one_way_turnover == pytest.approx(0.0, abs=1e-6)


# ── 5. Partial overlap ────────────────────────────────────────────────────────

def test_partial_overlap_actions() -> None:
    """open=new ticker, close=removed ticker, buy=increase, sell=decrease."""
    result = _build_rebalancing_delta(
        recommended_assets=[
            _asset("AAPL", 0.5),   # was 0.3 → buy
            _asset("GOOG", 0.3),   # not held → open
            _asset("MSFT", 0.2),   # was 0.4 → sell
        ],
        current_position_weights={
            "AAPL": 0.3,
            "MSFT": 0.4,
            "TLT": 0.3,   # not recommended → close
        },
    )
    by_ticker = {t.ticker: t for t in result.trades}

    assert by_ticker["AAPL"].action == "buy"
    assert by_ticker["GOOG"].action == "open"
    assert by_ticker["MSFT"].action == "sell"
    assert by_ticker["TLT"].action == "close"


# ── 6. Hold band ──────────────────────────────────────────────────────────────

def test_hold_band_small_delta_is_hold() -> None:
    """|delta| < 0.001 (hold band) must produce action='hold'."""
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.600_5)],
        current_position_weights={"AAPL": 0.600_0},
    )
    assert result.trades[0].action == "hold"


def test_hold_band_just_above_threshold_is_not_hold() -> None:
    """|delta| = 0.002 must produce buy, not hold."""
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.602)],
        current_position_weights={"AAPL": 0.600},
    )
    assert result.trades[0].action == "buy"


# ── 7. Turnover formula ───────────────────────────────────────────────────────

def test_one_way_turnover_formula() -> None:
    """one_way_turnover = 0.5 × Σ|delta_weight|."""
    result = _build_rebalancing_delta(
        recommended_assets=[
            _asset("AAPL", 0.5),
            _asset("GOOG", 0.3),
        ],
        current_position_weights={
            "AAPL": 0.3,
            "MSFT": 0.4,
        },
    )
    expected = 0.5 * sum(abs(t.delta_weight) for t in result.trades)
    assert result.one_way_turnover == pytest.approx(expected, abs=1e-6)


# ── 8–9. new_positions / closed_positions ────────────────────────────────────

def test_new_positions_contains_only_open_tickers() -> None:
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.5), _asset("GOOG", 0.5)],
        current_position_weights={"AAPL": 0.5},
    )
    assert result.new_positions == ["GOOG"]
    assert result.closed_positions == []


def test_closed_positions_contains_only_close_tickers() -> None:
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 1.0)],
        current_position_weights={"AAPL": 0.5, "TLT": 0.5},
    )
    assert result.closed_positions == ["TLT"]
    assert result.new_positions == []


# ── 10. Trades sorted by |delta_weight| descending ───────────────────────────

def test_trades_sorted_by_abs_delta_descending() -> None:
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.8), _asset("MSFT", 0.2)],
        current_position_weights={"AAPL": 0.1, "MSFT": 0.9},
    )
    deltas = [abs(t.delta_weight) for t in result.trades]
    assert deltas == sorted(deltas, reverse=True)


# ── 11. AllocationRecommendationResponse schema contract ─────────────────────

def test_allocation_recommendation_response_has_rebalancing_delta_field() -> None:
    """AllocationRecommendationResponse must declare rebalancing_delta (optional)."""
    fields = AllocationRecommendationResponse.model_fields
    assert "rebalancing_delta" in fields
    # Field should be optional (default None)
    assert fields["rebalancing_delta"].default is None


# ── 12. Return type ───────────────────────────────────────────────────────────

def test_build_rebalancing_delta_returns_correct_type() -> None:
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 1.0)],
        current_position_weights={"AAPL": 0.5},
    )
    assert isinstance(result, RebalancingDelta)
    assert all(isinstance(t, RebalancingTradeInstruction) for t in result.trades)


# ── 13. From-scratch turnover ─────────────────────────────────────────────────

def test_from_scratch_turnover_is_half_total_weight() -> None:
    """All new positions, no current portfolio → turnover = 0.5 × Σ target weights."""
    assets = [_asset("AAPL", 0.4), _asset("MSFT", 0.35), _asset("GOOG", 0.25)]
    result = _build_rebalancing_delta(
        recommended_assets=assets,
        current_position_weights={},
    )
    expected_turnover = 0.5 * sum(a.target_weight for a in assets)
    assert result.one_way_turnover == pytest.approx(expected_turnover, abs=1e-6)
    assert result.one_way_turnover == pytest.approx(0.5, abs=1e-6)


# ── 14. Full liquidation ──────────────────────────────────────────────────────

def test_full_liquidation_all_close() -> None:
    """No recommendation, all current positions → all 'close'."""
    result = _build_rebalancing_delta(
        recommended_assets=[],
        current_position_weights={"AAPL": 0.6, "MSFT": 0.4},
    )
    assert result.available is True
    assert all(t.action == "close" for t in result.trades)
    assert sorted(result.closed_positions) == ["AAPL", "MSFT"]
    assert result.new_positions == []
    assert result.one_way_turnover == pytest.approx(0.5, abs=1e-6)


# ── 15. Negative delta → sell ────────────────────────────────────────────────

def test_negative_delta_produces_sell_action() -> None:
    result = _build_rebalancing_delta(
        recommended_assets=[_asset("AAPL", 0.3)],
        current_position_weights={"AAPL": 0.7},
    )
    trade = result.trades[0]
    assert trade.action == "sell"
    assert trade.delta_weight < 0
    assert trade.delta_weight == pytest.approx(-0.4, abs=1e-6)
