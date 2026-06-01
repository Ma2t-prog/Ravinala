"""
routes/portfolio.py — Portfolio optimization endpoint.

Étape 13 — Frontend/Backend Boundary
──────────────────────────────────────
Endpoints:
  POST /api/v1/portfolio/optimize       — synchronous optimization (< 30s)
  POST /api/v1/portfolio/optimize/async  — Celery-dispatched optimization
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.core.executor import get_shared_executor
from app.schemas.envelope import ApiResponse
from app.schemas.portfolio import (
    OptimizeAsyncResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from app.services.portfolio_optimization_service import run_portfolio_optimization

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


def _optimize_sync(req: OptimizeRequest) -> dict:
    """Delegate optimization to the service layer."""
    return run_portfolio_optimization(req)


@router.post("/optimize", response_model=ApiResponse[OptimizeResponse])
async def portfolio_optimize(req: OptimizeRequest):
    """
    Run portfolio optimization synchronously.

    For portfolios ≤ 20 tickers this typically completes in < 15 s.
    For larger universes, use /optimize/async.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _optimize_sync, req)
    except Exception as exc:
        logger.error(f"Portfolio optimization failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        data=OptimizeResponse(**result),
        data_quality="live",
    )


@router.post("/optimize/async", response_model=ApiResponse[OptimizeAsyncResponse])
async def portfolio_optimize_async(req: OptimizeRequest):
    """
    Dispatch portfolio optimization to Celery worker.

    Returns a job_id — poll GET /api/v1/jobs/{job_id} for status.
    """
    try:
        from app.workers.celery_app import celery_app

        task = celery_app.send_task(
            "app.workers.tasks.portfolio_task.optimize_portfolio",
            kwargs=req.model_dump(),
        )
        return ApiResponse(
            data=OptimizeAsyncResponse(job_id=task.id, status="PENDING"),
            data_quality="live",
        )
    except Exception as exc:
        logger.error(f"Celery dispatch failed: {exc}, falling back to sync")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(get_shared_executor(), _optimize_sync, req)
        return ApiResponse(
            data=OptimizeAsyncResponse(
                status="COMPLETED_SYNC",
                result=OptimizeResponse(**result),
            ),
            data_quality="live",
        )
