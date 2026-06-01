"""Pytest smoke coverage for Step 3 risk modules."""

import numpy as np
import pandas as pd


def test_step3_risk_modules_smoke():
    from src.genesix.risk.correlation import CorrelationAnalyzer
    from src.genesix.risk.impact_analyzer import ImpactAnalyzer
    from src.genesix.risk.portfolio import PortfolioRiskAnalyzer
    from src.genesix.risk.risk_engine import GenesiXRiskEngine

    engine = GenesiXRiskEngine()
    impact = ImpactAnalyzer()
    corr = CorrelationAnalyzer()
    portfolio = PortfolioRiskAnalyzer()

    returns = np.random.normal(0.0005, 0.015, 252)
    assert engine.var_historical(returns, 0.95, 1) >= 0

    event = impact.event_impact_chain("fed_rate_hike_25bps")
    assert event["total_affected_assets"] > 4

    regime = corr.correlation_regime(["AAPL", "MSFT"], window=30)
    assert "regime" in regime

    returns_df = pd.DataFrame(
        np.random.normal(0.0005, 0.015, (252, 2)),
        columns=["SPY", "GLD"],
    )
    analytics = portfolio.portfolio_var(returns_df, {"SPY": 0.7, "GLD": 0.3}, 0.95, 1)
    assert "portfolio_var" in analytics
