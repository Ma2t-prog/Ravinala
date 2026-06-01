"""
MonitoringAgent — health checks and service monitoring.

Delegates to the shared observability services so agent missions report
real component health instead of simulated green checks.
"""

from __future__ import annotations

import logging
import time

from langgraph.config import get_stream_writer

from app.observability.alerts import get_alert_manager
from app.observability.health import deep_health_check

logger = logging.getLogger(__name__)

AGENT_NAME = "MonitoringAgent"


async def monitoring_agent_node(state: dict) -> dict:
    """Check real backend health and expose it through the agent runtime."""
    writer = get_stream_writer()
    started_at = time.time()

    writer(
        {
            "agent": AGENT_NAME,
            "event": "monitoring_start",
            "data": {"check_type": "deep_health"},
            "status": "running",
            "progress": 0.0,
            "timestamp": time.time(),
        }
    )

    try:
        health = await deep_health_check()
        checks = health.get("checks", {})
        services = list(checks.items())

        for index, (service, payload) in enumerate(services):
            writer(
                {
                    "agent": AGENT_NAME,
                    "event": "service_checked",
                    "data": {
                        "service": service,
                        "status": payload.get("status", "unknown"),
                        "detail": payload.get("detail"),
                        "latency_ms": payload.get("latency_ms"),
                    },
                    "status": "running",
                    "progress": (index + 1) / max(len(services), 1),
                    "timestamp": time.time(),
                }
            )

        alert_manager = get_alert_manager()
        alert_summary = alert_manager.summary()
        active_alerts = alert_manager.active(limit=10)
        overall = health.get("status", "unknown")
        duration_ms = int((time.time() - started_at) * 1000)

        monitoring_result = {
            "source": "observability.health",
            "status": overall,
            "checks": checks,
            "services": {
                service: payload.get("status", "unknown")
                for service, payload in checks.items()
            },
            "alerts": active_alerts,
            "alert_summary": alert_summary,
            "all_healthy": overall == "healthy",
            "timestamp": health.get("timestamp"),
        }

        writer(
            {
                "agent": AGENT_NAME,
                "event": "monitoring_complete",
                "data": {
                    "status": overall,
                    "active_alerts": alert_summary.get("total_active", 0),
                    "duration_ms": duration_ms,
                },
                "status": "completed",
                "progress": 1.0,
                "timestamp": time.time(),
            }
        )

        return {
            "monitoring_data": monitoring_result,
            "agents_completed": [AGENT_NAME],
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("MonitoringAgent error: %s", exc)
        writer(
            {
                "agent": AGENT_NAME,
                "event": "monitoring_error",
                "data": {"error": str(exc)},
                "status": "error",
                "progress": 0.0,
                "timestamp": time.time(),
            }
        )
        return {
            "monitoring_data": {
                "source": "observability.health",
                "status": "error",
                "error": str(exc),
            },
            "agents_failed": [AGENT_NAME],
            "errors": [{"agent": AGENT_NAME, "error": str(exc), "timestamp": time.time()}],
        }
