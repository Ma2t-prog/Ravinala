"""
observability/health.py — Deep health check with per-component status.

Étape 11 — Observabilité
─────────────────────────
Returns a structured health report with:
  - Overall status: healthy | degraded | critical
  - Per-component checks: database, cache, celery, data freshness, ML models
  - Latency measurements
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

ComponentStatus = Literal["ok", "degraded", "critical", "unknown"]


async def _check_database() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        from app.db.base import database_health_snapshot
        health = await database_health_snapshot()
        status = health.get("status", "unknown")
        return {
            "status": "ok" if status == "connected" else "degraded" if status == "not_configured" else "critical",
            "detail": health.get("detail", status),
        }
    except Exception as exc:
        return {"status": "critical", "detail": str(exc)}


def _check_cache() -> dict[str, Any]:
    """Check Redis / in-memory cache."""
    try:
        from app.services.cache import get_cache
        cache = get_cache()
        t0 = time.time()
        ok = cache.health()
        latency_ms = round((time.time() - t0) * 1000, 1)
        return {
            "status": "ok" if ok else "degraded",
            "latency_ms": latency_ms,
            "backend": "redis" if getattr(cache, "redis", None) else "memory",
        }
    except Exception as exc:
        return {"status": "critical", "detail": str(exc)}


def _check_celery() -> dict[str, Any]:
    """Check Celery broker connectivity."""
    try:
        from app.workers.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=2.0)
        ping = inspector.ping()
        if ping:
            workers = list(ping.keys())
            return {"status": "ok", "workers": len(workers), "worker_names": workers}
        return {"status": "degraded", "detail": "No workers responded to ping"}
    except Exception as exc:
        return {"status": "degraded", "detail": f"Broker unreachable: {exc}"}


def _check_ml_models() -> dict[str, Any]:
    """Check ML model artifact availability."""
    try:
        artifact_root = Path("artifacts")
        if not artifact_root.exists():
            # Try alternate locations
            for alt in [Path("app/ml/artifacts"), Path("models")]:
                if alt.exists():
                    artifact_root = alt
                    break
        if artifact_root.exists():
            models = list(artifact_root.glob("*.joblib"))
            return {
                "status": "ok" if models else "degraded",
                "models_available": len(models),
                "artifact_root": str(artifact_root),
            }
        return {"status": "degraded", "detail": "No artifact directory found", "models_available": 0}
    except Exception as exc:
        return {"status": "unknown", "detail": str(exc)}


def _check_data_freshness() -> dict[str, Any]:
    """Check whether market data was recently refreshed."""
    try:
        from app.services.cache import get_cache
        cache = get_cache()
        snapshot = cache.get("snapshot:full")
        if snapshot and isinstance(snapshot, dict):
            last_updated = snapshot.get("last_updated") or snapshot.get("timestamp")
            cache_age = cache.get_age("snapshot:full")
            if last_updated:
                status = "ok"
                ttl_seconds = cache.get_ttl("snapshot")
                if cache_age is not None and cache_age > ttl_seconds:
                    status = "degraded"
                return {
                    "status": status,
                    "last_update": last_updated,
                    "has_snapshot": True,
                    "staleness_seconds": cache_age,
                }
            return {
                "status": "ok",
                "has_snapshot": True,
                "last_update": None,
                "staleness_seconds": cache_age,
            }
        return {"status": "degraded", "has_snapshot": False, "detail": "No cached snapshot"}
    except Exception as exc:
        return {"status": "unknown", "detail": str(exc)}


async def deep_health_check() -> dict[str, Any]:
    """
    Run all component health checks and compute overall status.

    Returns a structured report consumable by the monitoring dashboard.
    """
    checks = {
        "database": await _check_database(),
        "cache": _check_cache(),
        "celery": _check_celery(),
        "ml_models": _check_ml_models(),
        "data_freshness": _check_data_freshness(),
    }

    # Compute overall status
    statuses = [c.get("status", "unknown") for c in checks.values()]
    if any(s == "critical" for s in statuses):
        overall = "critical"
    elif any(s == "degraded" for s in statuses):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
