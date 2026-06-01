from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import portfolio as portfolio_routes
from app.routes import universe as universe_routes
from app.schemas.portfolio import OptimizationObjective, OptimizeRequest
from app.schemas.universe import ScreenerRequest
from app.services import portfolio_optimization_service, universe_service
from app.workers.tasks import portfolio_task


def test_portfolio_and_universe_routes_no_longer_manage_src_path_directly() -> None:
    portfolio_source = (BACKEND_DIR / "app" / "routes" / "portfolio.py").read_text(encoding="utf-8")
    universe_source = (BACKEND_DIR / "app" / "routes" / "universe.py").read_text(encoding="utf-8")

    assert "sys.path.insert" not in portfolio_source
    assert "run_portfolio_optimization" in portfolio_source
    assert "sys.path.insert" not in universe_source
    assert "search_universe" in universe_source
    assert "screen_universe" in universe_source
    assert "get_instrument_detail" in universe_source


def test_portfolio_service_normalizes_optimizer_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Optimizer:
        def optimize(self, **kwargs):
            return {
                "asset_details": [
                    {"ticker": "AAPL", "weight": 0.6, "expected_return": 0.1, "volatility": 0.2},
                    {"ticker": "MSFT", "weight": 0.4, "expected_return": 0.08, "volatility": 0.18},
                ],
                "expected_return": 0.092,
                "expected_volatility": 0.19,
                "sharpe_ratio": 1.15,
                "diversification_ratio": 1.08,
                "efficient_frontier": {"points": [{"return": 0.09, "risk": 0.18}]},
            }

    monkeypatch.setattr(portfolio_optimization_service, "_load_optimizer", lambda: _Optimizer())

    result = portfolio_optimization_service.run_portfolio_optimization(
        OptimizeRequest(
            tickers=["AAPL", "MSFT"],
            objective=OptimizationObjective.max_sharpe,
            lookback_days=252,
            max_weight=0.8,
            min_weight=0.1,
        )
    )

    assert result["objective"] == "max_sharpe"
    assert len(result["weights"]) == 2
    assert result["weights"][0].ticker == "AAPL"
    assert result["efficient_frontier"][0].volatility == 0.18


def test_universe_service_normalizes_search_and_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    class _AssetClass:
        def __init__(self, value: str):
            self.value = value

    class _Instrument:
        def __init__(self, ticker: str):
            self.ticker = ticker
            self.name = f"{ticker} Inc."
            self.asset_class = _AssetClass("equity")
            self.sector = "Technology"
            self.country = "US"
            self.exchange = "NASDAQ"
            self.currency = "USD"
            self.price = 100.0
            self.price_change_1d = 0.01
            self.price_change_1m = 0.02
            self.price_change_1y = 0.15
            self.volume_avg_30d = 1_000_000.0
            self.market_cap = 500_000_000.0
            self.pe_ratio = 20.0
            self.pb_ratio = 4.0
            self.dividend_yield = 0.01
            self.volatility_1y = 0.2
            self.beta = 1.1
            self.sharpe_1y = 0.8
            self.esg_score = 55.0

    class _Pipeline:
        def get_instruments(self):
            return [_Instrument("AAPL"), _Instrument("MSFT")]

    class _Result:
        def __init__(self):
            self.instruments = [_Instrument("AAPL")]
            self.total_count = 1

    class _Engine:
        def __init__(self, instruments):
            self.instruments = instruments

        def screen(self, criteria):
            return _Result()

    class _Criteria:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.asset_classes = None

    class _UniverseModule:
        AssetClass = lambda self, value: value
        ScreenerCriteria = _Criteria
        ScreenerEngine = _Engine

        @staticmethod
        def get_pipeline():
            return _Pipeline()

    monkeypatch.setattr(universe_service, "_load_universe_module", lambda: _UniverseModule())

    search_payload = universe_service.search_universe(query="apple", asset_class=None, limit=5)
    detail_payload = universe_service.get_instrument_detail("aapl")
    screen_payload = universe_service.screen_universe(ScreenerRequest(limit=10))

    assert search_payload["total"] == 1
    assert search_payload["results"][0].ticker == "AAPL"
    assert detail_payload is not None
    assert detail_payload.exchange == "NASDAQ"
    assert screen_payload["total"] == 1
    assert screen_payload["instruments"][0].sector == "Technology"


def test_portfolio_worker_delegates_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.portfolio_optimization_service.run_portfolio_optimization_payload",
        lambda **kwargs: {
            "objective": kwargs["objective"],
            "weights": [],
            "expected_return": 0.1,
            "expected_volatility": 0.2,
            "sharpe_ratio": 1.0,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.1,
            "efficient_frontier": [],
        },
    )

    result = portfolio_task.optimize_portfolio(
        tickers=["AAPL", "MSFT"],
        objective="max_sharpe",
        risk_free_rate=0.03,
        lookback_days=252,
        max_weight=0.7,
        min_weight=0.1,
    )

    assert result["status"] == "ok"
    assert result["objective"] == "max_sharpe"


@pytest.mark.asyncio
async def test_portfolio_and_universe_routes_delegate_to_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Loop:
        async def run_in_executor(self, executor, fn, *args):
            return fn(*args)

    monkeypatch.setattr(portfolio_routes.asyncio, "get_event_loop", lambda: _Loop())
    monkeypatch.setattr(universe_routes.asyncio, "get_event_loop", lambda: _Loop())
    monkeypatch.setattr(
        portfolio_routes,
        "_optimize_sync",
        lambda req: {
            "objective": req.objective.value,
            "weights": [],
            "expected_return": 0.1,
            "expected_volatility": 0.2,
            "sharpe_ratio": 1.0,
            "risk_free_rate_used": 0.03,
            "diversification_ratio": 1.1,
            "efficient_frontier": [],
        },
    )
    monkeypatch.setattr(
        universe_routes,
        "_search_sync",
        lambda query, asset_class, limit: {"query": query, "total": 0, "results": []},
    )
    monkeypatch.setattr(
        universe_routes,
        "_screen_sync",
        lambda req: {"total": 0, "instruments": [], "filters_applied": {}},
    )
    monkeypatch.setattr(universe_routes, "_detail_sync", lambda ticker: None)

    portfolio_response = await portfolio_routes.portfolio_optimize(
        OptimizeRequest(tickers=["AAPL", "MSFT"], objective=OptimizationObjective.max_sharpe)
    )
    search_response = await universe_routes.universe_search(q="apple", asset_class=None, limit=10)
    screen_response = await universe_routes.universe_screen(ScreenerRequest(limit=10))

    assert portfolio_response.data.objective == "max_sharpe"
    assert search_response.data.query == "apple"
    assert screen_response.data.total == 0
