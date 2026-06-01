"""Pytest smoke coverage for Step 5 dashboard components."""

from __future__ import annotations

import importlib.util
import sys
import types

import numpy as np
import pandas as pd
import pytest


def _install_streamlit_stub() -> None:
    if "streamlit" in sys.modules:
        return

    st_stub = types.ModuleType("streamlit")
    st_stub.markdown = lambda *args, **kwargs: None
    st_stub.write = lambda *args, **kwargs: None
    st_stub.columns = lambda n=1, **kwargs: [types.SimpleNamespace(markdown=lambda *a, **k: None, write=lambda *a, **k: None) for _ in range(n)]
    st_stub.container = lambda *args, **kwargs: types.SimpleNamespace()
    st_stub.cache_data = lambda **kwargs: (lambda f: f)
    st_stub.cache_resource = lambda **kwargs: (lambda f: f)
    st_stub.metric = lambda *args, **kwargs: None
    st_stub.plotly_chart = lambda *args, **kwargs: None
    sys.modules["streamlit"] = st_stub


def _has_real_plotly() -> bool:
    try:
        spec = importlib.util.find_spec("plotly")
    except ValueError:
        module = sys.modules.get("plotly")
        return bool(module) and not getattr(module, "__RAVINALA_PLOTLY_STUB__", False)
    module = sys.modules.get("plotly")
    if module is not None and getattr(module, "__RAVINALA_PLOTLY_STUB__", False):
        return False
    return spec is not None


_HAS_PLOTLY = _has_real_plotly()


@pytest.mark.skipif(not _HAS_PLOTLY, reason="Optional dashboard dependency 'plotly' is not installed in the validation venv")
def test_step5_component_library_smoke():
    _install_streamlit_stub()

    from genesix.dashboard.components import (
        plot_correlation_matrix,
        plot_impact_chain,
        plot_investment_cone,
        plot_performance_heatmap,
        plot_return_distribution,
        plot_scenario_waterfall,
        plot_shap_waterfall,
        plot_stress_test_results,
        render_alert_badge,
        render_kpi_row,
        render_scenario_cards,
    )
    from genesix.dashboard.theme import GENESIX_COLORS, GENESIX_TEMPLATE, apply_theme

    assert len(GENESIX_COLORS) > 0
    assert GENESIX_TEMPLATE.layout is not None
    apply_theme()

    render_kpi_row([{"label": "PnL", "value": "+1.2%"}])
    render_scenario_cards([{"name": "Base", "probability": 0.5, "return_pct": 1.0, "final_value": 101.0}])
    render_alert_badge("yellow")

    returns = np.random.normal(0.001, 0.02, 252)
    assert plot_return_distribution(returns, height=400) is not None
    assert plot_scenario_waterfall(
        [
            {"name": "Crash", "probability": 0.05, "return_pct": -15.0, "final_value": 85.0},
            {"name": "Base", "probability": 0.60, "return_pct": 5.0, "final_value": 105.0},
        ],
        base_value=100.0,
    ) is not None
    assert plot_investment_cone(np.random.normal(100, 5, (50, 10))) is not None
    assert plot_correlation_matrix(np.random.uniform(-1, 1, (5, 5))) is not None
    assert plot_performance_heatmap(np.random.normal(0, 0.02, (50, 5))) is not None
    assert plot_stress_test_results(100.0, {"Fed Hikes": -2.5, "Soft Landing": 3.1}) is not None
    assert plot_impact_chain(
        "Fed Hikes",
        [
            {"from": "Event", "to": "Equities", "strength": -8.5},
            {"from": "Event", "to": "Vol", "strength": 12.0},
        ],
    ) is not None
    assert plot_shap_waterfall(["Momentum", "Volatility"], [0.045, -0.012], base_value=0.001) is not None
