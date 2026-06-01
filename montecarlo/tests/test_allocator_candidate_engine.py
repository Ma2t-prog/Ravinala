from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import portfolio_optimization_service


def test_allocator_candidate_engine_builds_multiple_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(**kwargs):
        objective = kwargs["objective"]
        base = {
            "max_sharpe": (10.0, 18.0, 1.30, 0.7, 0.3),
            "risk_parity": (9.0, 16.0, 1.10, 0.55, 0.45),
            "min_variance": (7.0, 12.0, 0.90, 0.4, 0.6),
        }[objective]
        return {
            "objective": objective,
            "weights": [
                {"ticker": "AAPL", "weight": base[3], "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": base[4], "expected_return": 10.0, "volatility": 18.0},
            ],
            "expected_return": base[0],
            "expected_volatility": base[1],
            "sharpe_ratio": base[2],
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.05,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_assumptions_payload",
        _fake_run,
    )

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10},
        selected_objective="risk_parity",
        risk_free_rate=0.03,
        lookback_days=252,
        max_weight=0.7,
        min_weight=0.0,
    )

    assert result["selected_candidate_id"] == "risk_parity_assumption_aware"
    assert len(result["candidates"]) == 3
    assert {candidate["candidate_id"] for candidate in result["candidates"]} == {
        "max_sharpe_assumption_aware",
        "risk_parity_assumption_aware",
        "min_variance_assumption_aware",
    }
    assert result["selected_payload"]["objective"] == "risk_parity"


def test_allocator_candidate_engine_falls_back_when_requested_objective_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        if kwargs["objective"] == "risk_parity":
            raise ValueError("risk parity unavailable")
        return {
            "objective": kwargs["objective"],
            "weights": [
                {"ticker": "AAPL", "weight": 0.5, "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": 0.5, "expected_return": 10.0, "volatility": 18.0},
            ],
            "expected_return": 8.0,
            "expected_volatility": 14.0,
            "sharpe_ratio": 1.0,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.1,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_assumptions_payload",
        _fake_run,
    )

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10},
        selected_objective="risk_parity",
        risk_free_rate=0.03,
        lookback_days=252,
        max_weight=0.7,
        min_weight=0.0,
    )

    assert result["selected_candidate_id"] != "risk_parity_assumption_aware"
    assert any("risk_parity_assumption_aware unavailable" in warning for warning in result["warnings"])


def test_allocator_candidate_engine_can_consume_canonical_risk_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_if_called(**kwargs):
        raise AssertionError("legacy assumption path should not be called when risk_inputs is provided")

    def _fake_run(**kwargs):
        return {
            "objective": kwargs["objective"],
            "weights": [
                {"ticker": "AAPL", "weight": 0.5, "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": 0.5, "expected_return": 10.0, "volatility": 18.0},
            ],
            "expected_return": 8.8,
            "expected_volatility": 14.5,
            "sharpe_ratio": 1.05,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.08,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_assumptions_payload",
        _fail_if_called,
    )
    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_risk_inputs_payload",
        _fake_run,
    )

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10},
        selected_objective="max_sharpe",
        risk_inputs={
            "tickers_used": ["AAPL", "MSFT"],
            "covariance_matrix": {},
            "asset_risk_inputs": [],
        },
        risk_free_rate=0.03,
        lookback_days=252,
        max_weight=0.7,
        min_weight=0.0,
    )

    assert result["selected_candidate_id"] == "max_sharpe_assumption_aware"
    assert len(result["candidates"]) == 3


def test_allocator_candidate_engine_enforces_max_selected_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        return {
            "objective": kwargs["objective"],
            "weights": [
                {"ticker": "AAPL", "weight": 0.50, "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": 0.30, "expected_return": 10.0, "volatility": 18.0},
                {"ticker": "TLT", "weight": 0.20, "expected_return": 5.0, "volatility": 8.0},
            ],
            "expected_return": 8.8,
            "expected_volatility": 14.5,
            "sharpe_ratio": 1.05,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.08,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_risk_inputs_payload",
        _fake_run,
    )

    risk_inputs = {
        "tickers_used": ["AAPL", "MSFT", "TLT"],
        "covariance_matrix": {
            "AAPL": {"AAPL": 0.04, "MSFT": 0.02, "TLT": 0.01},
            "MSFT": {"AAPL": 0.02, "MSFT": 0.03, "TLT": 0.01},
            "TLT": {"AAPL": 0.01, "MSFT": 0.01, "TLT": 0.01},
        },
        "asset_risk_inputs": [
            {"ticker": "AAPL", "annualized_volatility": 0.20},
            {"ticker": "MSFT", "annualized_volatility": 0.18},
            {"ticker": "TLT", "annualized_volatility": 0.08},
        ],
    }

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT", "TLT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10, "TLT": 0.05},
        selected_objective="max_sharpe",
        risk_inputs=risk_inputs,
        max_selected_assets=2,
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity", "TLT": "bond"},
        risk_free_rate=0.03,
    )

    selected = result["selected_payload"]
    assert len(selected["weights"]) == 2
    assert sum(asset["weight"] for asset in selected["weights"]) == pytest.approx(1.0)
    assert "max_selected_assets" in selected["tradeoff_summary"]
    assert "max_selected_assets" in selected["applied_constraints"]


