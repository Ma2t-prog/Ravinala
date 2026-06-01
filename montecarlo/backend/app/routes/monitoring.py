"""
routes/monitoring.py — Observability & monitoring endpoints.

Étape 11 — Observabilité et Opérabilité
────────────────────────────────────────
Provides 6 endpoints for runtime introspection:

  GET /api/v1/monitoring/health/deep    — per-component deep health check
  GET /api/v1/monitoring/metrics        — Prometheus-style or JSON metrics
  GET /api/v1/monitoring/metrics/json   — JSON metrics snapshot
  GET /api/v1/monitoring/data-quality   — data freshness per source
  GET /api/v1/monitoring/alerts         — recent alerts
  GET /api/v1/monitoring/status         — system status overview
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.observability.alerts import get_alert_manager
from app.observability.data_quality import get_data_quality
from app.observability.health import deep_health_check
from app.observability.metrics import get_metrics
from app.schemas.monitoring import (
    AlertsSnapshotResponse,
    DataQualitySnapshotResponse,
    DeepHealthResponse,
    MetricsSnapshotResponse,
    MonitoringStatusResponse,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


# ─── Deep Health ──────────────────────────────────────────────────────────

@router.get("/health/deep", response_model=DeepHealthResponse)
async def monitoring_health_deep() -> DeepHealthResponse:
    """
    Per-component deep health check.

    Returns overall status (healthy / degraded / critical) plus individual
    component reports for: database, cache, celery, ml_models, data_freshness.
    """
    return DeepHealthResponse.model_validate(await deep_health_check())


# ─── Prometheus Metrics ───────────────────────────────────────────────────

@router.get("/metrics", response_model=None, response_class=PlainTextResponse)
async def monitoring_metrics_prometheus() -> str:
    """
    Prometheus exposition format metrics.

    Scrape-ready endpoint for Prometheus / Grafana.
    """
    return get_metrics().prometheus_text()


@router.get("/metrics/json", response_model=MetricsSnapshotResponse)
async def monitoring_metrics_json() -> MetricsSnapshotResponse:
    """JSON snapshot of all collected metrics."""
    return MetricsSnapshotResponse.model_validate(get_metrics().snapshot())


# ─── Data Quality ─────────────────────────────────────────────────────────

@router.get("/data-quality", response_model=DataQualitySnapshotResponse)
async def monitoring_data_quality() -> DataQualitySnapshotResponse:
    """
    Data freshness and quality summary per source.

    Governance levels:
      - green: data < 30 min old
      - yellow: data 30 min – 2 h old
      - red: data > 2 h old or never fetched
    """
    return DataQualitySnapshotResponse.model_validate(get_data_quality().snapshot())


# ─── Alerts ───────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=AlertsSnapshotResponse)
async def monitoring_alerts(
    limit: int = Query(default=50, ge=1, le=500),
    active_only: bool = Query(default=False),
) -> AlertsSnapshotResponse:
    """
    Recent alerts with optional filter for active-only.
    """
    mgr = get_alert_manager()
    alerts = mgr.active(limit=limit) if active_only else mgr.recent(limit=limit)
    return AlertsSnapshotResponse.model_validate({
        "alerts": alerts,
        "summary": mgr.summary(),
    })


# ─── System Status Overview ──────────────────────────────────────────────

@router.get("/status", response_model=MonitoringStatusResponse)
async def monitoring_status() -> MonitoringStatusResponse:
    """
    Aggregated system status — single-glance overview.

    Combines health, data quality, alert counts, and key metrics.
    """
    health = await deep_health_check()
    dq = get_data_quality().snapshot()
    alert_summary = get_alert_manager().summary()
    metrics_snap = get_metrics().snapshot()

    return MonitoringStatusResponse.model_validate({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_health": health.get("status", "unknown"),
        "data_quality": dq.get("overall", "unknown"),
        "active_alerts": alert_summary.get("total_active", 0),
        "requests_total": metrics_snap.get("counters", {}).get("http_requests_total", 0),
        "errors_total": metrics_snap.get("counters", {}).get("http_errors_total", 0),
        "components": {
            name: comp.get("status", "unknown")
            for name, comp in health.get("checks", {}).items()
        },
    })
