"""
workers/tasks/allocator_task.py - Async portfolio allocation recommendation via Celery.

Closes the async delivery path for the allocator slice so recommendation runs
can be dispatched off the HTTP cycle and polled via the shared jobs API.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.tasks.allocator_task.recommend_allocation",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
)
def recommend_allocation(self, **payload: Any) -> dict[str, Any]:
    """
    Execute an allocation recommendation in a Celery worker.

    Returns a serializable payload consumable via GET /api/v1/jobs/{job_id}.
    """
    from app.services.allocation_recommendation_service import build_allocation_recommendation

    try:
        result = build_allocation_recommendation(payload)
        return {
            "status": "ok",
            "recommendation": result.model_dump(mode="json"),
        }
    except ValueError as exc:
        return {"status": "error", "detail": str(exc)}
    except Exception as exc:
        logger.error("Allocator task failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
