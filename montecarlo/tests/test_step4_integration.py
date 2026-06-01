"""Pytest integration smoke across GenesiX Steps 1-4."""

import numpy as np
import pandas as pd


def test_step4_end_to_end_smoke():
    from src.genesix import __version__
    from src.genesix.data.feature_store import FeatureStore
    from src.genesix.data.market_fetcher import MarketDataFetcher
    from src.genesix.ml.anomaly_detector import AnomalyDetector
    from src.genesix.ml.explainer import PredictionExplainer
    from src.genesix.ml.prediction_engine import GenesiXPredictor
    from src.genesix.risk.correlation import CorrelationAnalyzer
    from src.genesix.risk.impact_analyzer import ImpactAnalyzer
    from src.genesix.risk.portfolio import PortfolioRiskAnalyzer
    from src.genesix.risk.risk_engine import GenesiXRiskEngine

    assert __version__

    fs = FeatureStore()
    mf = MarketDataFetcher()
    assert fs is not None and mf is not None

    engine = GenesiXRiskEngine()
    returns = np.random.normal(0.0005, 0.015, 252)
    assert engine.var_historical(returns, 0.95, 1) >= 0

    impact = ImpactAnalyzer()
    assert impact.event_impact_chain("fed_rate_hike_25bps")["total_affected_assets"] > 0

    corr = CorrelationAnalyzer()
    assert "regime" in corr.correlation_regime(["AAPL", "MSFT"], window=30)

    returns_df = pd.DataFrame(
        np.random.normal(0.0005, 0.015, (252, 2)),
        columns=["SPY", "GLD"],
    )
    portfolio = PortfolioRiskAnalyzer()
    assert "portfolio_var" in portfolio.portfolio_var(returns_df, {"SPY": 0.7, "GLD": 0.3}, 0.95, 1)

    predictor = GenesiXPredictor(models=["random_forest"], n_bootstrap=100)
    assert list(predictor.models.keys()) == ["random_forest"]

    detector = AnomalyDetector()
    assert "level" in detector.composite_alert_level()

    explainer = PredictionExplainer()
    assert explainer is not None
