"""
workers/tasks/ml_task.py — Async ML training via Celery.

Étape 5 complétion — moves heavy ML training off the HTTP cycle.
Routes call  ``train_model.delay(...)``  and return a job_id immediately.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.ml_task.train_model",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    soft_time_limit=600,
    time_limit=700,
)
def train_model(self, *, asset: str, model_type: str, horizon_days: int,
                period: str, seed: int, params: dict | None,
                include_baselines: bool = True) -> dict:
    """
    Train a model (+ baselines) in a Celery worker.

    Returns a summary dict.  Full artifacts are saved on disk.
    """
    from app.services.ml_service import (
        InvalidModelTypeError,
        PriceFetchError,
        execute_training_sync,
        persist_training_runs_sync,
    )

    try:
        result = execute_training_sync(
            asset=asset,
            model_type=model_type,
            horizon_days=horizon_days,
            period=period,
            seed=seed,
            params=params,
            include_baselines=include_baselines,
        )

        try:
            persist_training_runs_sync(result)
        except Exception:
            pass

        def _ser(r):
            if r is None:
                return None
            return {
                "run_id": str(r["run_id"]),
                "run_name": r["run_name"],
                "model_type": r["model_type"],
                "status": r["status"],
            }

        return {
            "status": "ok",
            "primary": _ser(result["primary"]),
            "baseline_naive": _ser(result.get("baseline_naive")),
            "baseline_linear": _ser(result.get("baseline_linear")),
        }

    except (InvalidModelTypeError, PriceFetchError) as exc:
        return {"status": "error", "detail": str(exc)}
    except Exception as exc:
        logger.error("ML training task failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
