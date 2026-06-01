"""
tests/test_agents_node_truthfulness.py

Validates that PortfolioAgent, BacktestAgent, SpawnerAgent CorrelationAgent,
and LoggerAgent are now connected to real services / real data.

1. PortfolioAgent delegates to run_portfolio_optimization_payload.
2. PortfolioAgent falls back to equal_weight when < 2 tickers.
3. PortfolioAgent falls back on optimizer error (not crash).
4. PortfolioAgent returns source="portfolio_optimizer" on success.
5. BacktestAgent delegates to run_backtest_bundle.
6. BacktestAgent returns source="not_executed" when no tickers.
7. BacktestAgent coerces unknown strategy to default (no crash).
8. BacktestAgent falls back on engine error.
9. CorrelationAgent uses real returns_30d when available.
10. CorrelationAgent falls back to hash-based when no returns data.
11. LoggerAgent has no _fake_delay (asyncio.sleep directly).
"""

from __future__ import annotations

import os
import sys
import math
from types import SimpleNamespace
from unittest import mock

import pytest

# Stub langgraph before importing any agent module
sys.modules.setdefault("langgraph", mock.MagicMock())
sys.modules.setdefault("langgraph.config", mock.MagicMock())
sys.modules.setdefault("langgraph.graph", mock.MagicMock())
sys.modules.setdefault("langgraph.graph.message", mock.MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.nodes import portfolio_agent, backtest_agent, spawner_agent, logger_agent  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _events(monkeypatch, module) -> list[dict]:
    evts: list[dict] = []
    monkeypatch.setattr(module, "get_stream_writer", lambda: evts.append)
    return evts


def _mock_executor(monkeypatch, module):
    monkeypatch.setattr(module, "get_shared_executor", lambda: None)


def _fake_opt_result(tickers):
    """Simulate what run_portfolio_optimization_payload returns."""
    n = len(tickers)
    weights = [SimpleNamespace(ticker=t, weight=round(1.0 / n, 4)) for t in tickers]
    return {
        "objective": "max_sharpe",
        "weights": weights,
        "expected_return": 8.5,
        "expected_volatility": 14.2,
        "sharpe_ratio": 0.78,
        "risk_free_rate_used": 0.045,
        "diversification_ratio": 1.12,
        "efficient_frontier": [],
    }


# ── PortfolioAgent ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portfolio_agent_delegates_to_optimizer(monkeypatch):
    evts = _events(monkeypatch, portfolio_agent)
    _mock_executor(monkeypatch, portfolio_agent)

    tickers = ["AAPL", "MSFT", "GOOGL"]

    def fake_opt(tickers, objective):
        return _fake_opt_result(tickers)

    monkeypatch.setattr(portfolio_agent, "run_portfolio_optimization_payload", fake_opt)

    result = await portfolio_agent.portfolio_agent_node({"params": {"tickers": tickers}})

    assert result["agents_completed"] == ["PortfolioAgent"]
    pd = result["portfolio_data"]
    assert pd["source"] == "portfolio_optimizer"
    assert pd["sharpe"] == pytest.approx(0.78)
    assert pd["expected_return"] == pytest.approx(8.5)
    assert set(pd["weights"].keys()) == set(tickers)
    assert any(e["event"] == "portfolio_complete" for e in evts)


@pytest.mark.asyncio
async def test_portfolio_agent_fallback_too_few_tickers(monkeypatch):
    evts = _events(monkeypatch, portfolio_agent)
    _mock_executor(monkeypatch, portfolio_agent)

    result = await portfolio_agent.portfolio_agent_node({"params": {"tickers": ["AAPL"]}})

    assert result["agents_completed"] == ["PortfolioAgent"]
    pd = result["portfolio_data"]
    assert pd["source"] == "fallback_equal_weight"
    assert "fallback_reason" in pd
    assert any(e["event"] == "portfolio_skipped" for e in evts)


@pytest.mark.asyncio
async def test_portfolio_agent_fallback_on_optimizer_error(monkeypatch):
    evts = _events(monkeypatch, portfolio_agent)
    _mock_executor(monkeypatch, portfolio_agent)

    def bad_opt(tickers, objective):
        raise RuntimeError("optimizer failed")

    monkeypatch.setattr(portfolio_agent, "run_portfolio_optimization_payload", bad_opt)

    result = await portfolio_agent.portfolio_agent_node(
        {"params": {"tickers": ["AAPL", "MSFT"]}}
    )

    # Should go to agents_failed path (not crash silently)
    assert "agents_failed" in result
    assert result["agents_failed"] == ["PortfolioAgent"]
    assert any(e["event"] == "portfolio_error" for e in evts)


@pytest.mark.asyncio
async def test_portfolio_agent_method_mapping(monkeypatch):
    """risk_parity method maps to risk_parity objective."""
    evts = _events(monkeypatch, portfolio_agent)
    _mock_executor(monkeypatch, portfolio_agent)

    used_objectives: list[str] = []

    def fake_opt(tickers, objective):
        used_objectives.append(objective)
        return _fake_opt_result(tickers)

    monkeypatch.setattr(portfolio_agent, "run_portfolio_optimization_payload", fake_opt)

    await portfolio_agent.portfolio_agent_node(
        {"params": {"tickers": ["AAPL", "MSFT"], "method": "risk_parity"}}
    )

    assert used_objectives == ["risk_parity"]


# ── BacktestAgent ─────────────────────────────────────────────────────────────

def _fake_bundle(strategy):
    metrics = {
        "total_return": 0.312,
        "sharpe_ratio": 1.05,
        "max_drawdown": -0.18,
        "volatility": 0.14,
        "risk_free_rate": 0.045,
    }
    primary = SimpleNamespace(
        run_id="bt-001", run_name="test_bt",
        strategy=strategy, level="strategy", status="completed",
        assets=["AAPL", "MSFT"], benchmark="SPY",
        start_date="2022-01-01", end_date="2025-01-01",
        params={}, seed=42, initial_capital=100_000,
        cost_model_desc={"commission_bps": 10, "slippage_bps": 5},
        metrics=metrics, benchmark_metrics={}, limitations={},
        deployment_policy={}, n_trades=37, duration_seconds=1.2,
        error_message=None,
    )
    return {
        "primary": primary,
        "baseline_buy_hold": primary,
        "baseline_equal_weight": primary,
        "comparison": {},
    }


@pytest.mark.asyncio
async def test_backtest_agent_delegates_to_engine(monkeypatch):
    evts = _events(monkeypatch, backtest_agent)
    _mock_executor(monkeypatch, backtest_agent)

    async def fake_bundle(**kwargs):
        return _fake_bundle(kwargs["strategy"])

    monkeypatch.setattr(backtest_agent, "run_backtest_bundle", fake_bundle)

    result = await backtest_agent.backtest_agent_node(
        {"params": {"tickers": ["AAPL", "MSFT"], "strategy": "momentum"}}
    )

    assert result["agents_completed"] == ["BacktestAgent"]
    bd = result["backtest_data"]
    assert bd["source"] == "backtest_engine"
    assert bd["strategy"] == "momentum"
    assert bd["total_return"] == pytest.approx(0.312)
    assert bd["n_trades"] == 37
    assert any(e["event"] == "backtest_complete" for e in evts)


@pytest.mark.asyncio
async def test_backtest_agent_skipped_when_no_tickers(monkeypatch):
    evts = _events(monkeypatch, backtest_agent)
    _mock_executor(monkeypatch, backtest_agent)

    result = await backtest_agent.backtest_agent_node({"params": {"tickers": []}})

    assert result["agents_completed"] == ["BacktestAgent"]
    assert result["backtest_data"]["source"] == "not_executed"
    assert any(e["event"] == "backtest_skipped" for e in evts)


@pytest.mark.asyncio
async def test_backtest_agent_coerces_unknown_strategy(monkeypatch):
    evts = _events(monkeypatch, backtest_agent)
    _mock_executor(monkeypatch, backtest_agent)

    used_strategies: list[str] = []

    async def fake_bundle(**kwargs):
        used_strategies.append(kwargs["strategy"])
        return _fake_bundle(kwargs["strategy"])

    monkeypatch.setattr(backtest_agent, "run_backtest_bundle", fake_bundle)

    result = await backtest_agent.backtest_agent_node(
        {"params": {"tickers": ["AAPL", "MSFT"], "strategy": "totally_unknown"}}
    )

    assert result["agents_completed"] == ["BacktestAgent"]
    assert used_strategies == ["momentum"]  # default


@pytest.mark.asyncio
async def test_backtest_agent_returns_error_on_engine_failure(monkeypatch):
    evts = _events(monkeypatch, backtest_agent)
    _mock_executor(monkeypatch, backtest_agent)

    from app.services.backtest_service import BacktestExecutionError

    async def bad_bundle(**kwargs):
        raise BacktestExecutionError("engine broken")

    monkeypatch.setattr(backtest_agent, "run_backtest_bundle", bad_bundle)

    result = await backtest_agent.backtest_agent_node(
        {"params": {"tickers": ["AAPL", "MSFT"], "strategy": "momentum"}}
    )

    assert "agents_failed" in result
    assert result["agents_failed"] == ["BacktestAgent"]
    assert any(e["event"] == "backtest_error" for e in evts)


# ── SpawnerAgent / CorrelationAgent ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_correlation_agent_uses_real_returns(monkeypatch):
    """CorrelationAgent computes real Pearson correlation from returns_30d."""
    evts: list[dict] = []
    monkeypatch.setattr(spawner_agent, "get_stream_writer", lambda: evts.append)

    # AAPL and MSFT with perfectly correlated series (correlation = 1.0)
    returns_a = [0.01 * i for i in range(1, 31)]
    returns_b = [0.02 * i for i in range(1, 31)]  # 2× scale, same direction

    state = {
        "market_data": {
            "AAPL": {"returns_30d": returns_a, "price": 175.0},
            "MSFT": {"returns_30d": returns_b, "price": 420.0},
        },
        "risk_data": {},
        "analysis_data": {},
        "params": {"tickers": ["AAPL", "MSFT"]},
    }

    # Only run the spawner for correlation (inject a minimal _decide_agents)
    monkeypatch.setattr(
        spawner_agent, "_decide_agents",
        lambda s: [{"name": "CorrelationAgent", "reason": "test", "fn": spawner_agent._run_correlation}],
    )

    result = await spawner_agent.spawner_agent_node(state)

    corr = result["spawned_data"]["CorrelationAgent"]
    assert corr["source"] == "computed", "Should use real returns, not hash fallback"
    # AAPL vs MSFT should be highly correlated (both rising linearly)
    assert corr["correlation_matrix"]["AAPL"]["MSFT"] > 0.9
    assert corr["correlation_matrix"]["AAPL"]["AAPL"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_correlation_agent_fallback_when_no_returns(monkeypatch):
    """CorrelationAgent falls back to hash-based when no returns_30d available."""
    evts: list[dict] = []
    monkeypatch.setattr(spawner_agent, "get_stream_writer", lambda: evts.append)

    state = {
        "market_data": {
            "AAPL": {"price": 175.0},   # no returns_30d
            "MSFT": {"price": 420.0},
        },
        "risk_data": {},
        "analysis_data": {},
        "params": {"tickers": ["AAPL", "MSFT"]},
    }

    monkeypatch.setattr(
        spawner_agent, "_decide_agents",
        lambda s: [{"name": "CorrelationAgent", "reason": "test", "fn": spawner_agent._run_correlation}],
    )

    result = await spawner_agent.spawner_agent_node(state)

    corr = result["spawned_data"]["CorrelationAgent"]
    assert corr["source"] == "fallback_hash"
    assert corr["correlation_matrix"]["AAPL"]["AAPL"] == pytest.approx(1.0)


# ── LoggerAgent ───────────────────────────────────────────────────────────────

def test_logger_agent_has_no_fake_delay():
    """LoggerAgent must not contain a _fake_delay function."""
    assert not hasattr(logger_agent, "_fake_delay"), (
        "logger_agent still has _fake_delay — remove it and use asyncio.sleep directly"
    )


def test_logger_agent_uses_asyncio():
    """LoggerAgent imports asyncio at the module level."""
    import asyncio as _asyncio
    import inspect
    src = inspect.getsource(logger_agent)
    assert "import asyncio" in src
    assert "asyncio.sleep" in src
