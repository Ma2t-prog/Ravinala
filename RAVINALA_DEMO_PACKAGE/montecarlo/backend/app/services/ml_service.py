"""
services/ml_service.py - shared ML application service.

Centralises ML route/worker orchestration so HTTP routes and Celery tasks
delegate to the same training, prediction, registry and persistence logic.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Executor
from typing import Any

from app.providers.yfinance_adapter import YFinanceProvider
from app.schemas.ml import ModelInfo, PredictionResult, RunDetail, RunSummary, TrainResponse

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """Base class for ML application-service errors."""


class InvalidModelTypeError(MLServiceError):
    """Raised when the requested ML model type is disabled or unknown."""


class PriceFetchError(MLServiceError):
    """Raised when required market data cannot be fetched."""


class ArtifactNotFoundError(MLServiceError):
    """Raised when a requested trained-model artifact cannot be resolved."""


class PredictionExecutionError(MLServiceError):
    """Raised when inference fails after prices and artifact are available."""


def _fetch_prices_sync(ticker: str, period: str = "5y") -> "pd.DataFrame":
    """Fetch OHLCV data via provider (R3 compliant)."""
    provider = YFinanceProvider()
    return provider.fetch_prices(ticker, period=period)


def _result_to_detail(result: dict[str, Any]) -> RunDetail:
    """Convert a training result payload into the canonical API schema."""
    return RunDetail(
        run_id=str(result["run_id"]),
        run_name=result["run_name"],
        model_type=result["model_type"],
        asset=result["asset"],
        horizon_days=result["horizon_days"],
        status=result["status"],
        params=result.get("params"),
        metrics_train=result.get("metrics_train"),
        metrics_val=result.get("metrics_val"),
        metrics_test=result.get("metrics_test"),
        artifact_path=result.get("artifact_path"),
        mlflow_run_id=result.get("mlflow_run_id"),
        dataset_hash=result.get("dataset_hash"),
        n_samples_train=result.get("n_samples_train"),
        n_samples_val=result.get("n_samples_val"),
        n_samples_test=result.get("n_samples_test"),
        validation_method=result.get("validation_method", "walk_forward"),
        n_splits=result.get("n_splits"),
        seed=result.get("seed"),
        feature_columns=result.get("feature_columns"),
        duration_seconds=result.get("duration_seconds"),
        error_message=result.get("error_message"),
        created_at=result.get("created_at"),
    )


def validate_model_type(model_type: str) -> None:
    """Validate a requested model type against the backend ML policy."""
    from app.ml.training import ALLOWED_MODELS, DISABLED_MODELS

    if model_type in DISABLED_MODELS:
        allowed = ", ".join(sorted(ALLOWED_MODELS - {"baseline_naive", "baseline_linear"}))
        raise InvalidModelTypeError(
            f"Model type '{model_type}' is disabled. "
            f"LSTM/GARCH require a proper pipeline. Allowed: {allowed}"
        )
    if model_type not in ALLOWED_MODELS:
        raise InvalidModelTypeError(f"Unknown model type: {model_type}")


def execute_training_sync(
    *,
    asset: str,
    model_type: str,
    horizon_days: int,
    period: str,
    seed: int,
    params: dict[str, Any] | None,
    include_baselines: bool,
) -> dict[str, Any]:
    """Fetch prices and execute the full training bundle synchronously."""
    from app.ml.training import train_model, train_with_baselines

    validate_model_type(model_type)

    try:
        prices = _fetch_prices_sync(asset, period)
    except Exception as exc:  # noqa: BLE001
        raise PriceFetchError(f"Failed to fetch prices for {asset}: {exc}") from exc

    if prices is None or prices.empty:
        raise PriceFetchError(f"Failed to fetch prices for {asset}: empty dataset")

    if include_baselines:
        return train_with_baselines(
            prices,
            asset,
            model_type,
            horizon_days,
            params,
            seed,
        )

    raw = train_model(
        prices,
        asset,
        model_type,
        horizon_days,
        params,
        5,
        seed,
    )
    return {
        "primary": raw,
        "baseline_naive": None,
        "baseline_linear": None,
        "comparison": None,
    }


async def run_training(
    *,
    asset: str,
    model_type: str,
    horizon_days: int,
    period: str,
    seed: int,
    params: dict[str, Any] | None,
    include_baselines: bool,
    executor: Executor | None = None,
) -> dict[str, Any]:
    """Async wrapper around the shared synchronous training execution."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        executor,
        lambda: execute_training_sync(
            asset=asset,
            model_type=model_type,
            horizon_days=horizon_days,
            period=period,
            seed=seed,
            params=params,
            include_baselines=include_baselines,
        ),
    )


async def persist_training_runs(result: dict[str, Any]) -> None:
    """Persist all training runs produced by a training bundle."""
    from app.ml.prediction import log_run_to_db

    await log_run_to_db(result["primary"])
    if result.get("baseline_naive"):
        await log_run_to_db(result["baseline_naive"])
    if result.get("baseline_linear"):
        await log_run_to_db(result["baseline_linear"])


def persist_training_runs_sync(result: dict[str, Any]) -> None:
    """Synchronous wrapper for Celery workers or thread-based execution paths."""
    asyncio.run(persist_training_runs(result))


def build_train_response(result: dict[str, Any]) -> TrainResponse:
    """Convert the raw training bundle into the public API schema."""
    return TrainResponse(
        primary=_result_to_detail(result["primary"]),
        baseline_naive=_result_to_detail(result["baseline_naive"]) if result.get("baseline_naive") else None,
        baseline_linear=_result_to_detail(result["baseline_linear"]) if result.get("baseline_linear") else None,
        comparison=result.get("comparison"),
    )


