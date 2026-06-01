"""
ml/prediction.py — Prediction service with DB logging.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Every prediction is persisted to ml_predictions for audit.
Links prediction → originating run for traceability.
actual_return is backfilled when the target date is reached.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.ml.features import build_features, dataset_hash, feature_columns
from app.ml.training import load_artifact, load_artifact_meta

logger = logging.getLogger(__name__)


def predict(
    prices: pd.DataFrame,
    artifact_path: str,
    asset: str,
    horizon_days: int = 5,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Run inference using a saved model artifact.

    Parameters
    ----------
    prices : pd.DataFrame
        Recent OHLCV data (must be enough for feature lookback ≈ 63 rows minimum).
    artifact_path : str
        Path to the joblib model artifact.
    asset : str
        Ticker / asset identifier.
    horizon_days : int
        Prediction horizon in trading days.
    run_id : str | None
        Optional originating ML run identifier. When provided, the prediction
        is persisted to the backend ML audit table synchronously.

    Returns
    -------
    dict with: predicted_return, predicted_direction, confidence,
               features_hash, prediction_date, target_date, horizon_days, asset
    """
    model = load_artifact(artifact_path)
    meta  = load_artifact_meta(artifact_path)

    feat_df = build_features(prices, horizon_days=horizon_days)
    feat_cols = feature_columns(feat_df)

    # Use the last available row (most recent features)
    if len(feat_df) == 0:
        raise ValueError("Not enough price data to compute features")

    last_row = feat_df[feat_cols].iloc[[-1]]
    X = last_row.values

    y_pred = float(model.predict(X)[0])
    direction = "up" if y_pred > 0 else ("down" if y_pred < 0 else "flat")

    now = datetime.now(timezone.utc)
    target_date = now + timedelta(days=horizon_days)

    f_hash = hashlib.sha256(last_row.values.tobytes()).hexdigest()[:16]

    # ── Confidence: historical directional accuracy from walk-forward val ──
    # Source: avg directional accuracy across out-of-fold validation splits.
    # This is an honest estimate: computed on data the model never saw in training.
    # It does NOT represent certainty about this specific prediction.
    val_dir_acc = meta.get("val_directional_accuracy")
    confidence  = round(float(val_dir_acc), 4) if val_dir_acc is not None else None
    confidence_method = (
        "val_directional_accuracy"  # walk-forward out-of-fold historical accuracy
        if confidence is not None
        else "not_available"        # legacy artifact without embedded meta
    )

    # ── Ensemble uncertainty: std across trees (RandomForest only) ────────
    # For RF, each tree produces an independent prediction.
    # High std → the ensemble disagrees → lower effective confidence.
    # XGBoost/LightGBM: tree-level extraction not standardly available; skipped.
    prediction_std: float | None = None
    if hasattr(model, "estimators_"):
        try:
            tree_preds = np.array([t.predict(X)[0] for t in model.estimators_])
            prediction_std = round(float(tree_preds.std()), 8)
        except Exception as exc:
            logger.debug("Could not compute ensemble std: %s", exc)

    result = {
        "asset":                  asset,
        "predicted_return":       round(y_pred, 8),
        "predicted_direction":    direction,
        "confidence":             confidence,
        "confidence_method":      confidence_method,
        "prediction_std":         prediction_std,
        "features_hash":          f_hash,
        "prediction_date":        now.isoformat(),
        "target_date":            target_date.isoformat(),
        "horizon_days":           horizon_days,
        "artifact_path":          artifact_path,
        "run_id":                 run_id,
    }

    logger.info(
        "Prediction: %s %dd → %.4f%% (%s)",
        asset, horizon_days, y_pred * 100, direction,
    )

    _persist_prediction_run(run_id, result)

    return result


def _persist_prediction_run(run_id: str | None, prediction: dict[str, Any]) -> None:
    """
    Persist prediction to the backend ML prediction log when a run_id is available.

    Graceful no-op if the backend DB is not configured.
    """
    if not run_id:
        return

    try:
        log_prediction_to_db_sync(run_id, prediction)
    except Exception as exc:
        logger.warning("Failed to persist prediction for %s: %s", prediction["asset"], exc)


async def log_prediction_to_db(
    run_id: str,
    prediction: dict[str, Any],
) -> None:
    """
    Persist a prediction to the ml_predictions table.
    Graceful no-op if DATABASE_URL not configured.
    """
    try:
        from app.db import base as _db
        if _db._session_factory is None:
            return

        from app.db.models import MLPrediction
        from datetime import datetime

        async with _db._session_factory() as session:
            row = MLPrediction(
                run_id=run_id,
                asset=prediction["asset"],
                prediction_date=datetime.fromisoformat(prediction["prediction_date"]),
                target_date=datetime.fromisoformat(prediction["target_date"]),
                horizon_days=prediction["horizon_days"],
                predicted_return=prediction["predicted_return"],
                predicted_direction=prediction["predicted_direction"],
                confidence=prediction.get("confidence"),
                features_hash=prediction.get("features_hash"),
            )
            session.add(row)
            await session.commit()
            logger.debug("Prediction logged to DB for %s", prediction["asset"])
    except Exception as exc:
        logger.warning("Failed to log prediction to DB: %s", exc)


def log_prediction_to_db_sync(
    run_id: str,
    prediction: dict[str, Any],
) -> None:
    """Synchronous wrapper for thread-pool based inference paths."""
    asyncio.run(log_prediction_to_db(run_id, prediction))


async def log_run_to_db(result: dict[str, Any]) -> None:
    """
    Persist a training run result to the ml_runs table.
    Graceful no-op if DATABASE_URL not configured.
    """
    try:
        from app.db import base as _db
        if _db._session_factory is None:
            return

        from app.db.models import MLRun
        from datetime import datetime

        async with _db._session_factory() as session:
            run = MLRun(
                id=result["run_id"],
                run_name=result["run_name"],
                model_type=result["model_type"],
                asset=result["asset"],
                horizon_days=result["horizon_days"],
                params=result.get("params"),
                dataset_hash=result.get("dataset_hash"),
                n_samples_train=result.get("n_samples_train"),
                n_samples_val=result.get("n_samples_val"),
                n_samples_test=result.get("n_samples_test"),
                validation_method=result.get("validation_method", "walk_forward"),
                n_splits=result.get("n_splits"),
                seed=result.get("seed"),
                metrics_train=result.get("metrics_train"),
                metrics_val=result.get("metrics_val"),
                metrics_test=result.get("metrics_test"),
                artifact_path=result.get("artifact_path"),
                mlflow_run_id=result.get("mlflow_run_id"),
                mlflow_experiment=result.get("mlflow_experiment"),
                status=result.get("status", "completed"),
                error_message=result.get("error_message"),
                duration_seconds=result.get("duration_seconds"),
            )
            session.add(run)
            await session.commit()
            logger.debug("ML run logged to DB: %s", result["run_name"])
    except Exception as exc:
        logger.warning("Failed to log ML run to DB: %s", exc)
