from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.routing import APIRoute

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.backtest import persistence as backtest_persistence
from app.backtest.engine import run_with_baselines
from app.routes import backtest as backtest_routes
from app.services import backtest_service
from app.routes.backtest import CostModelResponse, RunSummary, router
from app.workers.tasks import backtest_task


def _route(path: str, method: str) -> APIRoute:
    for candidate in router.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"Route not found for {method} {path}")


def _sample_prices() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC")
    closes = pd.DataFrame(
        {
            "AAPL": [100, 101, 102, 104, 103, 105, 107, 108],
            "MSFT": [200, 198, 201, 203, 204, 206, 207, 209],
            "SPY": [400, 401, 402, 403, 404, 405, 406, 407],
        },
        index=dates,
    )
    return pd.concat({"Close": closes}, axis=1)


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
    def __init__(self, store: dict[str, list[Any]]):
        self._store = store

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def add(self, obj: Any) -> None:
        bucket = "runs" if obj.__class__.__name__ == "BacktestRun" else "trades"
        self._store[bucket].append(obj)

    async def commit(self) -> None:
        return None

    async def execute(self, query: Any) -> _FakeExecuteResult:
        rows = list(self._store["runs"])
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
    def __init__(self, store: dict[str, list[Any]]):
        self._store = store

    def __call__(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self._store)


def _db_store() -> dict[str, list[Any]]:
    return {"runs": [], "trades": []}


def _result_bundle() -> dict[str, Any]:
    return run_with_baselines(
        prices=_sample_prices(),
        assets=["AAPL", "MSFT"],
        strategy="equal_weight",
        benchmark="SPY",
        initial_capital=100_000.0,
        commission_bps=5.0,
        slippage_bps=5.0,
        risk_free_rate=0.03,
        params={"rebalance_freq": 2},
        seed=7,
    )


def test_backtest_routes_use_typed_contracts() -> None:
    run_route = _route("/api/v1/backtest/run", "POST")
    list_route = _route("/api/v1/backtest/runs", "GET")
    detail_route = _route("/api/v1/backtest/runs/{run_id}", "GET")

    assert "ApiResponse" in str(run_route.response_model)
    assert "BacktestRunResponse" in str(run_route.response_model)
    assert "ApiResponse" in str(list_route.response_model)
    assert "RunSummary" in str(list_route.response_model)
    assert "ApiResponse" in str(detail_route.response_model)
    assert "BacktestRunResponse" in str(detail_route.response_model)
    assert backtest_routes.FullRunResponse.model_fields["cost_model"].annotation is CostModelResponse


@pytest.mark.asyncio
async def test_backtest_bundle_round_trip_uses_db_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _db_store()
    monkeypatch.setattr(backtest_persistence, "async_session", lambda: _FakeSessionFactory(store))
    monkeypatch.setattr(backtest_service, "_runs_store", {})

    result = _result_bundle()
    persisted = await backtest_persistence.save_backtest_bundle(result)

    assert persisted is not None
    assert persisted["persisted_runs"] == 3
    assert {row.bundle_role for row in store["runs"]} == {
        "primary",
        "baseline_buy_hold",
        "baseline_equal_weight",
    }
    assert len(store["trades"]) == sum(run.n_trades for run in result.values() if hasattr(run, "n_trades"))

    listed = await backtest_routes.list_runs(strategy=None, limit=10)
    assert len(listed.data) == 1
    assert isinstance(listed.data[0], RunSummary)
    assert listed.data[0].run_id == str(result["primary"].run_id)
    assert listed.data[0].risk_free_rate_used == pytest.approx(0.03)

    fetched = await backtest_routes.get_run(str(result["primary"].run_id))
    assert fetched.data.primary.run_id == str(result["primary"].run_id)
    assert fetched.data.primary.cost_model.name == "flat_bps"
    assert fetched.data.primary.cost_model.commission_bps == pytest.approx(5.0)
    assert fetched.data.primary.cost_model.slippage_bps == pytest.approx(5.0)
    assert fetched.data.comparison == result["comparison"]


def test_backtest_worker_includes_persisted_bundle_id(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _result_bundle()

    class _Provider:
        def fetch_prices_batch(self, tickers: list[str], period: str) -> pd.DataFrame:
            assert set(tickers) == {"AAPL", "MSFT", "SPY"}
            assert period == "1y"
            return _sample_prices()

    monkeypatch.setattr(backtest_service, "_fetch_prices_sync", lambda tickers, period: _Provider().fetch_prices_batch(tickers, period))
    monkeypatch.setattr(backtest_service, "run_with_baselines", lambda **kwargs: result)
    monkeypatch.setattr(
        "app.backtest.persistence.save_backtest_bundle_sync",
        lambda payload: {"bundle_id": str(payload["primary"].run_id)},
    )

    payload = backtest_task.run_backtest(
        assets=["AAPL", "MSFT"],
        strategy="equal_weight",
        benchmark="SPY",
        period="1y",
        initial_capital=100_000.0,
        commission_bps=5.0,
        slippage_bps=5.0,
        risk_free_rate=0.03,
        seed=7,
        params={"rebalance_freq": 2},
    )

    assert payload["status"] == "ok"
    assert payload["bundle_id"] == str(result["primary"].run_id)
