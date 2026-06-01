"""
routes/backtest.py — Backtesting API endpoints.

Étape 9 — Backtesting traçable
────────────────────────────────
Endpoints:
  POST /api/v1/backtest/run           — run strategy + mandatory baselines
  GET  /api/v1/backtest/runs          — list past runs
  GET  /api/v1/backtest/runs/{run_id} — single run detail
  GET  /api/v1/backtest/strategies    — list available strategies
  GET  /api/v1/backtest/limitations   — default limitations matrix
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.backtest.engine import DEPLOYMENT_POLICY, DEFAULT_LIMITATIONS, STRATEGY_MAP
from app.core.executor import get_shared_executor
from app.schemas.backtest_api import (
    BacktestAsyncResponse,
    BacktestLimitationsResponse,
    BacktestRunRequest,
    BacktestRunResponse,
    CostModelResponse,
    FullRunResponse,
    RunSummary,
    TradeOut,
)
from app.schemas.envelope import ApiResponse
from app.services.backtest_service import (
    BacktestExecutionError,
    BacktestPriceFetchError,
    BacktestRunNotFoundError,
    InvalidBacktestStrategyError,
    _runs_store,
    get_backtest_bundle,
    list_backtest_runs,
    persist_or_store_backtest_bundle,
    run_backtest_bundle,
    validate_strategy,
    build_backtest_response,
)

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


@router.post("/run", response_model=ApiResponse[BacktestRunResponse])
async def run_backtest(req: BacktestRunRequest):
    """
    Run a backtest with mandatory baselines (buy & hold, equal weight).

    The engine enforces anti-lookahead (signal[t] → trade[t+1]),
    explicit cost assumptions, and outputs a limitations matrix.
    All runs are labelled "exploration" until biases are corrected.
    """
    try:
        result = await run_backtest_bundle(
            assets=req.assets,
            strategy=req.strategy,
            benchmark=req.benchmark,
            period=req.period,
            initial_capital=req.initial_capital,
            commission_bps=req.commission_bps,
            slippage_bps=req.slippage_bps,
            risk_free_rate=req.risk_free_rate,
            params=req.params,
            seed=req.seed,
            executor=get_shared_executor(),
        )
    except InvalidBacktestStrategyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BacktestPriceFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except BacktestExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    await persist_or_store_backtest_bundle(result)
    return ApiResponse(status="ok", data=build_backtest_response(result), data_quality="live")


@router.post("/run/async", response_model=ApiResponse[BacktestAsyncResponse])
async def run_backtest_async(req: BacktestRunRequest):
    """
    Dispatch a backtest to Celery and return a job_id immediately.

    Poll GET /api/v1/jobs/{job_id} for status.
    """
    try:
        validate_strategy(req.strategy)
    except InvalidBacktestStrategyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        from app.workers.tasks.backtest_task import run_backtest as _task

        task = _task.delay(
            assets=req.assets,
            strategy=req.strategy,
            benchmark=req.benchmark,
            period=req.period,
            initial_capital=req.initial_capital,
            commission_bps=req.commission_bps,
            slippage_bps=req.slippage_bps,
            risk_free_rate=req.risk_free_rate,
            seed=req.seed,
            params=req.params,
        )
        return ApiResponse(
            status="ok",
            data=BacktestAsyncResponse(job_id=task.id, status="PENDING"),
            data_quality="live",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {exc}")


@router.get("/runs", response_model=ApiResponse[list[RunSummary]])
async def list_runs(
    strategy: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    """List past backtest runs (most recent first)."""
    return ApiResponse(
        status="ok",
        data=await list_backtest_runs(strategy=strategy, limit=limit),
        data_quality="live",
    )


@router.get("/runs/{run_id}", response_model=ApiResponse[BacktestRunResponse])
async def get_run(run_id: str):
    """Get full details for a specific backtest run."""
    try:
        response = await get_backtest_bundle(run_id)
    except BacktestRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ApiResponse(status="ok", data=response, data_quality="live")


@router.get("/strategies", response_model=ApiResponse[list[str]])
async def list_strategies():
    """List available backtesting strategies."""
    return ApiResponse(status="ok", data=list(STRATEGY_MAP.keys()), data_quality="demo_static")


@router.get("/limitations", response_model=ApiResponse[BacktestLimitationsResponse])
async def get_limitations():
    """
    Default limitations matrix — documents all known biases and simplifications.
    Every backtest run includes this matrix.
    """
    return ApiResponse(
        status="ok",
        data=BacktestLimitationsResponse(
            limitations=DEFAULT_LIMITATIONS,
            deployment_policy=DEPLOYMENT_POLICY,
        ),
        data_quality="demo_static",
    )
