"""
routes/ml.py — ML model training, prediction and registry API.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Endpoints:
  POST /api/v1/ml/train          — trigger model training (+ baselines)
  POST /api/v1/ml/predict        — run inference with a saved model
  GET  /api/v1/ml/runs           — list training runs
  GET  /api/v1/ml/runs/{run_id}  — single run detail
  GET  /api/v1/ml/models         — list available model artifacts
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.core.executor import get_shared_executor
from app.schemas.envelope import ApiResponse
from app.schemas.ml import (
    MLTrainAsyncResponse,
    ModelInfo,
    PredictRequest,
    PredictionResult,
    RunDetail,
    RunSummary,
    TrainRequest,
    TrainResponse,
)
from app.services.ml_service import (
    ArtifactNotFoundError,
    InvalidModelTypeError,
    PredictionExecutionError,
    PriceFetchError,
    build_train_response,
    fetch_run_detail,
    fetch_runs,
    list_model_artifacts,
    run_prediction,
    run_training,
    validate_model_type,
)

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


@router.post("/train", response_model=ApiResponse[TrainResponse])
async def train_model_endpoint(req: TrainRequest) -> ApiResponse[TrainResponse]:
    """
    Train a model on historical price data for the given asset.

    Mandatory baselines (naive + linear) are trained alongside by default.
    Training runs in a thread pool to avoid blocking the event loop.
    """
    try:
        result = await run_training(
            asset=req.asset,
            model_type=req.model_type,
            horizon_days=req.horizon_days,
            period=req.period,
            seed=req.seed,
            params=req.params,
            include_baselines=req.include_baselines,
            executor=get_shared_executor(),
        )
    except InvalidModelTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PriceFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ML training failed: {exc}")

    from app.services.ml_service import persist_training_runs

    asyncio.create_task(persist_training_runs(result))
    return ApiResponse(
        data=build_train_response(result),
        data_quality="live",
        cache_hit=False,
    )


@router.post("/train/async", response_model=ApiResponse[MLTrainAsyncResponse])
async def train_model_async(req: TrainRequest) -> ApiResponse[MLTrainAsyncResponse]:
    """
    Dispatch ML training to Celery and return a job_id immediately.

    Poll GET /api/v1/jobs/{job_id} for status.
    """
    try:
        validate_model_type(req.model_type)
    except InvalidModelTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        from app.workers.tasks.ml_task import train_model as _task

        task = _task.delay(
            asset=req.asset,
            model_type=req.model_type,
            horizon_days=req.horizon_days,
            period=req.period,
            seed=req.seed,
            params=req.params,
            include_baselines=req.include_baselines,
        )
        return ApiResponse(
            data=MLTrainAsyncResponse(job_id=task.id, status="PENDING"),
            data_quality="live",
            cache_hit=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {exc}")


@router.post("/predict", response_model=ApiResponse[PredictionResult])
async def predict_endpoint(req: PredictRequest) -> ApiResponse[PredictionResult]:
    """
    Run inference using a previously trained model.

    The prediction is logged to ml_predictions for audit trail.
    """
    try:
        prediction = await run_prediction(
            asset=req.asset,
            run_id=req.run_id,
            horizon_days=req.horizon_days,
            period=req.period,
            executor=get_shared_executor(),
        )
    except ArtifactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PriceFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except PredictionExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        data=prediction,
        data_quality="live",
        cache_hit=False,
    )


@router.get("/runs", response_model=ApiResponse[list[RunSummary]])
async def list_runs(
    asset: str | None = Query(None, description="Filter by asset"),
    model_type: str | None = Query(None, description="Filter by model type"),
    limit: int = Query(50, ge=1, le=500),
) -> ApiResponse[list[RunSummary]]:
    """List ML training runs from the database."""
    runs = await fetch_runs(asset=asset, model_type=model_type, limit=limit)
    return ApiResponse(data=runs, data_quality="live", cache_hit=False)


@router.get("/runs/{run_id}", response_model=ApiResponse[RunDetail])
async def get_run(run_id: str) -> ApiResponse[RunDetail]:
    """Get a single training run by ID."""
    detail = await fetch_run_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return ApiResponse(data=detail, data_quality="live", cache_hit=False)


@router.get("/models", response_model=ApiResponse[list[ModelInfo]])
async def list_models() -> ApiResponse[list[ModelInfo]]:
    """List available model artifacts on disk."""
    return ApiResponse(data=list_model_artifacts(), data_quality="live", cache_hit=False)
