from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.allocation import persistence as allocation_persistence


class _FakeScalars:
    def __init__(self, rows: list[Any]):
        self._rows = list(rows)

    def all(self) -> list[Any]:
        return list(self._rows)


class _FakeExecuteResult:
    def __init__(self, rows: list[Any]):
        self._rows = list(rows)

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


class _FakeAsyncSession:
    def __init__(self, store: list[Any]):
        self._store = store

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        self._store.append(obj)

    async def commit(self) -> None:
        return None

    async def execute(self, query: Any) -> _FakeExecuteResult:
        rows = list(self._store)
        for criterion in getattr(query, "_where_criteria", ()):
            column = getattr(getattr(criterion, "left", None), "name", None)
            value = getattr(getattr(criterion, "right", None), "value", None)
            if column is not None:
                rows = [row for row in rows if getattr(row, column) == value]

        limit_clause = getattr(query, "_limit_clause", None)
        limit = getattr(limit_clause, "value", None)
        if limit is not None:
            rows = rows[:limit]

        return _FakeExecuteResult(rows)


class _FakeSessionFactory:
    def __init__(self, store: list[Any]):
        self._store = store

    def __call__(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self._store)


def _sample_payload() -> dict[str, Any]:
    return {
        "recommendation_id": "rec-123",
        "request_payload": {"amount": 100_000, "tickers": ["AAPL", "MSFT"]},
        "policy": {
            "amount": 100_000,
            "base_currency": "USD",
            "risk_profile": "moderate",
            "objective_used": "risk_parity",
            "benchmark_preference": "60_40",
        },
        "eligibility": {
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
            "eligible_assets": [{"ticker": "AAPL", "name": "Apple Inc.", "asset_class": "equity", "currency": "USD", "price": 190.0, "market_cap": 2_800_000_000_000.0, "volume_avg_30d": 50_000_000.0, "liquidity_tier": "deep", "data_quality_score": 1.0, "cost_proxy_available": True, "notes": []}],
            "rejected_assets": [],
            "warnings": [],
        },
        "assumptions": {
            "methodology_version": "cma_v1",
            "risk_free_rate_used": 0.03,
            "investment_horizon_years": 5,
            "assumptions": [
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
                }
            ],
            "warnings": [],
        },
        "risk_inputs": {
            "methodology_version": "portfolio_risk_inputs_v1",
            "risk_model_type": "historical_covariance_allocator_v1",
            "data_source": "yfinance",
            "lookback_days": 504,
            "observation_count": 252,
            "annualization_factor": 252,
            "risk_free_rate_used": 0.03,
            "benchmark_preference": "60_40",
            "tickers_used": ["AAPL", "MSFT"],
            "dropped_tickers": [],
            "asset_risk_inputs": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "asset_class": "equity",
                    "annualized_volatility": 0.22,
                    "downside_volatility": 0.18,
                    "max_drawdown_proxy": 0.25,
                    "var_95_1d": 0.021,
                    "cvar_95_1d": 0.031,
                    "data_points_used": 252,
                }
            ],
            "covariance_matrix": {
                "AAPL": {"AAPL": 0.0484, "MSFT": 0.0280},
                "MSFT": {"AAPL": 0.0280, "MSFT": 0.0324},
            },
            "correlation_matrix": {
                "AAPL": {"AAPL": 1.0, "MSFT": 0.71},
                "MSFT": {"AAPL": 0.71, "MSFT": 1.0},
            },
            "top_correlation_pairs": [
                {
                    "left_ticker": "AAPL",
                    "right_ticker": "MSFT",
                    "correlation": 0.71,
                    "absolute_correlation": 0.71,
                }
            ],
            "risk_budget": {
                "target_volatility": 0.14,
                "max_drawdown_tolerance": 0.2,
                "max_single_name_weight": 0.35,
                "min_weight": 0.0,
                "cash_buffer_weight": 0.05,
                "concentration_hhi_soft_limit": 0.2,
                "effective_name_floor": 5.0,
            },
            "universe_risk_diagnostics": {
                "asset_count": 2,
                "observation_count": 252,
                "average_pairwise_correlation": 0.71,
                "max_pairwise_correlation": 0.71,
                "volatility_dispersion": 0.04,
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
        "eligible_tickers": ["AAPL", "MSFT"],
        "recommended_assets": [{"ticker": "AAPL", "target_weight": 0.6}],
        "rejected_assets": [{"ticker": "BTC", "reason": "excluded_by_investor_policy"}],
        "optimization": {
            "objective": "risk_parity",
            "expected_return": 0.08,
            "expected_volatility": 0.12,
            "sharpe_ratio": 1.0,
            "risk_free_rate_used": 0.03,
            "selected_candidate_id": "risk_parity_assumption_aware",
            "constraint_snapshot": {
                "max_weight": 0.35,
                "min_weight": 0.0,
                "target_volatility": 0.14,
                "max_drawdown_tolerance": 0.2,
                "cash_buffer_weight": 0.05,
                "lookback_days": 504,
            },
            "candidate_portfolios": [
                {
                    "candidate_id": "risk_parity_assumption_aware",
                    "objective": "risk_parity",
                    "selected": True,
                    "expected_return": 0.08,
                    "expected_volatility": 0.12,
                    "sharpe_ratio": 1.0,
                    "diversification_ratio": 1.1,
                    "tradeoff_summary": "balanced risk-contribution candidate",
                    "weights": [{"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.6, "amount": 60000.0}],
                }
            ],
            "efficient_frontier": [],
        },
        "total_allocated_amount": 95_000.0,
        "cash_reserve_amount": 5_000.0,
        "warnings": ["allocation persistence test"],
    }


@pytest.mark.asyncio
async def test_allocator_persistence_helpers_fail_softly_when_db_is_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(allocation_persistence, "async_session", lambda: None)

    save_result = await allocation_persistence.save_allocation_run(_sample_payload())
    list_result = await allocation_persistence.list_allocation_runs_db(limit=10)
    get_result = await allocation_persistence.get_allocation_run_db("run-123")

    assert save_result is None
    assert list_result is None
    assert get_result is None


@pytest.mark.asyncio
async def test_allocator_persistence_round_trip_uses_db_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: list[Any] = []
    monkeypatch.setattr(
        allocation_persistence,
        "async_session",
        lambda: _FakeSessionFactory(store),
    )

    persisted = await allocation_persistence.save_allocation_run(_sample_payload())

    assert persisted is not None
    assert len(store) == 1

    listed = await allocation_persistence.list_allocation_runs_db(limit=10)
    assert listed is not None
    assert listed[0]["recommendation_id"] == "rec-123"
    assert listed[0]["recommended_asset_count"] == 1

    detail = await allocation_persistence.get_allocation_run_db(persisted["run_id"])
    assert detail is not None
    assert detail["recommendation_id"] == "rec-123"
    assert detail["eligibility"]["criteria"]["heuristic_version"] == "v1"
    assert detail["assumptions"]["methodology_version"] == "cma_v1"
    assert detail["risk_inputs"]["methodology_version"] == "portfolio_risk_inputs_v1"
    assert detail["optimization"]["objective"] == "risk_parity"
