"""
workers/tasks/analysis_task.py — Async company analysis via Celery.

Étape 13 — Frontend/Backend Boundary
Routes call  ``analyze_company.delay(...)``  and return a job_id immediately.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.analysis_task.analyze_company",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=240,
    time_limit=300,
)
def analyze_company(
    self,
    *,
    ticker: str,
    modules: list[str] | None = None,
) -> dict:
    """
    Run company fundamental analysis (DCF, ratios, peers, Monte Carlo)
    in a Celery worker.

    Returns a serialisable result dict.
    """
    try:
        from app.services.company_analysis_service import run_company_analysis_payload

        result = run_company_analysis_payload(
            ticker=ticker,
            modules=modules,
        )

        return {"status": "ok", **result}

    except Exception as exc:
        logger.error("Company analysis task failed for %s: %s", ticker, exc)
        return {"status": "error", "detail": str(exc)}
