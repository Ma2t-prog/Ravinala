"""
Tests de non-régression — agents core (MarketAgent, RiskAgent, AnalysisAgent).
Aucun appel réseau : on teste les fonctions pures et les fallbacks déterministes.
"""

import math
import pytest
import sys
import os
from unittest import mock

# Mock langgraph before importing anything that depends on it
sys.modules.setdefault("langgraph", mock.MagicMock())
sys.modules.setdefault("langgraph.config", mock.MagicMock())
sys.modules.setdefault("langgraph.graph", mock.MagicMock())
sys.modules.setdefault("langgraph.graph.message", mock.MagicMock())

# Ajouter le backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Imports des fonctions pures ────────────────────────────────────────────────
from app.agents.nodes.market_agent   import _synthetic_returns, _std, _beta  # noqa: E402
from app.agents.nodes.risk_agent     import (  # noqa: E402
    _var_parametric, _cvar_parametric,
    _max_drawdown, _sharpe, _pool_returns,
)
from app.agents.nodes.analysis_agent import _score_ticker, _deterministic_fallback  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# MarketAgent — fonctions pures
# ══════════════════════════════════════════════════════════════════════════════

class TestMarketAgentPure:

    def test_synthetic_returns_length(self):
        r = _synthetic_returns("AAPL", 30)
        assert len(r) == 30

    def test_synthetic_returns_deterministic(self):
        """Même ticker → mêmes returns."""
        assert _synthetic_returns("MSFT") == _synthetic_returns("MSFT")

    def test_synthetic_returns_differ_by_ticker(self):
        assert _synthetic_returns("AAPL") != _synthetic_returns("MSFT")

    def test_synthetic_returns_no_zeros(self):
        r = _synthetic_returns("GOOGL")
        assert all(v != 0.0 for v in r)

    def test_std_basic(self):
        vals = [0.01, -0.01, 0.02, -0.02]
        s = _std(vals)
        assert s > 0

    def test_std_empty(self):
        assert _std([]) == 0.0

    def test_std_single(self):
        assert _std([0.05]) == 0.0

    def test_beta_spy_equal(self):
        """Beta d'un ticker identique au SPY doit être ≈ 1."""
        r = [0.01, -0.02, 0.015, -0.005, 0.012] * 6
        b = _beta(r, r)
        assert abs(b - 1.0) < 0.01

    def test_beta_zero_variance(self):
        """Si SPY ne bouge pas, retourner 1.0 sans crash."""
        spy = [0.0] * 10
        ticker = [0.01] * 10
        assert _beta(ticker, spy) == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# RiskAgent — fonctions pures
# ══════════════════════════════════════════════════════════════════════════════

SAMPLE_RETURNS = [
    0.012, -0.008, 0.015, -0.023, 0.009, 0.004, -0.011,
    0.018, -0.006, 0.013, -0.019, 0.007, 0.002, -0.014,
    0.021, -0.003, 0.010, -0.017, 0.008, 0.005, -0.009,
    0.016, -0.012, 0.011, 0.006,  -0.015, 0.020, -0.004, 0.014, -0.007,
]


class TestRiskAgentPure:

    def test_var_negative(self):
        """VaR doit être négatif (c'est une perte)."""
        var = _var_parametric(SAMPLE_RETURNS)
        assert var < 0

    def test_cvar_leq_var(self):
        """CVaR doit être ≤ VaR (perte conditionnelle plus sévère)."""
        var  = _var_parametric(SAMPLE_RETURNS)
        cvar = _cvar_parametric(SAMPLE_RETURNS)
        assert cvar <= var

    def test_var_99_leq_var_95(self):
        """VaR 99% doit être plus négatif que VaR 95%."""
        v95 = _var_parametric(SAMPLE_RETURNS, 0.95)
        v99 = _var_parametric(SAMPLE_RETURNS, 0.99)
        assert v99 <= v95

    def test_max_drawdown_negative_or_zero(self):
        dd = _max_drawdown(SAMPLE_RETURNS)
        assert dd <= 0

    def test_max_drawdown_all_positive(self):
        """Série toujours positive → drawdown proche de 0."""
        dd = _max_drawdown([0.01] * 20)
        assert dd == 0.0

    def test_sharpe_positive_series(self):
        """Série avec variance positive et rendement > RF → Sharpe positif."""
        pos = [0.005 + (i % 3) * 0.001 for i in range(30)]
        s = _sharpe(pos, annual_rf=0.02)
        assert s > 0

    def test_sharpe_empty(self):
        assert _sharpe([]) == 0.0

    def test_pool_returns_equal_weight(self):
        """Pool de 2 tickers identiques → même série."""
        market = {
            "A": {"returns_30d": [0.01, 0.02, -0.01]},
            "B": {"returns_30d": [0.01, 0.02, -0.01]},
        }
        pooled = _pool_returns(market)
        assert pooled == [0.01, 0.02, -0.01]

    def test_pool_returns_empty_market(self):
        assert _pool_returns({}) == []

    def test_no_hardcoded_values(self):
        """Vérifier que le résultat change avec des données différentes."""
        r1 = [0.01] * 30
        r2 = [-0.02] * 30
        assert _var_parametric(r1) != _var_parametric(r2)


