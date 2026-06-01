"""Pytest smoke coverage for Step 4 ML modules."""

import numpy as np
import pandas as pd


def test_step4_ml_modules_smoke():
    from sklearn.ensemble import RandomForestRegressor

    from src.genesix.ml.anomaly_detector import AnomalyDetector
    from src.genesix.ml.explainer import PredictionExplainer
    from src.genesix.ml.prediction_engine import GenesiXPredictor, ModelTrainer

    trainer = ModelTrainer("random_forest")
    x_train = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
    y_train = pd.Series(np.random.randn(100))
    result = trainer.train(x_train, y_train)
    assert "converged" in result

    predictor = GenesiXPredictor(models=["random_forest"], n_bootstrap=100)
    assert list(predictor.models.keys()) == ["random_forest"]

    detector = AnomalyDetector()
    alert = detector.composite_alert_level()
    assert "level" in alert and "score" in alert

    explainer = PredictionExplainer()
    model = RandomForestRegressor(n_estimators=5, random_state=42)
    model.fit(x_train, y_train)
    importance_df = explainer.feature_importance_global(model, x_train)
    assert len(importance_df) == x_train.shape[1]
