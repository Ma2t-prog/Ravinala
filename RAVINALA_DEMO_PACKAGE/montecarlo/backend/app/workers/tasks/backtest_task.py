"""
workers/tasks/backtest_task.py — Async backtest execution via Celery.

Étape 5 complétion — moves heavy backtest computation off the HTTP cycle.
Routes call  ``run_backtest_task.delay(...)``  and return a job_id immediately.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.backtest_task.run_backtest",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
)
def run_backtest(self, *, assets: list[str], strategy: str, benchmark: str,
                period: str, initial_capital: float, commission_bps: float,
                slippage_bps: float, risk_free_rate: float | None = None,
                seed: int | None = None, params: dict | None = None) -> dict:
    """
    Execute a full backtest (primary + baselines) in a Celery worker.

    Returns a dict consumable by BacktestRunResponse.
    """
    from app.backtest.persistence import save_backtest_bundle_sync
    from app.services.backtest_service import (
        InvalidBacktestStrategyError,
        BacktestPriceFetchError,
        BacktestExecutionError,
        execute_backtest_sync,
        serialize_worker_summary,
    )

    try:
        result = execute_backtest_sync(
            assets=assets,
            strategy=strategy,
            benchmark=benchmark,
            period=period,
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            risk_free_rate=risk_free_rate,
            params=params,
            seed=seed,
        )

        persisted = save_backtest_bundle_sync(result)
        return serialize_worker_summary(result, persisted=persisted)
    except (InvalidBacktestStrategyError, BacktestPriceFetchError, BacktestExecutionError) as exc:
        return {"status": "error", "detail": str(exc)}
    except Exception as exc:
        logger.error("Backtest task failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
