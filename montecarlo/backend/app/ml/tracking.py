"""
ml/tracking.py — MLflow integration with graceful degradation.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Wraps MLflow calls so the training pipeline works with or without
MLflow installed / configured.  When MLflow is unavailable, operations
are logged via stdlib logging only.

To activate MLflow:
  pip install mlflow
  Set MLFLOW_TRACKING_URI in environment (default: ./mlruns)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# MLFLOW AVAILABILITY
# ═══════════════════════════════════════════════════════════════════════════

_mlflow = None
_mlflow_available = False

try:
    import mlflow as _mlflow  # type: ignore[no-redef]
    _mlflow_available = True
except ImportError:
    pass


def is_available() -> bool:
    return _mlflow_available


def _tracking_uri() -> str:
    return os.getenv("MLFLOW_TRACKING_URI", "./mlruns")


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def ensure_experiment(name: str) -> str | None:
    """Create or get an MLflow experiment.  Returns experiment_id or None."""
    if not _mlflow_available:
        return None
    _mlflow.set_tracking_uri(_tracking_uri())
    exp = _mlflow.get_experiment_by_name(name)
    if exp is None:
        return _mlflow.create_experiment(name)
    return exp.experiment_id


# ═══════════════════════════════════════════════════════════════════════════
# RUN LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════

class TrackedRun:
    """
    Context manager around an MLflow run.

    Usage::

        with TrackedRun("ravinala-ml", run_name="rf_SPY_5d") as run:
            run.log_params({"n_estimators": 200})
            run.log_metrics({"mse": 0.002, "dir_acc": 0.54})
            run.log_artifact("/path/to/model.joblib")
            mlflow_run_id = run.run_id   # or None if MLflow unavailable
    """

    def __init__(self, experiment_name: str, run_name: str):
        self._experiment_name = experiment_name
        self._run_name = run_name
        self._run = None
        self.run_id: str | None = None

    def __enter__(self) -> "TrackedRun":
        if _mlflow_available:
            exp_id = ensure_experiment(self._experiment_name)
            self._run = _mlflow.start_run(
                experiment_id=exp_id,
                run_name=self._run_name,
            )
            self.run_id = self._run.info.run_id
            logger.info("MLflow run started: %s (experiment=%s)", self.run_id, self._experiment_name)
        else:
            logger.info(
                "MLflow unavailable — run '%s' tracked via logging only",
                self._run_name,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if _mlflow_available and self._run is not None:
            status = "FAILED" if exc_type else "FINISHED"
            _mlflow.end_run(status=status)
            logger.info("MLflow run ended: %s (%s)", self.run_id, status)

    def log_params(self, params: dict[str, Any]) -> None:
        if _mlflow_available:
            _mlflow.log_params(params)
        logger.info("Params: %s", params)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if _mlflow_available:
            _mlflow.log_metrics(metrics, step=step)
        logger.info("Metrics: %s", metrics)

    def log_artifact(self, path: str) -> None:
        if _mlflow_available:
            _mlflow.log_artifact(path)
        logger.info("Artifact logged: %s", path)

    def set_tag(self, key: str, value: str) -> None:
        if _mlflow_available:
            _mlflow.set_tag(key, value)
