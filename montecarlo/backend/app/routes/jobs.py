"""
routes/jobs.py — Job status polling endpoint.

Étape 5 complétion — clients poll GET /api/v1/jobs/{job_id}
after receiving a Celery task_id from backtest/ml/risk dispatches.
"""

from __future__ import annotations

import logging
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.envelope import ApiResponse
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str  # PENDING | STARTED | SUCCESS | FAILURE | RETRY | REVOKED
    result: Any | None = None
    error: str | None = None


@router.get("/{job_id}", response_model=ApiResponse[JobStatus])
async def get_job_status(job_id: str):
    """
    Poll the status of an asynchronous Celery task.

    Returns the current state and, if completed, the task result.
    """
    res = AsyncResult(job_id, app=celery_app)
    status = res.status  # PENDING, STARTED, SUCCESS, FAILURE, etc.

    result = None
    error = None
    if status == "SUCCESS":
        result = res.result
    elif status == "FAILURE":
        error = str(res.result) if res.result else "Unknown error"

    return ApiResponse(
        data=JobStatus(job_id=job_id, status=status, result=result, error=error),
        data_quality="live",
        cache_hit=False,
    )
