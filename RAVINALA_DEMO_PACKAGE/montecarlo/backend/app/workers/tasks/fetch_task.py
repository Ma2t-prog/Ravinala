"""
Periodic data-refresh task — Étape 5: Job System.

This task replaces the inline cache warm-up in main.py's lifespan.
It is dispatched immediately at startup (via delay()) and re-runs
every 5 minutes via Celery Beat (see celery_app.beat_schedule).

The async snapshot service is run in a dedicated event loop so it
is safe to call from a synchronous Celery worker process.
"""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.fetch_task.refresh_snapshot",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # wait 60 s before retrying
    soft_time_limit=120,
    time_limit=180,
)
def refresh_snapshot(self) -> dict:
    """
    Fetch fresh market data from all providers and repopulate the cache.

    Returns a dict with ``status`` and ``keys_updated`` for the task result.
    Retries up to 3 times (60 s apart) on transient failures.
    """
    # Deferred imports keep the module importable even when the FastAPI
    # app context is not initialised (e.g. during celery inspect).
    from app.services.snapshot_service import get_full_snapshot_async

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(get_full_snapshot_async())
            logger.info("✅ Snapshot refreshed via Celery task")
            return {"status": "ok", "keys_updated": 1}
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    except Exception as exc:
        logger.error(f"❌ Snapshot refresh failed: {exc}")
        raise self.retry(exc=exc)
