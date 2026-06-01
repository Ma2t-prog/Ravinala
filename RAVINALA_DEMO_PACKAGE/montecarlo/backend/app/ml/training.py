"""
ml/training.py — Model training with walk-forward validation + baselines.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Centralisex all model training logic.

Supported model types:
  - random_forest    (scikit-learn RandomForestRegressor)
  - xgboost          (XGBRegressor)
  - lightgbm         (LGBMRegressor)
  - baseline_naive   (predict last observed return)
  - baseline_linear  (LinearRegression — mandatory simple baseline)

Hard rules (construction22032026.docx):
  - Temporal split ONLY — random split is FORBIDDEN
  - Walk-forward expanding window by default
  - Baselines mandatory alongside every model run
  - Model artifacts saved via joblib
  - All hyperparams, metrics, dataset refs persisted
  - LSTM and GARCH explicitly disabled
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.ml.features import build_features, dataset_hash, feature_columns
from app.ml.tracking import TrackedRun

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

ALLOWED_MODELS = frozenset(
    {"random_forest", "xgboost", "lightgbm", "baseline_naive", "baseline_linear"}
)
DISABLED_MODELS = frozenset({"lstm", "garch"})

ARTIFACT_ROOT = Path(os.getenv("ML_ARTIFACT_ROOT", "data/ml_artifacts"))
MLFLOW_EXPERIMENT = "ravinala-ml"

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "random_forest": {
        "n_estimators": 200,
        "max_depth": 8,
        "min_samples_leaf": 10,
        "random_state": 42,
        "n_jobs": -1,
    },
    "xgboost": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    },
    "lightgbm": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbose": -1,
    },
    "baseline_linear": {},
    "baseline_naive": {},
}


# ═══════════════════════════════════════════════════════════════════════════
# MODEL FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def _create_model(model_type: str, params: dict[str, Any]) -> Any:
    """Instantiate a model by type string.  Raises ValueError for unknown/disabled."""
    if model_type in DISABLED_MODELS:
        raise ValueError(
            f"Model type '{model_type}' is explicitly disabled. "
            "LSTM/GARCH require a proper pipeline (see construction22032026.docx Étape 8)."
        )
    if model_type not in ALLOWED_MODELS:
        raise ValueError(f"Unknown model type: {model_type}")

    if model_type == "random_forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(**params)

    if model_type == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(**params)

    if model_type == "lightgbm":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(**params)

    if model_type == "baseline_linear":
        return LinearRegression()

    if model_type == "baseline_naive":
        return None  # no sklearn model — handled inline

    raise ValueError(f"Cannot create model: {model_type}")


# ═══════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════

def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute standard regression + directional metrics."""
    mse = float(mean_squared_error(y_true, y_pred))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    # Directional accuracy
    dir_true = np.sign(y_true)
    dir_pred = np.sign(y_pred)
    dir_acc = float(np.mean(dir_true == dir_pred))

    # Information coefficient (rank correlation)
    from scipy.stats import spearmanr
    ic, _ = spearmanr(y_true, y_pred)
    ic = float(ic) if np.isfinite(ic) else 0.0

    return {
        "mse": round(mse, 8),
        "rmse": round(np.sqrt(mse), 8),
        "mae": round(mae, 8),
        "r2": round(r2, 6),
        "directional_accuracy": round(dir_acc, 4),
        "information_coefficient": round(ic, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
# WALK-FORWARD VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def walk_forward_split(
    n_samples: int,
    n_splits: int = 5,
    min_train_ratio: float = 0.5,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Generate expanding-window temporal splits.

    Each split uses all data up to split point for training and the
    next chunk for validation.  No shuffling, no future leakage.
    """
    min_train = int(n_samples * min_train_ratio)
    val_size = (n_samples - min_train) // n_splits
    if val_size < 10:
        # Not enough data for requested splits — fall back to single split
        split_point = int(n_samples * 0.8)
        return [(np.arange(split_point), np.arange(split_point, n_samples))]

    splits = []
    for i in range(n_splits):
        val_start = min_train + i * val_size
        val_end = min(val_start + val_size, n_samples)
        if val_end <= val_start:
            break
        train_idx = np.arange(val_start)
        val_idx = np.arange(val_start, val_end)
        splits.append((train_idx, val_idx))

    return splits


# ═══════════════════════════════════════════════════════════════════════════
# CORE TRAINING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def train_model(
    prices: pd.DataFrame,
    asset: str,
    model_type: str = "random_forest",
    horizon_days: int = 5,
    params: dict[str, Any] | None = None,
    n_splits: int = 5,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Train a model on the given price DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        OHLCV data with DatetimeIndex.
    asset : str
        Ticker/asset identifier.
    model_type : str
        One of ALLOWED_MODELS.
    horizon_days : int
        Prediction horizon in trading days.
    params : dict | None
        Hyperparams override; defaults from DEFAULT_PARAMS.
    n_splits : int
        Walk-forward validation splits.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with keys:
        run_id, run_name, model_type, asset, horizon_days, params,
        metrics_train, metrics_val, metrics_test, artifact_path,
        mlflow_run_id, dataset_hash, n_samples_*, status, duration_seconds,
        dataset_start, dataset_end, seed
    """
    start_time = time.time()
    run_id = _uuid.uuid4()
    run_name = f"{model_type}_{asset}_{horizon_days}d_{run_id.hex[:8]}"

    if params is None:
        params = dict(DEFAULT_PARAMS.get(model_type, {}))
    if "random_state" in DEFAULT_PARAMS.get(model_type, {}) and "random_state" not in params:
        params["random_state"] = seed

    logger.info("Training %s on %s (horizon=%dd, seed=%d)", model_type, asset, horizon_days, seed)

    # ── Build features ───────────────────────────────────────────────────
    feat_df = build_features(prices, horizon_days=horizon_days)
    # Drop rows where target is NaN (last horizon_days rows)
    feat_df = feat_df.dropna(subset=["fwd_return"])
    feat_cols = feature_columns(feat_df)

    X = feat_df[feat_cols].values
    y = feat_df["fwd_return"].values
    ds_hash = dataset_hash(feat_df)

    n_total = len(X)
    if n_total < 60:
        return _error_result(run_id, run_name, model_type, asset, horizon_days, params, seed,
                             "Insufficient data: need ≥60 rows, got {n_total}")

    # ── Temporal train/test split (last 20% = test hold-out) ─────────────
    test_size = max(int(n_total * 0.2), 20)
    X_dev, X_test = X[:-test_size], X[-test_size:]
    y_dev, y_test = y[:-test_size], y[-test_size:]

    # ── Walk-forward validation on dev set ───────────────────────────────
    splits = walk_forward_split(len(X_dev), n_splits=n_splits)

    val_metrics_list: list[dict] = []

    with TrackedRun(MLFLOW_EXPERIMENT, run_name=run_name) as tracked:
        tracked.log_params({
            "model_type": model_type,
            "asset": asset,
            "horizon_days": horizon_days,
            "seed": seed,
            "n_splits": len(splits),
            "n_total": n_total,
            **{f"hp_{k}": v for k, v in params.items()},
        })

        for fold_i, (train_idx, val_idx) in enumerate(splits):
            X_tr, y_tr = X_dev[train_idx], y_dev[train_idx]
            X_vl, y_vl = X_dev[val_idx], y_dev[val_idx]

            model = _create_model(model_type, params)

            if model_type == "baseline_naive":
                # Predict last known return for each validation row
                y_pred_vl = np.full(len(y_vl), y_tr[-1] if len(y_tr) > 0 else 0.0)
            else:
                model.fit(X_tr, y_tr)
                y_pred_vl = model.predict(X_vl)

            fold_metrics = _compute_metrics(y_vl, y_pred_vl)
            val_metrics_list.append(fold_metrics)
            tracked.log_metrics(
                {f"val_{k}": v for k, v in fold_metrics.items()},
                step=fold_i,
            )

        # ── Average validation metrics ───────────────────────────────────
        avg_val = _mean_metrics(val_metrics_list)

        # ── Retrain on full dev set for final model ──────────────────────
        final_model = _create_model(model_type, params)
        if model_type == "baseline_naive":
            y_pred_train = np.full(len(y_dev), y_dev[-1] if len(y_dev) > 0 else 0.0)
            y_pred_test = np.full(len(y_test), y_dev[-1] if len(y_dev) > 0 else 0.0)
        else:
            final_model.fit(X_dev, y_dev)
            y_pred_train = final_model.predict(X_dev)
            y_pred_test = final_model.predict(X_test)

        train_metrics = _compute_metrics(y_dev, y_pred_train)
        test_metrics = _compute_metrics(y_test, y_pred_test)

        tracked.log_metrics({f"train_{k}": v for k, v in train_metrics.items()})
        tracked.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        # ── Save artifact with training metadata ─────────────────────────
        artifact_meta = {
            "val_directional_accuracy": avg_val.get("directional_accuracy"),
            "val_mae":                  avg_val.get("mae"),
            "val_ic":                   avg_val.get("information_coefficient"),
            "test_directional_accuracy": test_metrics.get("directional_accuracy"),
            "model_type":               model_type,
            "feature_columns":          feat_cols,
            "horizon_days":             horizon_days,
            "asset":                    asset,
            "trained_at":               datetime.now(timezone.utc).isoformat(),
            "n_val_splits":             len(splits),
            # Q2.4 — Missing data transparency: record how many rows the pipeline saw
            # and how many were retained after target-NaN removal.  Feature NaNs in the
            # first ~63 rows (EWM/rolling warm-up) are NOT dropped — they are contained
            # in the training set only if the temporal split produces them in X_dev.
            # No forward-fill is applied at any stage (Q2.2 causal defensibility).
            "dataset_total_rows":       len(feat_df) + test_size,  # before dropna(target)
            "dataset_rows_after_dropna": int(n_total),             # after target NaN removal
            "training_samples":         int(len(X_dev)),
            "test_samples":             int(test_size),
            "feature_count":            int(len(feat_cols)),
            "fill_method":              "no_fill_applied_target_nans_dropped",
            # Q2.2 — Causal defensibility: all features are backward-looking by construction
            # (pct_change, ewm, rolling.std/mean, RSI, MACD, SMA, volume_ratio, calendar).
            # fwd_return is the ONLY forward-looking column and is excluded from feat_cols.
            "causal_fill_policy":       "backward_only_no_ffill_bfill_on_features",
        }
        artifact_path = _save_artifact(final_model, run_name, model_type, meta=artifact_meta)
        if artifact_path:
            tracked.log_artifact(str(artifact_path))

        tracked.set_tag("stage", "dev")
        mlflow_run_id = tracked.run_id

    duration = round(time.time() - start_time, 2)

    result = {
        "run_id": run_id,
        "run_name": run_name,
        "model_type": model_type,
        "asset": asset,
        "horizon_days": horizon_days,
        "params": params,
        "metrics_train": train_metrics,
        "metrics_val": avg_val,
        "metrics_test": test_metrics,
        "artifact_path": str(artifact_path) if artifact_path else None,
        "mlflow_run_id": mlflow_run_id,
        "mlflow_experiment": MLFLOW_EXPERIMENT,
        "dataset_hash": ds_hash,
        "dataset_start": str(feat_df.index.min()),
        "dataset_end": str(feat_df.index.max()),
        "n_samples_train": len(X_dev),
        "n_samples_val": sum(len(s[1]) for s in splits),
        "n_samples_test": len(X_test),
        "validation_method": "walk_forward",
        "n_splits": len(splits),
        "seed": seed,
        "status": "completed",
        "duration_seconds": duration,
        "feature_columns": feat_cols,
    }

    logger.info(
        "Training complete: %s | test_dir_acc=%.3f test_mae=%.6f (%.1fs)",
        run_name,
        test_metrics["directional_accuracy"],
        test_metrics["mae"],
        duration,
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════
# TRAIN WITH MANDATORY BASELINES
# ═══════════════════════════════════════════════════════════════════════════

def train_with_baselines(
    prices: pd.DataFrame,
    asset: str,
    model_type: str = "random_forest",
    horizon_days: int = 5,
    params: dict[str, Any] | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Train a model AND its mandatory baselines (naive + linear).

    Returns a dict with keys: primary, baseline_naive, baseline_linear,
    each containing the train_model() result.

    This enforces the construction22032026.docx rule:
    "NO model without baseline comparison."
    """
    primary = train_model(prices, asset, model_type, horizon_days, params, seed=seed)
    naive = train_model(prices, asset, "baseline_naive", horizon_days, seed=seed)
    linear = train_model(prices, asset, "baseline_linear", horizon_days, seed=seed)

    # Compute improvement over baselines
    primary_test = primary.get("metrics_test", {})
    naive_test = naive.get("metrics_test", {})
    linear_test = linear.get("metrics_test", {})

    comparison = {}
    for metric in ["mae", "directional_accuracy", "information_coefficient"]:
        pv = primary_test.get(metric, 0)
        nv = naive_test.get(metric, 0)
        lv = linear_test.get(metric, 0)
        comparison[f"{metric}_vs_naive"] = round(pv - nv, 6) if pv and nv else None
        comparison[f"{metric}_vs_linear"] = round(pv - lv, 6) if pv and lv else None

    return {
        "primary": primary,
        "baseline_naive": naive,
        "baseline_linear": linear,
        "comparison": comparison,
    }


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _save_artifact(
    model: Any,
    run_name: str,
    model_type: str,
    meta: dict[str, Any] | None = None,
) -> Path | None:
    """
    Save model artifact to disk via joblib.

    Payload format: {"model": model, "meta": meta_dict}
    Backward-compatible: load_artifact() strips the wrapper for old callers.
    """
    if model is None:  # baseline_naive has no sklearn model
        return None
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_ROOT / f"{run_name}.joblib"
    joblib.dump({"model": model, "meta": meta or {}}, path)
    logger.info("Artifact saved: %s", path)
    return path


def load_artifact(artifact_path: str) -> Any:
    """
    Load a model from a joblib artifact.

    Handles both:
    - New format: {"model": model, "meta": {...}}
    - Legacy format: raw model object
    """
    path = Path(artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    obj = joblib.load(path)
    if isinstance(obj, dict) and "model" in obj:
        return obj["model"]
    return obj  # legacy artifact — return as-is


def load_artifact_meta(artifact_path: str) -> dict[str, Any]:
    """
    Load training metadata from a joblib artifact.

    Returns {} for legacy artifacts (no embedded meta).
    Keys when present: val_directional_accuracy, val_mae, val_ic,
    model_type, feature_columns, horizon_days, asset, trained_at, n_val_splits.
    """
    path = Path(artifact_path)
    if not path.exists():
        return {}
    try:
        obj = joblib.load(path)
        if isinstance(obj, dict) and "meta" in obj:
            return obj["meta"]
    except Exception as exc:
        logger.warning("Could not read artifact meta from %s: %s", path, exc)
    return {}


def _mean_metrics(metrics_list: list[dict]) -> dict[str, float]:
    """Average a list of metric dicts."""
    if not metrics_list:
        return {}
    keys = metrics_list[0].keys()
    return {k: round(float(np.mean([m[k] for m in metrics_list if k in m])), 6) for k in keys}


def _error_result(
    run_id: _uuid.UUID, run_name: str, model_type: str,
    asset: str, horizon_days: int, params: dict, seed: int,
    error: str,
) -> dict[str, Any]:
    """Build a failed-run result dict."""
    return {
        "run_id": run_id,
        "run_name": run_name,
        "model_type": model_type,
        "asset": asset,
        "horizon_days": horizon_days,
        "params": params,
        "status": "failed",
        "error_message": error,
        "seed": seed,
        "metrics_train": None,
        "metrics_val": None,
        "metrics_test": None,
        "artifact_path": None,
        "mlflow_run_id": None,
    }
