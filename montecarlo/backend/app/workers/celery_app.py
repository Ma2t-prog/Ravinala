"""
Celery application factory — Étape 5: Job System.

Broker  : Redis (same instance as the app cache layer)
Backend : Redis
Beat    : refresh_snapshot every 5 minutes

Run worker:
    celery -A app.workers.celery_app worker --loglevel=info

Run beat (scheduler):
    celery -A app.workers.celery_app beat --loglevel=info

Both can be combined for development:
    celery -A app.workers.celery_app worker --beat --loglevel=info
"""

import os

from celery import Celery

# Support both REDIS_URL (shared with cache) and CELERY_BROKER_URL overrides
_REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "ravinala",
    broker=_REDIS_URL,
    backend=_REDIS_URL,
    include=[
        "app.workers.tasks.fetch_task",
        "app.workers.tasks.allocator_task",
        "app.workers.tasks.analysis_task",
        "app.workers.tasks.backtest_task",
        "app.workers.tasks.ml_task",
        "app.workers.tasks.portfolio_task",
        "app.workers.tasks.risk_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Don't crash on startup if broker is temporarily unreachable
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=0,  # stop retrying if Redis is absent
    # Task result expiry — 1 hour
    result_expires=3600,
    # Beat schedule: keep the snapshot cache fresh
    beat_schedule={
        "refresh-snapshot-5min": {
            "task": "app.workers.tasks.fetch_task.refresh_snapshot",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
