"""Pydantic schemas for ML endpoints."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MLTrainRequest(BaseModel):
    ticker: str
    horizon_days: int = Field(default=5, ge=1, le=60)
    model_type: str = Field(default="xgboost", pattern=r"^(xgboost|lightgbm|random_forest)$")
    lookback_days: int = Field(default=504, ge=120, le=2520)


class MLTrainResponse(BaseModel):
    run_id: str
    model_type: str
    directional_accuracy: float
    r2_test: float
    baseline_accuracy: float = 0.50
    artifact_path: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    created_at: datetime


class MLTrainAsyncResponse(BaseModel):
    """Async training job dispatch payload."""

    job_id: str
    status: Literal["PENDING"] = "PENDING"


class TrainRequest(BaseModel):
    asset: str = Field(..., description="Ticker symbol (e.g. SPY, AAPL)", min_length=1, max_length=20)
    model_type: str = Field(
        default="random_forest",
        description="Model type: random_forest | xgboost | lightgbm",
    )
    horizon_days: int = Field(default=5, ge=1, le=63, description="Prediction horizon (trading days)")
    seed: int = Field(default=42, ge=0, description="Random seed")
    params: dict[str, Any] | None = Field(default=None, description="Hyperparams override")
    include_baselines: bool = Field(default=True, description="Train mandatory baselines alongside")
    period: str = Field(default="5y", description="yfinance period for price data")


class PredictRequest(BaseModel):
    asset: str = Field(..., description="Ticker symbol", min_length=1, max_length=20)
    run_id: str = Field(..., description="UUID of the training run to use")
    horizon_days: int = Field(default=5, ge=1, le=63)
    period: str = Field(default="1y", description="yfinance period for recent prices")


class RunSummary(BaseModel):
    run_id: str
    run_name: str
    model_type: str
    asset: str
    horizon_days: int
    status: str
    stage: str = "dev"
    metrics_test: dict[str, float] | None = None
    duration_seconds: float | None = None
    created_at: str | None = None


class RunDetail(RunSummary):
    params: dict[str, Any] | None = None
    metrics_train: dict[str, float] | None = None
    metrics_val: dict[str, float] | None = None
    artifact_path: str | None = None
    mlflow_run_id: str | None = None
    dataset_hash: str | None = None
    n_samples_train: int | None = None
    n_samples_val: int | None = None
    n_samples_test: int | None = None
    validation_method: str = "walk_forward"
    n_splits: int | None = None
    seed: int | None = None
    feature_columns: list[str] | None = None
    error_message: str | None = None


class PredictionResult(BaseModel):
    asset: str
    predicted_return: float
    predicted_direction: str
    confidence: float | None = None
    prediction_date: str
    target_date: str
    horizon_days: int
    run_id: str


class TrainResponse(BaseModel):
    primary: RunDetail
    baseline_naive: RunDetail | None = None
    baseline_linear: RunDetail | None = None
    comparison: dict[str, float | None] | None = None


class ModelInfo(BaseModel):
    run_name: str
    model_type: str
    asset: str
    artifact_path: str
    stage: str = "dev"
    test_directional_accuracy: float | None = None
