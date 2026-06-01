from __future__ import annotations

import importlib
import math
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
ANALYSIS_DIR = SRC_DIR / "analysis"
GENESIX_DIR = SRC_DIR / "genesix"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Minimal Streamlit stub to import analysis modules in test environment.
if "streamlit" not in sys.modules:
    st_stub = types.ModuleType("streamlit")

    def _cache_data(*args, **kwargs):
        def _decorator(fn):
            return fn
        return _decorator

    st_stub.cache_data = _cache_data  # type: ignore[attr-defined]
    sys.modules["streamlit"] = st_stub

# Minimal Plotly stubs (import-time only for this slice).
if "plotly" not in sys.modules:
    plotly_stub = types.ModuleType("plotly")
    go_stub = types.ModuleType("plotly.graph_objects")
    subplots_stub = types.ModuleType("plotly.subplots")

    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

    go_stub.Figure = _Dummy  # type: ignore[attr-defined]
    go_stub.Scatter = _Dummy  # type: ignore[attr-defined]
    subplots_stub.make_subplots = lambda *args, **kwargs: _Dummy()  # type: ignore[attr-defined]

    sys.modules["plotly"] = plotly_stub
    sys.modules["plotly.graph_objects"] = go_stub
    sys.modules["plotly.subplots"] = subplots_stub

# Avoid executing analysis/__init__.py during test collection.
if "analysis" not in sys.modules:
    pkg = types.ModuleType("analysis")
    pkg.__path__ = [str(ANALYSIS_DIR)]  # type: ignore[attr-defined]
    sys.modules["analysis"] = pkg

# Avoid executing genesix/__init__.py during test collection.
if "genesix" not in sys.modules:
    pkg = types.ModuleType("genesix")
    pkg.__path__ = [str(GENESIX_DIR)]  # type: ignore[attr-defined]
    sys.modules["genesix"] = pkg

Backtester = importlib.import_module("analysis.backtesting").Backtester
quant = importlib.import_module("genesix.utils.quant_conventions")
RISK_FREE_RATE = quant.RISK_FREE_RATE
TRADING_DAYS = quant.TRADING_DAYS
annualize_geometric_return = quant.annualize_geometric_return
annualize_volatility = quant.annualize_volatility
periods_per_year_for_timeframe = quant.periods_per_year_for_timeframe
sharpe_ratio = quant.sharpe_ratio


def _build_equity_from_returns(returns: np.ndarray) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(returns) + 1, freq="B")
    path = np.cumprod(np.concatenate(([1.0], 1.0 + returns)))
    return pd.Series(100.0 * path, index=idx, dtype=float)


def test_backtester_defaults_align_with_quant_conventions() -> None:
    bt = Backtester()
    assert bt.risk_free_rate == RISK_FREE_RATE
    assert bt.periods_per_year == TRADING_DAYS


def test_compute_metrics_uses_excess_return_for_sharpe_and_sortino() -> None:
    base = np.array([0.012, -0.006, 0.008, -0.003, 0.009, -0.002], dtype=float)
    returns = np.tile(base, 40)
    equity = _build_equity_from_returns(returns)
    benchmark = pd.Series(np.linspace(100.0, 106.0, len(equity)), index=equity.index)

    risk_free = 0.03
    metrics = Backtester._compute_metrics(
        equity,
        [],
        benchmark,
        risk_free_rate=risk_free,
        periods_per_year=TRADING_DAYS,
    )

    daily = equity.pct_change().dropna()
    cagr_dec = annualize_geometric_return(daily.values, trading_days=TRADING_DAYS)
    vol_dec = annualize_volatility(float(daily.std()))
    expected_sharpe = sharpe_ratio(cagr_dec, vol_dec, risk_free_rate=risk_free)
    downside = daily[daily < 0]
    downside_vol_dec = annualize_volatility(float(downside.std()))
    expected_sortino = (cagr_dec - risk_free) / downside_vol_dec

    assert metrics["sharpe"] == round(expected_sharpe, 2)
    assert metrics["sortino"] == round(expected_sortino, 2)
    assert metrics["risk_free_rate_used"] == round(risk_free, 6)
    assert metrics["periods_per_year_used"] == TRADING_DAYS


def test_compute_metrics_respects_custom_periods_per_year() -> None:
    base = np.array([0.006, -0.004, 0.007, -0.002, 0.005], dtype=float)
    returns = np.tile(base, 50)
    equity = _build_equity_from_returns(returns)
    benchmark = pd.Series(np.linspace(100.0, 102.0, len(equity)), index=equity.index)

    metrics_252 = Backtester._compute_metrics(
        equity,
        [],
        benchmark,
        risk_free_rate=RISK_FREE_RATE,
        periods_per_year=252,
    )
    metrics_360 = Backtester._compute_metrics(
        equity,
        [],
        benchmark,
        risk_free_rate=RISK_FREE_RATE,
        periods_per_year=360,
    )

    assert metrics_252["periods_per_year_used"] == 252
    assert metrics_360["periods_per_year_used"] == 360
    assert not math.isclose(metrics_252["cagr"], metrics_360["cagr"], rel_tol=0, abs_tol=1e-9)
    assert not math.isclose(
        metrics_252["volatility_ann"], metrics_360["volatility_ann"], rel_tol=0, abs_tol=1e-9
    )


def test_suite_ui_passes_timeframe_frequency_and_shared_rate_to_backtester() -> None:
    text = (SRC_DIR / "analysis" / "suite_ui.py").read_text(encoding="utf-8")

    assert 'st.session_state.get("rate_sidebar", RISK_FREE_RATE)' in text
    assert "periods_per_year_for_timeframe(timeframe)" in text
    assert periods_per_year_for_timeframe("1w") == 52
