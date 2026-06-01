from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml import prediction as prediction_service
from app.routes import ml as ml_routes
from app.routes.ml import PredictRequest


class _Model:
    def predict(self, X: np.ndarray) -> np.ndarray:
        assert X.shape[1] == 2
        return np.array([0.0125])


def _feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feat_one": [0.1, 0.2, 0.3],
            "feat_two": [0.4, 0.5, 0.6],
        }
    )


def _patch_prediction_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prediction_service, "load_artifact", lambda _: _Model())
    monkeypatch.setattr(
        prediction_service,
        "build_features",
        lambda prices, horizon_days=5: _feature_frame(),
    )
    monkeypatch.setattr(
        prediction_service,
        "feature_columns",
        lambda frame: ["feat_one", "feat_two"],
    )


def test_prediction_module_no_longer_depends_on_src_db_models() -> None:
    source = Path(prediction_service.__file__).read_text(encoding="utf-8")
    assert "src.db.models" not in source


def test_predict_persists_via_backend_wrapper_when_run_id_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_prediction_dependencies(monkeypatch)
    captured: dict[str, object] = {}

    def _persist(run_id: str, prediction: dict[str, object]) -> None:
        captured["run_id"] = run_id
        captured["prediction"] = dict(prediction)

    monkeypatch.setattr(prediction_service, "log_prediction_to_db_sync", _persist)

    result = prediction_service.predict(
        prices=pd.DataFrame(),
        artifact_path="artifact.joblib",
        asset="AAPL",
        horizon_days=5,
        run_id="run-123",
    )

    assert result["run_id"] == "run-123"
    assert captured["run_id"] == "run-123"
    assert captured["prediction"]["asset"] == "AAPL"
    assert captured["prediction"]["predicted_direction"] == "up"


def test_predict_without_run_id_skips_backend_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_prediction_dependencies(monkeypatch)
    called = {"value": False}

    def _persist(run_id: str, prediction: dict[str, object]) -> None:
        called["value"] = True

    monkeypatch.setattr(prediction_service, "log_prediction_to_db_sync", _persist)

    result = prediction_service.predict(
        prices=pd.DataFrame(),
        artifact_path="artifact.joblib",
        asset="MSFT",
        horizon_days=10,
        run_id=None,
    )

    assert result["run_id"] is None
    assert called["value"] is False


@pytest.mark.asyncio
async def test_predict_route_passes_run_id_into_prediction_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _run_prediction(
        *,
        asset: str,
        run_id: str,
        horizon_days: int,
        period: str,
        executor=None,
    ) -> dict[str, object]:
        captured["asset"] = asset
        captured["horizon_days"] = horizon_days
        captured["run_id"] = run_id
        captured["period"] = period
        return ml_routes.PredictionResult(
            asset=asset,
            predicted_return=0.02,
            predicted_direction="up",
            confidence=None,
            prediction_date="2026-03-23T12:00:00+00:00",
            target_date="2026-03-28T12:00:00+00:00",
            horizon_days=horizon_days,
            run_id=run_id,
        )

    monkeypatch.setattr(ml_routes, "run_prediction", _run_prediction)

    response = await ml_routes.predict_endpoint(
        PredictRequest(asset="AAPL", run_id="run-123", horizon_days=5, period="1y")
    )

    assert captured["run_id"] == "run-123"
    assert captured["period"] == "1y"
    assert response.data.run_id == "run-123"
    assert response.data.asset == "AAPL"