def test_allocator_candidate_engine_enforces_asset_class_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        return {
            "objective": kwargs["objective"],
            "weights": [
                {"ticker": "AAPL", "weight": 0.70, "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": 0.20, "expected_return": 10.0, "volatility": 18.0},
                {"ticker": "TLT", "weight": 0.10, "expected_return": 5.0, "volatility": 8.0},
            ],
            "expected_return": 9.2,
            "expected_volatility": 16.0,
            "sharpe_ratio": 1.15,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.04,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_risk_inputs_payload",
        _fake_run,
    )

    risk_inputs = {
        "tickers_used": ["AAPL", "MSFT", "TLT"],
        "covariance_matrix": {
            "AAPL": {"AAPL": 0.04, "MSFT": 0.02, "TLT": 0.01},
            "MSFT": {"AAPL": 0.02, "MSFT": 0.03, "TLT": 0.01},
            "TLT": {"AAPL": 0.01, "MSFT": 0.01, "TLT": 0.01},
        },
        "asset_risk_inputs": [
            {"ticker": "AAPL", "annualized_volatility": 0.20},
            {"ticker": "MSFT", "annualized_volatility": 0.18},
            {"ticker": "TLT", "annualized_volatility": 0.08},
        ],
    }

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT", "TLT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10, "TLT": 0.05},
        selected_objective="max_sharpe",
        risk_inputs=risk_inputs,
        asset_class_constraints=[
            {"asset_class": "equity", "max_weight": 0.60},
            {"asset_class": "bond", "min_weight": 0.20},
        ],
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity", "TLT": "bond"},
        risk_free_rate=0.03,
        max_weight=0.80,
    )

    selected = result["selected_payload"]
    weight_map = {asset["ticker"]: asset["weight"] for asset in selected["weights"]}
    equity_weight = weight_map["AAPL"] + weight_map["MSFT"]
    bond_weight = weight_map["TLT"]

    assert equity_weight == pytest.approx(0.60)
    assert bond_weight == pytest.approx(0.40)
    assert "asset_class_max:equity" in selected["applied_constraints"]


def test_allocator_candidate_engine_handles_cardinality_without_breaking_asset_class_feasibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        return {
            "objective": kwargs["objective"],
            "weights": [
                {"ticker": "AAPL", "weight": 0.50, "expected_return": 11.0, "volatility": 20.0},
                {"ticker": "MSFT", "weight": 0.30, "expected_return": 10.0, "volatility": 18.0},
                {"ticker": "TLT", "weight": 0.20, "expected_return": 5.0, "volatility": 8.0},
            ],
            "expected_return": 8.8,
            "expected_volatility": 14.5,
            "sharpe_ratio": 1.05,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.08,
            "efficient_frontier": [],
        }

    monkeypatch.setattr(
        portfolio_optimization_service,
        "run_portfolio_optimization_with_risk_inputs_payload",
        _fake_run,
    )

    risk_inputs = {
        "tickers_used": ["AAPL", "MSFT", "TLT"],
        "covariance_matrix": {
            "AAPL": {"AAPL": 0.04, "MSFT": 0.02, "TLT": 0.01},
            "MSFT": {"AAPL": 0.02, "MSFT": 0.03, "TLT": 0.01},
            "TLT": {"AAPL": 0.01, "MSFT": 0.01, "TLT": 0.01},
        },
        "asset_risk_inputs": [
            {"ticker": "AAPL", "annualized_volatility": 0.20},
            {"ticker": "MSFT", "annualized_volatility": 0.18},
            {"ticker": "TLT", "annualized_volatility": 0.08},
        ],
    }

    result = portfolio_optimization_service.run_allocator_candidate_optimizations_payload(
        tickers=["AAPL", "MSFT", "TLT"],
        expected_returns={"AAPL": 0.11, "MSFT": 0.10, "TLT": 0.05},
        selected_objective="max_sharpe",
        risk_inputs=risk_inputs,
        max_selected_assets=2,
        asset_class_constraints=[{"asset_class": "equity", "max_weight": 0.60}],
        asset_class_by_ticker={"AAPL": "equity", "MSFT": "equity", "TLT": "bond"},
        risk_free_rate=0.03,
        max_weight=0.80,
    )

    selected = result["selected_payload"]
    weight_map = {asset["ticker"]: asset["weight"] for asset in selected["weights"]}

    assert set(weight_map) == {"AAPL", "TLT"}
    assert weight_map["AAPL"] == pytest.approx(0.60)
    assert weight_map["TLT"] == pytest.approx(0.40)
    assert "max_selected_assets" in selected["applied_constraints"]
    assert "asset_class_max:equity" in selected["applied_constraints"]
