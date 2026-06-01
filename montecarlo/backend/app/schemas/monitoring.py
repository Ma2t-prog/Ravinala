"""Pydantic schemas for monitoring and observability endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

HealthLevel = Literal["healthy", "degraded", "critical", "unknown"]
ComponentStatus = Literal["ok", "degraded", "critical", "unknown"]
AlertTierValue = Literal["critical", "warning", "info"]
AlertCategoryValue = Literal[
    "data_source",
    "risk_engine",
    "ml_model",
    "portfolio",
    "cache",
    "system",
]


class MonitoringComponentHealth(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: ComponentStatus
    detail: str | None = None
    latency_ms: float | None = None
    backend: str | None = None
    workers: int | None = None
    worker_names: list[str] | None = None
    models_available: int | None = None
    artifact_root: str | None = None
    has_snapshot: bool | None = None
    last_update: str | None = None
    staleness_seconds: float | None = None


class DeepHealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: HealthLevel
    timestamp: str
    checks: dict[str, MonitoringComponentHealth]


class MetricEndpointStats(BaseModel):
    model_config = ConfigDict(extra="ignore")

    count: int
    errors: int
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


class MetricsSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uptime_seconds: float
    counters: dict[str, int]
    endpoints: dict[str, MetricEndpointStats]


class DataSourceHealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: str
    governance_level: Literal["green", "yellow", "red"]
    last_ok: str | None = None
    staleness_seconds: float | None = None
    last_error: str | None = None
    ok_count: int
    error_count: int
    last_latency_ms: float


class DataQualityCounts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    green: int
    yellow: int
    red: int


class DataQualitySnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall: Literal["green", "yellow", "red"]
    counts: DataQualityCounts
    sources: list[DataSourceHealthResponse]


class AlertRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tier: AlertTierValue
    category: AlertCategoryValue
    title: str
    detail: str
    source: str
    created_at: str
    resolved_at: str | None = None
    is_active: bool


class AlertSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_active: int
    total_all_time: int
    by_tier: dict[str, int]
    by_category: dict[str, int]


class AlertsSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alerts: list[AlertRecord]
    summary: AlertSummaryResponse


class MonitoringStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    overall_health: HealthLevel
    data_quality: Literal["green", "yellow", "red", "unknown"]
    active_alerts: int
    requests_total: int
    errors_total: int
    components: dict[str, ComponentStatus]
