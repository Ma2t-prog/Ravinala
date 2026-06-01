from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
GENESIX_DIR = SRC_DIR / "genesix"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Avoid executing genesix/__init__.py during test collection.
if "genesix" not in sys.modules:
    pkg = types.ModuleType("genesix")
    pkg.__path__ = [str(GENESIX_DIR)]  # type: ignore[attr-defined]
    sys.modules["genesix"] = pkg

BacktestingEngine = importlib.import_module("genesix.backtesting_engine").BacktestingEngine
PerformanceTracker = importlib.import_module(
    "genesix.performance_engine.tracker"
).PerformanceTracker
RiskMetricsEngine = importlib.import_module("genesix.risk_metrics_engine").RiskMetricsEngine
quant = importlib.import_module("genesix.utils.quant_conventions")

ANNUALIZATION_FACTOR_VOL = quant.ANNUALIZATION_FACTOR_VOL
RISK_FREE_RATE = quant.RISK_FREE_RATE
TRADING_DAYS = quant.TRADING_DAYS


def test_backtesting_engine_uses_shared_risk_free_default() -> None:
    returns = pd.Series([0.01, -0.004, 0.006, 0.002, -0.003, 0.005], dtype=float)

    annual_return = (1.0 + returns).prod() ** (TRADING_DAYS / len(returns)) - 1.0
    annual_vol = float(returns.std()) * ANNUALIZATION_FACTOR_VOL
    expected_sharpe = (annual_return - RISK_FREE_RATE) / max(annual_vol, 0.001)

    observed = BacktestingEngine._calculate_sharpe(returns)
    assert observed == pytest.approx(expected_sharpe, rel=1e-9, abs=1e-12)


def test_risk_metrics_engine_defaults_to_shared_conventions() -> None:
    prices = pd.Series([100.0, 101.5, 100.8, 102.0, 103.2, 102.4, 104.1], dtype=float)
    engine = RiskMetricsEngine(price_series=prices)

    observed_default = engine.calculate_sharpe_ratio()
    observed_explicit = engine.calculate_sharpe_ratio(risk_free_rate=RISK_FREE_RATE)
    assert observed_default == pytest.approx(observed_explicit, rel=1e-12, abs=1e-12)

    metrics = engine.get_all_metrics()
    expected_vol = float(engine.returns.std()) * ANNUALIZATION_FACTOR_VOL * 100
    assert metrics.volatility == pytest.approx(expected_vol, rel=1e-9, abs=1e-12)


def test_performance_tracker_run_uses_shared_annualization(monkeypatch: pytest.MonkeyPatch) -> None:
    idx = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 101.0, 100.2, 102.4, 101.6, 103.0, 103.5, 104.2],
            "BBB": [50.0, 50.5, 50.3, 50.8, 51.0, 50.7, 51.2, 51.6],
        },
        index=idx,
    )
    benchmark = pd.Series(
        [200.0, 201.0, 200.4, 202.0, 201.5, 202.6, 203.1, 203.9],
        index=idx,
        name="SPY",
    )

    tracker = PerformanceTracker(
        tickers=["AAA", "BBB"],
        weights={"AAA": 0.6, "BBB": 0.4},
        benchmark="SPY",
        period="1mo",
    )
    monkeypatch.setattr(tracker, "_fetch_prices", lambda: prices)
    monkeypatch.setattr(tracker, "_fetch_benchmark", lambda: benchmark)

    snapshot = tracker.run()
    assert snapshot is not None
    assert tracker.rf == pytest.approx(RISK_FREE_RATE, rel=0, abs=0)

    nav = snapshot.nav
    daily_ret = nav.pct_change().dropna()
    expected_ann_ret = ((1.0 + daily_ret).prod() ** (TRADING_DAYS / len(daily_ret)) - 1.0) * 100
    expected_ann_vol = float(daily_ret.std()) * ANNUALIZATION_FACTOR_VOL * 100

    assert snapshot.annual_return == pytest.approx(round(float(expected_ann_ret), 2), rel=0, abs=1e-9)
    assert snapshot.annual_volatility == pytest.approx(round(float(expected_ann_vol), 2), rel=0, abs=1e-9)
