"""
workers/tasks/portfolio_task.py — Async portfolio optimization via Celery.

Étape 13 — Frontend/Backend Boundary
Routes call  ``optimize_portfolio.delay(...)``  and return a job_id immediately.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.portfolio_task.optimize_portfolio",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=180,
    time_limit=240,
)
def optimize_portfolio(
    self,
    *,
    tickers: list,
    objective: str = "max_sharpe",
    risk_free_rate: float | None = None,
    lookback_days: int = 252,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
) -> dict:
    """
    Run portfolio optimization in a Celery worker.

    Returns a serialisable result dict.
    """
    try:
        from app.services.portfolio_optimization_service import run_portfolio_optimization_payload

        result = run_portfolio_optimization_payload(
            tickers=tickers,
            objective=objective,
            risk_free_rate=risk_free_rate,
            lookback_days=lookback_days,
            max_weight=max_weight,
            min_weight=min_weight,
        )

        return {
            "status": "ok",
            **result,
        }

    except Exception as exc:
        logger.error("Portfolio optimization task failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
