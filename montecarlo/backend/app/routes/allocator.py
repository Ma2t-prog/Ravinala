"""
routes/allocator.py - Portfolio construction recommendation endpoints.

First dedicated allocator slice:
- canonical investor policy normalization
- recommendation payload reusing the existing optimizer
- persisted run history when DB is active
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.executor import get_shared_executor
from app.schemas.allocator import (
    AllocationLiveMLRequest,
    AllocationRecommendationAsyncResponse,
    AllocationRecommendationRequest,
    AllocationRecommendationResponse,
    CapitalMarketAssumptionsResponse,
    EligibleUniverseResponse,
    AllocationRunDetail,
    AllocationRunSummary,
    PortfolioRiskInputsResponse,
)
from app.schemas.envelope import ApiResponse
from app.services.allocation_recommendation_service import (
    build_allocation_recommendation,
    build_live_ml_predictions,
    get_allocation_run_payload,
    list_allocation_runs,
)
from app.services.capital_market_assumptions_service import build_capital_market_assumptions
from app.services.investable_universe_service import build_eligible_universe
from app.services.investor_policy_service import build_investor_policy
from app.services.portfolio_risk_inputs_service import build_portfolio_risk_inputs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/allocator", tags=["allocator"])


def _recommend_sync(req: AllocationRecommendationRequest) -> AllocationRecommendationResponse:
    """Delegate allocation recommendation to the service layer."""
    return build_allocation_recommendation(req)


def _eligible_universe_sync(req: AllocationRecommendationRequest) -> EligibleUniverseResponse:
    """Preview the explicit eligible universe for a given investor mandate."""
    policy = build_investor_policy(req)
    return build_eligible_universe(req=req, policy=policy)


def _capital_market_assumptions_sync(
    req: AllocationRecommendationRequest,
) -> CapitalMarketAssumptionsResponse:
    """Preview the explicit expected-return assumptions for a given mandate."""
    policy = build_investor_policy(req)
    eligibility = build_eligible_universe(req=req, policy=policy)
    return build_capital_market_assumptions(eligibility=eligibility, policy=policy)


def _risk_inputs_sync(
    req: AllocationRecommendationRequest,
) -> PortfolioRiskInputsResponse:
    """Preview the canonical allocator risk payload for a given mandate."""
    policy = build_investor_policy(req)
    eligibility = build_eligible_universe(req=req, policy=policy)
    return build_portfolio_risk_inputs(eligibility=eligibility, policy=policy)


@router.post("/eligible-universe", response_model=ApiResponse[EligibleUniverseResponse])
async def preview_eligible_universe(
    req: AllocationRecommendationRequest,
) -> ApiResponse[EligibleUniverseResponse]:
    """Preview which candidate assets remain eligible before optimization."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _eligible_universe_sync, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Eligible universe preview failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(data=result, data_quality="live")


@router.post("/assumptions", response_model=ApiResponse[CapitalMarketAssumptionsResponse])
async def preview_capital_market_assumptions(
    req: AllocationRecommendationRequest,
) -> ApiResponse[CapitalMarketAssumptionsResponse]:
    """Preview the expected-return assumptions used by the allocator slice."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _capital_market_assumptions_sync, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Capital market assumptions preview failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(data=result, data_quality="live")


@router.post("/risk-inputs", response_model=ApiResponse[PortfolioRiskInputsResponse])
async def preview_portfolio_risk_inputs(
    req: AllocationRecommendationRequest,
) -> ApiResponse[PortfolioRiskInputsResponse]:
    """Preview the canonical allocator risk payload before optimization."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _risk_inputs_sync, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Portfolio risk inputs preview failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(data=result, data_quality="live")


@router.post("/recommend", response_model=ApiResponse[AllocationRecommendationResponse])
async def recommend_allocation(
    req: AllocationRecommendationRequest,
) -> ApiResponse[AllocationRecommendationResponse]:
    """Build an allocation recommendation from investor inputs and a candidate universe."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _recommend_sync, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Allocation recommendation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(data=result, data_quality="live")


@router.post("/recommend/with-live-ml", response_model=ApiResponse[AllocationRecommendationResponse])
async def recommend_allocation_with_live_ml(
    req: AllocationLiveMLRequest,
) -> ApiResponse[AllocationRecommendationResponse]:
    """Build an allocation recommendation with live ML predictions fetched server-side.

    If ``ml_run_ids`` is non-empty the endpoint calls ``run_prediction()`` concurrently
    for each ticker→run_id pair and injects the results into ``ml_predictions`` before
    CMA blending.  Explicit ``ml_predictions`` entries take priority over live-fetched
    ones for the same ticker.  Tickers whose prediction fails are skipped (warning added
    to response) so the allocation can still complete without full ML coverage.
    """
    live_predictions: list = []
    live_warnings: list[str] = []

    if req.ml_run_ids:
        live_predictions, live_warnings = await build_live_ml_predictions(
            req.ml_run_ids,
            horizon_days=req.ml_horizon_days,
            period=req.ml_price_period,
            executor=get_shared_executor(),
        )

    # Explicit ml_predictions override live-fetched ones for the same ticker.
    explicit_tickers = {p.ticker for p in req.ml_predictions}
    merged = list(req.ml_predictions) + [p for p in live_predictions if p.ticker not in explicit_tickers]
    enriched_req = req.model_copy(update={"ml_predictions": merged})

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_shared_executor(), _recommend_sync, enriched_req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Allocation recommendation with live ML failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if live_warnings:
        result.warnings.extend(live_warnings)

    return ApiResponse(data=result, data_quality="live")


@router.post("/recommend/async", response_model=ApiResponse[AllocationRecommendationAsyncResponse])
async def recommend_allocation_async(
    req: AllocationRecommendationRequest,
) -> ApiResponse[AllocationRecommendationAsyncResponse]:
    """Dispatch allocator recommendation to Celery and return a job id immediately."""
    try:
        from app.workers.tasks.allocator_task import recommend_allocation as _task

        task = _task.delay(**req.model_dump(mode="json"))
        return ApiResponse(
            data=AllocationRecommendationAsyncResponse(job_id=task.id, status="PENDING"),
            data_quality="live",
            cache_hit=False,
        )
    except Exception as exc:
        logger.error("Allocator async dispatch failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {exc}")


@router.get("/runs", response_model=ApiResponse[list[AllocationRunSummary]])
async def list_allocator_runs(
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[AllocationRunSummary]]:
    """List persisted allocator runs when database persistence is active."""
    runs = await list_allocation_runs(limit=limit)
    if runs is None:
        raise HTTPException(
            status_code=503,
            detail="allocation persistence inactive (set DATABASE_URL to enable run history)",
        )
    return ApiResponse(data=runs, data_quality="live", cache_hit=False)


@router.get("/runs/{run_id}", response_model=ApiResponse[AllocationRunDetail])
async def get_allocator_run(run_id: str) -> ApiResponse[AllocationRunDetail]:
    """Return a persisted allocator run detail by id."""
    payload = await get_allocation_run_payload(run_id)
    if payload is None:
        raise HTTPException(
            status_code=503,
            detail="allocation persistence inactive (set DATABASE_URL to enable run history)",
        )
    if not payload:
        raise HTTPException(status_code=404, detail=f"allocator run '{run_id}' not found")
    return ApiResponse(data=AllocationRunDetail(**payload), data_quality="live", cache_hit=False)
