from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import monitoring
from app.schemas.monitoring import (
    AlertsSnapshotResponse,
    DataQualitySnapshotResponse,
    DeepHealthResponse,
    MetricsSnapshotResponse,
    MonitoringStatusResponse,
)


class _FakeMetrics:
    def snapshot(self) -> dict[str, object]:
        return {
            "uptime_seconds": 12.5,
            "counters": {"http_requests_total": 42, "http_errors_total": 3},
            "endpoints": {
                "GET /api/v1/monitoring/status": {
                    "count": 10,
                    "errors": 1,
                    "p50_ms": 10.5,
                    "p95_ms": 21.0,
                    "p99_ms": 30.0,
                }
            },
        }


class _FakeDataQuality:
    def snapshot(self) -> dict[str, object]:
        return {
            "overall": "yellow",
            "counts": {"green": 1, "yellow": 2, "red": 0},
            "sources": [
                {
                    "source": "yfinance",
                    "governance_level": "green",
                    "last_ok": "2026-03-23T10:00:00Z",
                    "staleness_seconds": 12.0,
                    "last_error": None,
                    "ok_count": 5,
                    "error_count": 0,
                    "last_latency_ms": 41.2,
                }
            ],
        }


class _FakeAlerts:
    def active(self, limit: int | None = None) -> list[dict[str, object]]:
        alerts = [
            {
                "id": "abc123",
                "tier": "warning",
                "category": "cache",
                "title": "Cache miss spike",
                "detail": "Miss rate above threshold",
                "source": "monitoring",
                "created_at": "2026-03-23T10:00:00Z",
                "resolved_at": None,
                "is_active": True,
            }
        ]
        return alerts[:limit] if limit is not None else alerts

    def recent(self, limit: int = 50) -> list[dict[str, object]]:
        return self.active()[:limit]

    def summary(self) -> dict[str, object]:
        return {
            "total_active": 1,
            "total_all_time": 2,
            "by_tier": {"warning": 1},
            "by_category": {"cache": 1},
        }


@pytest.mark.asyncio
async def test_monitoring_health_deep_returns_typed_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_deep_health_check() -> dict[str, object]:
        return {
            "status": "degraded",
            "timestamp": "2026-03-23T10:00:00Z",
            "checks": {
                "database": {"status": "ok", "detail": "connected"},
                "cache": {"status": "degraded", "latency_ms": 4.2, "backend": "memory"},
            },
        }

    monkeypatch.setattr(monitoring, "deep_health_check", fake_deep_health_check)

    result = await monitoring.monitoring_health_deep()

    assert isinstance(result, DeepHealthResponse)
    assert result.status == "degraded"
    assert result.checks["database"].status == "ok"
    assert result.checks["cache"].backend == "memory"


@pytest.mark.asyncio
async def test_monitoring_metrics_json_returns_typed_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(monitoring, "get_metrics", lambda: _FakeMetrics())

    result = await monitoring.monitoring_metrics_json()

    assert isinstance(result, MetricsSnapshotResponse)
    assert result.uptime_seconds == 12.5
    assert result.counters["http_requests_total"] == 42
    assert result.endpoints["GET /api/v1/monitoring/status"].p95_ms == 21.0


@pytest.mark.asyncio
async def test_monitoring_data_quality_returns_typed_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(monitoring, "get_data_quality", lambda: _FakeDataQuality())

    result = await monitoring.monitoring_data_quality()

    assert isinstance(result, DataQualitySnapshotResponse)
    assert result.overall == "yellow"
    assert result.counts.red == 0
    assert result.sources[0].source == "yfinance"


@pytest.mark.asyncio
async def test_monitoring_alerts_returns_typed_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(monitoring, "get_alert_manager", lambda: _FakeAlerts())

    result = await monitoring.monitoring_alerts(limit=10, active_only=False)

    assert isinstance(result, AlertsSnapshotResponse)
    assert result.summary.total_active == 1
    assert result.alerts[0].is_active is True
    assert result.alerts[0].tier == "warning"


@pytest.mark.asyncio
async def test_monitoring_alerts_active_only_honors_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    class _LimitedAlerts(_FakeAlerts):
        def active(self, limit: int | None = None) -> list[dict[str, object]]:
            alerts = super().active(limit=None)
            alerts.append(
                {
                    "id": "def456",
                    "tier": "critical",
                    "category": "system",
                    "title": "DB down",
                    "detail": "connection refused",
                    "source": "monitoring",
                    "created_at": "2026-03-23T10:01:00Z",
                    "resolved_at": None,
                    "is_active": True,
                }
            )
            return alerts[:limit] if limit is not None else alerts

    monkeypatch.setattr(monitoring, "get_alert_manager", lambda: _LimitedAlerts())

    result = await monitoring.monitoring_alerts(limit=1, active_only=True)

    assert isinstance(result, AlertsSnapshotResponse)
    assert len(result.alerts) == 1


@pytest.mark.asyncio
async def test_monitoring_status_composes_health_and_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_deep_health_check() -> dict[str, object]:
        return {
            "status": "critical",
            "timestamp": "2026-03-23T10:00:00Z",
            "checks": {
                "database": {"status": "critical", "detail": "down"},
                "cache": {"status": "ok", "backend": "redis"},
            },
        }

    monkeypatch.setattr(monitoring, "deep_health_check", fake_deep_health_check)
    monkeypatch.setattr(monitoring, "get_data_quality", lambda: _FakeDataQuality())
    monkeypatch.setattr(monitoring, "get_alert_manager", lambda: _FakeAlerts())
    monkeypatch.setattr(monitoring, "get_metrics", lambda: _FakeMetrics())

    result = await monitoring.monitoring_status()

    assert isinstance(result, MonitoringStatusResponse)
    assert result.overall_health == "critical"
    assert result.data_quality == "yellow"
    assert result.components["database"] == "critical"
    assert result.requests_total == 42