# ══════════════════════════════════════════════════════════════════════════════
# AnalysisAgent — fonctions pures
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalysisAgentPure:

    def test_score_in_range(self):
        info = {"trailingPE": 18, "priceToBook": 2.5, "returnOnEquity": 0.18,
                "debtToEquity": 45, "revenueGrowth": 0.12, "profitMargins": 0.15}
        result = _score_ticker("AAPL", info)
        assert 0 <= result["score"] <= 100

    def test_recommendation_valid(self):
        info = {"trailingPE": 18, "returnOnEquity": 0.25}
        result = _score_ticker("TEST", info)
        assert result["recommendation"] in {"BUY", "SELL", "HOLD"}

    def test_good_fundamentals_buy(self):
        """Fondamentaux excellents → BUY."""
        info = {
            "trailingPE": 12, "priceToBook": 1.2, "returnOnEquity": 0.28,
            "debtToEquity": 20, "revenueGrowth": 0.25, "profitMargins": 0.22,
            "currentRatio": 2.5,
        }
        result = _score_ticker("GOOD", info)
        assert result["recommendation"] == "BUY"
        assert result["score"] >= 68

    def test_bad_fundamentals_sell(self):
        """Fondamentaux mauvais → SELL."""
        info = {
            "trailingPE": 80, "priceToBook": 12, "returnOnEquity": -0.05,
            "debtToEquity": 300, "revenueGrowth": -0.15, "profitMargins": -0.08,
        }
        result = _score_ticker("BAD", info)
        assert result["recommendation"] == "SELL"
        assert result["score"] <= 40

    def test_empty_info_hold(self):
        """Aucune donnée → score neutre → HOLD."""
        result = _score_ticker("EMPTY", {})
        assert result["score"] == 50.0
        assert result["recommendation"] == "HOLD"

    def test_reasons_populated(self):
        info = {"trailingPE": 10, "returnOnEquity": 0.30, "profitMargins": 0.25}
        result = _score_ticker("X", info)
        assert len(result["reasons"]) >= 3

    def test_fallback_deterministic(self):
        """Même ticker → même résultat."""
        r1 = _deterministic_fallback("AAPL")
        r2 = _deterministic_fallback("AAPL")
        assert r1["score"] == r2["score"]
        assert r1["recommendation"] == r2["recommendation"]

    def test_fallback_different_tickers(self):
        """Tickers différents → scores différents."""
        r1 = _deterministic_fallback("AAPL")
        r2 = _deterministic_fallback("MSFT")
        assert r1["score"] != r2["score"]

    def test_no_demo_source_when_data_present(self):
        """Le scoring yfinance ne doit jamais retourner source=demo_fallback."""
        info = {"trailingPE": 20}
        result = _score_ticker("X", info)
        assert result.get("source") != "demo_fallback"


# ══════════════════════════════════════════════════════════════════════════════
# Intégration : pipeline Market → Risk
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:

    def test_synthetic_returns_feed_risk(self):
        """Les returns synthétiques de MarketAgent doivent produire un VaR valide."""
        returns = _synthetic_returns("AAPL", 30)
        var = _var_parametric(returns)
        assert isinstance(var, float)
        assert math.isfinite(var)

    def test_pool_returns_then_var(self):
        market = {
            "AAPL": {"returns_30d": _synthetic_returns("AAPL")},
            "MSFT": {"returns_30d": _synthetic_returns("MSFT")},
        }
        pooled = _pool_returns(market)
        var    = _var_parametric(pooled)
        cvar   = _cvar_parametric(pooled)
        dd     = _max_drawdown(pooled)

        assert var < 0
        assert cvar <= var
        assert dd <= 0