async def resolve_artifact_path(run_id: str) -> str | None:
    """Resolve an artifact path from DB first, then from local artifacts."""
    try:
        from app.db import base as _db

        if _db._session_factory is not None:
            from app.db.models import MLRun
            from sqlalchemy import select

            async with _db._session_factory() as session:
                stmt = select(MLRun.artifact_path).where(MLRun.id == run_id)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    return row
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to resolve ML artifact from DB for %s: %s", run_id, exc)

    from app.ml.training import ARTIFACT_ROOT

    if ARTIFACT_ROOT.exists():
        short_id = run_id.replace("-", "")[:8]
        for artifact in ARTIFACT_ROOT.glob("*.joblib"):
            if short_id in artifact.stem:
                return str(artifact)
    return None


async def run_prediction(
    *,
    asset: str,
    run_id: str,
    horizon_days: int,
    period: str,
    executor: Executor | None = None,
) -> PredictionResult:
    """Resolve the artifact, fetch prices, run inference and return the typed payload."""
    from app.ml.prediction import predict

    artifact_path = await resolve_artifact_path(run_id)
    if not artifact_path:
        raise ArtifactNotFoundError(f"No artifact found for run {run_id}")

    loop = asyncio.get_running_loop()
    try:
        prices = await loop.run_in_executor(executor, _fetch_prices_sync, asset, period)
    except Exception as exc:  # noqa: BLE001
        raise PriceFetchError(f"Failed to fetch prices: {exc}") from exc

    try:
        prediction = await loop.run_in_executor(
            executor,
            predict,
            prices,
            artifact_path,
            asset,
            horizon_days,
            run_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise PredictionExecutionError(f"Prediction failed: {exc}") from exc

    return PredictionResult(**{k: v for k, v in prediction.items() if k != "artifact_path"})


async def fetch_runs(
    *,
    asset: str | None = None,
    model_type: str | None = None,
    limit: int = 50,
) -> list[RunSummary]:
    """Fetch ML run summaries from the backend DB, degrading gracefully when absent."""
    try:
        from app.db import base as _db

        if _db._session_factory is None:
            return []

        from app.db.models import MLRun
        from sqlalchemy import select

        async with _db._session_factory() as session:
            stmt = select(MLRun).order_by(MLRun.created_at.desc()).limit(limit)
            if asset:
                stmt = stmt.where(MLRun.asset == asset)
            if model_type:
                stmt = stmt.where(MLRun.model_type == model_type)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                RunSummary(
                    run_id=str(row.id),
                    run_name=row.run_name,
                    model_type=row.model_type,
                    asset=row.asset,
                    horizon_days=row.horizon_days,
                    status=row.status,
                    stage=row.stage,
                    metrics_test=row.metrics_test,
                    duration_seconds=row.duration_seconds,
                    created_at=row.created_at.isoformat() if row.created_at else None,
                )
                for row in rows
            ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch runs from DB: %s", exc)
        return []


async def fetch_run_detail(run_id: str) -> RunDetail | None:
    """Fetch one ML run detail from the backend DB."""
    try:
        from app.db import base as _db

        if _db._session_factory is None:
            return None

        from app.db.models import MLRun
        from sqlalchemy import select

        async with _db._session_factory() as session:
            stmt = select(MLRun).where(MLRun.id == run_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return RunDetail(
                run_id=str(row.id),
                run_name=row.run_name,
                model_type=row.model_type,
                asset=row.asset,
                horizon_days=row.horizon_days,
                status=row.status,
                stage=row.stage,
                params=row.params,
                metrics_train=row.metrics_train,
                metrics_val=row.metrics_val,
                metrics_test=row.metrics_test,
                artifact_path=row.artifact_path,
                mlflow_run_id=row.mlflow_run_id,
                dataset_hash=row.dataset_hash,
                n_samples_train=row.n_samples_train,
                n_samples_val=row.n_samples_val,
                n_samples_test=row.n_samples_test,
                validation_method=row.validation_method,
                n_splits=row.n_splits,
                seed=row.seed,
                duration_seconds=row.duration_seconds,
                error_message=row.error_message,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch run detail: %s", exc)
        return None


def list_model_artifacts() -> list[ModelInfo]:
    """List locally available joblib model artifacts with lightweight metadata."""
    from app.ml.training import ARTIFACT_ROOT

    models: list[ModelInfo] = []
    if not ARTIFACT_ROOT.exists():
        return models

    for artifact in sorted(ARTIFACT_ROOT.glob("*.joblib")):
        parts = artifact.stem.split("_")
        models.append(
            ModelInfo(
                run_name=artifact.stem,
                model_type=parts[0] if parts else "unknown",
                asset=parts[1] if len(parts) > 1 else "unknown",
                artifact_path=str(artifact),
            )
        )
    return models


__all__ = [
    "ArtifactNotFoundError",
    "InvalidModelTypeError",
    "MLServiceError",
    "PredictionExecutionError",
    "PriceFetchError",
    "build_train_response",
    "execute_training_sync",
    "fetch_run_detail",
    "fetch_runs",
    "list_model_artifacts",
    "persist_training_runs",
    "persist_training_runs_sync",
    "resolve_artifact_path",
    "run_prediction",
    "run_training",
    "validate_model_type",
]
