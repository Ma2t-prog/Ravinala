"""
tests/test_ml_confidence_boundaries.py

Validates:
  1. _save_artifact() embeds meta in the joblib payload.
  2. load_artifact() returns the model (not the wrapper dict).
  3. load_artifact_meta() returns the meta dict.
  4. load_artifact_meta() returns {} for legacy artifacts (raw model).
  5. predict() populates confidence from artifact meta.
  6. predict() returns confidence=None for legacy artifacts without meta.
  7. predict() computes prediction_std for RandomForest models.
  8. predict() returns prediction_std=None for non-ensemble models.
  9. confidence_method is set correctly in both cases.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.training import _save_artifact, load_artifact, load_artifact_meta


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sample_prices(n: int = 120) -> pd.DataFrame:
    """Generate synthetic OHLCV data with DatetimeIndex."""
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "Open":   close * 0.999,
            "High":   close * 1.005,
            "Low":    close * 0.995,
            "Close":  close,
            "Volume": np.random.randint(1_000_000, 10_000_000, size=n).astype(float),
        },
        index=dates,
    )


SAMPLE_META = {
    "val_directional_accuracy": 0.5432,
    "val_mae": 0.0021,
    "val_ic": 0.12,
    "model_type": "random_forest",
    "feature_columns": ["ret_1d", "vol_5d"],
    "horizon_days": 5,
    "asset": "AAPL",
    "trained_at": "2026-03-24T10:00:00+00:00",
    "n_val_splits": 5,
}


# ── Artifact save/load contract tests ─────────────────────────────────────────

class TestArtifactMeta:
    def test_save_artifact_embeds_meta(self, tmp_path):
        model = LinearRegression()
        with patch("app.ml.training.ARTIFACT_ROOT", tmp_path):
            path = _save_artifact(model, "run_test", "baseline_linear", meta=SAMPLE_META)

        assert path is not None
        raw = joblib.load(path)
        assert isinstance(raw, dict), "Artifact must be a dict wrapper"
        assert "model" in raw
        assert "meta" in raw
        assert raw["meta"]["val_directional_accuracy"] == pytest.approx(0.5432)

    def test_load_artifact_returns_model_not_dict(self, tmp_path):
        model = LinearRegression()
        with patch("app.ml.training.ARTIFACT_ROOT", tmp_path):
            path = _save_artifact(model, "run_test", "baseline_linear", meta=SAMPLE_META)

        loaded = load_artifact(str(path))
        assert isinstance(loaded, LinearRegression), "load_artifact must return the model, not the dict"

    def test_load_artifact_meta_returns_meta(self, tmp_path):
        model = LinearRegression()
        with patch("app.ml.training.ARTIFACT_ROOT", tmp_path):
            path = _save_artifact(model, "run_test", "baseline_linear", meta=SAMPLE_META)

        meta = load_artifact_meta(str(path))
        assert meta["val_directional_accuracy"] == pytest.approx(0.5432)
        assert meta["model_type"] == "random_forest"  # SAMPLE_META fixture value
        assert meta["asset"] == "AAPL"

    def test_load_artifact_meta_empty_for_legacy_artifact(self, tmp_path):
        """Legacy artifacts saved as raw model (no dict wrapper) return {}."""
        model = LinearRegression()
        path = tmp_path / "legacy.joblib"
        joblib.dump(model, path)  # old format — raw model

        meta = load_artifact_meta(str(path))
        assert meta == {}, "Legacy artifact must return empty meta"

    def test_load_artifact_handles_legacy_raw_model(self, tmp_path):
        """load_artifact must still work on legacy (non-dict) artifacts."""
        model = LinearRegression()
        path = tmp_path / "legacy.joblib"
        joblib.dump(model, path)

        loaded = load_artifact(str(path))
        assert isinstance(loaded, LinearRegression)

    def test_save_artifact_none_model_returns_none(self, tmp_path):
        with patch("app.ml.training.ARTIFACT_ROOT", tmp_path):
            result = _save_artifact(None, "baseline_naive", "baseline_naive")
        assert result is None


# ── predict() confidence integration tests ────────────────────────────────────

class TestPredictConfidence:
    def _make_artifact(self, tmp_path, model, meta=None) -> str:
        path = tmp_path / "test_model.joblib"
        payload = {"model": model, "meta": meta or {}}
        joblib.dump(payload, path)
        return str(path)

    def _make_legacy_artifact(self, tmp_path, model) -> str:
        path = tmp_path / "legacy_model.joblib"
        joblib.dump(model, path)
        return str(path)

    def _mock_model(self, return_value: float = 0.005) -> MagicMock:
        """Mock sklearn-like model that accepts any X shape."""
        m = MagicMock()
        m.predict.return_value = np.array([return_value])
        # No estimators_ → no ensemble std
        del m.estimators_
        return m

    def _mock_rf(self, n_trees: int = 10, return_value: float = 0.005) -> MagicMock:
        """Mock RF model with estimators_ so prediction_std is computed."""
        rf = MagicMock()
        rf.predict.return_value = np.array([return_value])
        # Each tree returns a slightly different prediction
        trees = []
        for i in range(n_trees):
            t = MagicMock()
            t.predict.return_value = np.array([return_value + (i - n_trees / 2) * 0.001])
            trees.append(t)
        rf.estimators_ = trees
        return rf

    def test_predict_returns_confidence_from_meta(self, tmp_path):
        from app.ml.prediction import predict

        prices = _sample_prices()
        meta = {**SAMPLE_META, "val_directional_accuracy": 0.6100}
        model = self._mock_model()

        with patch("app.ml.prediction.load_artifact", return_value=model), \
             patch("app.ml.prediction.load_artifact_meta", return_value=meta), \
             patch("app.ml.prediction._persist_prediction_run"):
            result = predict(prices, "fake/path.joblib", "AAPL", horizon_days=5)

        assert result["confidence"] == pytest.approx(0.6100)
        assert result["confidence_method"] == "val_directional_accuracy"

    def test_predict_confidence_none_for_legacy_artifact(self, tmp_path):
        from app.ml.prediction import predict

        prices = _sample_prices()
        model = self._mock_model()

        with patch("app.ml.prediction.load_artifact", return_value=model), \
             patch("app.ml.prediction.load_artifact_meta", return_value={}), \
             patch("app.ml.prediction._persist_prediction_run"):
            result = predict(prices, "fake/path.joblib", "AAPL", horizon_days=5)

        assert result["confidence"] is None
        assert result["confidence_method"] == "not_available"

    def test_predict_computes_prediction_std_for_rf(self, tmp_path):
        from app.ml.prediction import predict

        prices = _sample_prices()
        rf = self._mock_rf(n_trees=10)
        meta = {**SAMPLE_META, "val_directional_accuracy": 0.55}

        with patch("app.ml.prediction.load_artifact", return_value=rf), \
             patch("app.ml.prediction.load_artifact_meta", return_value=meta), \
             patch("app.ml.prediction._persist_prediction_run"):
            result = predict(prices, "fake/path.joblib", "AAPL", horizon_days=5)

        assert result["prediction_std"] is not None, "RF must have prediction_std"
        assert isinstance(result["prediction_std"], float)
        assert result["prediction_std"] >= 0.0

    def test_predict_prediction_std_none_for_linear(self, tmp_path):
        from app.ml.prediction import predict

        prices = _sample_prices()
        model = self._mock_model()  # no estimators_
        meta = {**SAMPLE_META, "val_directional_accuracy": 0.52}

        with patch("app.ml.prediction.load_artifact", return_value=model), \
             patch("app.ml.prediction.load_artifact_meta", return_value=meta), \
             patch("app.ml.prediction._persist_prediction_run"):
            result = predict(prices, "fake/path.joblib", "AAPL", horizon_days=5)

        assert result["prediction_std"] is None, "Non-ensemble model has no std"

    def test_predict_result_has_all_required_keys(self, tmp_path):
        from app.ml.prediction import predict

        prices = _sample_prices()
        model = self._mock_model()

        with patch("app.ml.prediction.load_artifact", return_value=model), \
             patch("app.ml.prediction.load_artifact_meta", return_value=SAMPLE_META), \
             patch("app.ml.prediction._persist_prediction_run"):
            result = predict(prices, "fake/path.joblib", "TEST", horizon_days=5)

        required_keys = {
            "asset", "predicted_return", "predicted_direction",
            "confidence", "confidence_method", "prediction_std",
            "features_hash", "prediction_date", "target_date",
            "horizon_days", "artifact_path", "run_id",
        }
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"
