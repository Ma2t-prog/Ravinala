from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import main
from app.observability import health


class _HealthCache:
    def __init__(self, payload: dict | None) -> None:
        self._payload = payload

    def get(self, key: str):
        assert key == "snapshot:full"
        return self._payload

    def get_age(self, key: str) -> int | None:
        assert key == "snapshot:full"
        return 42 if self._payload is not None else None

    def get_ttl(self, section: str) -> int:
        assert section == "snapshot"
        return 900

    def health(self) -> bool:
        return True


def test_check_data_freshness_reports_cached_snapshot_without_invalid_cache_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = _HealthCache({"timestamp": "2026-03-24T00:00:00+00:00"})
    monkeypatch.setattr("app.services.cache.get_cache", lambda: cache)

    result = health._check_data_freshness()

    assert result["status"] == "ok"
    assert result["has_snapshot"] is True
    assert result["last_update"] == "2026-03-24T00:00:00+00:00"
    assert result["staleness_seconds"] == 42


@pytest.mark.asyncio
async def test_system_health_endpoint_returns_timezone_aware_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "get_cache", lambda: _HealthCache(None))
    async def fake_database_health_snapshot() -> dict[str, str]:
        return {"status": "connected", "detail": "connected"}
    monkeypatch.setattr(main, "database_health_snapshot", fake_database_health_snapshot)

    result = await main.health_check()

    assert result.timestamp.tzinfo is not None
    assert result.timestamp.utcoffset() is not None


@pytest.mark.asyncio
async def test_system_health_endpoint_uses_live_database_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "get_cache", lambda: _HealthCache(None))

    async def fake_database_health_snapshot() -> dict[str, str]:
        return {"status": "unhealthy", "detail": "connection refused"}

    monkeypatch.setattr(main, "database_health_snapshot", fake_database_health_snapshot)

    result = await main.health_check()

    assert result.db_status == "unhealthy"


@pytest.mark.asyncio
async def test_deep_health_reports_database_probe_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_database_health_snapshot() -> dict[str, str]:
        return {"status": "unhealthy", "detail": "connection refused"}

    monkeypatch.setattr("app.db.base.database_health_snapshot", fake_database_health_snapshot)
    monkeypatch.setattr("app.services.cache.get_cache", lambda: _HealthCache(None))

    result = await health.deep_health_check()

    assert result["checks"]["database"]["status"] == "critical"
    assert result["checks"]["database"]["detail"] == "connection refused"
