"""
workers/tasks/risk_task.py — Async risk computation via Celery.

Étape 5 complétion — moves heavy risk computation off the HTTP cycle.
Routes call  ``compute_risk.delay(...)``  and return a job_id immediately.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.risk_task.compute_risk",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def compute_risk(self, *, asset: str, period: str, portfolio_value: float) -> dict:
    """
    Compute full governed risk report in a Celery worker.

    Returns a serialisable summary dict.
    """
    from app.services.risk_service import (
        RiskComputationError,
        RiskPriceFetchError,
        compute_risk_task_payload_sync,
    )

    try:
        return compute_risk_task_payload_sync(
            asset=asset,
            period=period,
            portfolio_value=portfolio_value,
        )
    except (RiskPriceFetchError, RiskComputationError) as exc:
        return {"status": "error", "detail": str(exc)}
    except Exception as exc:
        logger.error("Risk computation task failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
