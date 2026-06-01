"""
routes/analysis.py — Company fundamental analysis endpoint.

Étape 13 — Frontend/Backend Boundary
──────────────────────────────────────
Endpoints:
  POST /api/v1/analysis/company       — run company analysis (sync)
  POST /api/v1/analysis/company/async  — Celery-dispatched company analysis
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.core.executor import get_shared_executor
from app.schemas.analysis import (
    CompanyAnalysisAsyncResponse,
    CompanyAnalysisRequest,
    CompanyAnalysisResponse,
)
from app.schemas.envelope import ApiResponse
from app.services.company_analysis_service import run_company_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


def _run_analysis(req: CompanyAnalysisRequest) -> dict:
    """Delegate company analysis to the service layer."""
    return run_company_analysis(req)


@router.post("/company", response_model=ApiResponse[CompanyAnalysisResponse])
async def company_analysis(req: CompanyAnalysisRequest):
    """
    Run company fundamental analysis.

    Modules: fundamentals, ratios, dcf, monte_carlo, peers.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _run_analysis, req)
    except Exception as exc:
        logger.error(f"Company analysis failed for {req.ticker}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        data=CompanyAnalysisResponse(**result),
        data_quality="live",
    )


@router.post("/company/async", response_model=ApiResponse[CompanyAnalysisAsyncResponse])
async def company_analysis_async(req: CompanyAnalysisRequest) -> ApiResponse[CompanyAnalysisAsyncResponse]:
    """
    Dispatch company analysis to Celery worker.

    Returns a job_id — poll GET /api/v1/jobs/{job_id} for status.
    """
    try:
        from app.workers.celery_app import celery_app

        task = celery_app.send_task(
            "app.workers.tasks.analysis_task.analyze_company",
            kwargs=req.model_dump(),
        )
        return ApiResponse(
            data=CompanyAnalysisAsyncResponse(job_id=task.id, status="PENDING"),
            data_quality="live",
        )
    except Exception as exc:
        logger.error(f"Celery dispatch failed for company analysis: {exc}, falling back to sync")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(get_shared_executor(), _run_analysis, req)
        return ApiResponse(
            data=CompanyAnalysisAsyncResponse(
                status="COMPLETED_SYNC",
                result=CompanyAnalysisResponse(**result),
            ),
            data_quality="live",
        )
