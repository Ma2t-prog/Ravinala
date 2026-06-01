"""
observability/data_quality.py — Data freshness & quality tracking.

Étape 11 — Observabilité
─────────────────────────
Monitors data sources and flags staleness / quality issues.
Feeds into the alert system when thresholds are breached.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from .alerts import AlertCategory, AlertTier, get_alert_manager


class DataSourceHealth:
    """Per-source freshness and quality tracker."""

    __slots__ = ("name", "last_ok", "last_error", "ok_count",
                 "error_count", "last_latency_ms")

    def __init__(self, name: str) -> None:
        self.name = name
        self.last_ok: datetime | None = None
        self.last_error: str | None = None
        self.ok_count = 0
        self.error_count = 0
        self.last_latency_ms: float = 0.0

    def record_ok(self, latency_ms: float = 0.0) -> None:
        self.last_ok = datetime.now(timezone.utc)
        self.ok_count += 1
        self.last_latency_ms = latency_ms
        self.last_error = None

    def record_error(self, error: str) -> None:
        self.error_count += 1
        self.last_error = error

    @property
    def staleness_seconds(self) -> float | None:
        if self.last_ok is None:
            return None
        delta = datetime.now(timezone.utc) - self.last_ok
        return delta.total_seconds()

    @property
    def governance_level(self) -> str:
        """green / yellow / red classification."""
        stale = self.staleness_seconds
        if stale is None:
            return "red"
        if stale > 7200:  # 2 hours
            return "red"
        if stale > 1800:  # 30 min
            return "yellow"
        return "green"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.name,
            "governance_level": self.governance_level,
            "last_ok": self.last_ok.isoformat() if self.last_ok else None,
            "staleness_seconds": round(self.staleness_seconds, 1) if self.staleness_seconds is not None else None,
            "last_error": self.last_error,
            "ok_count": self.ok_count,
            "error_count": self.error_count,
            "last_latency_ms": round(self.last_latency_ms, 1),
        }


class DataQualityMonitor:
    """
    Central data-quality registry.

    Register sources at startup; record success/failure on each fetch.
    Governance levels:
      - green:  data < 30 min old
      - yellow: data 30 min – 2 h old
      - red:    data > 2 h old or never fetched
    """

    STALENESS_WARNING_S = 1800   # 30 min → yellow
    STALENESS_CRITICAL_S = 7200  # 2 h   → red

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[str, DataSourceHealth] = {}

    def _get(self, name: str) -> DataSourceHealth:
        if name not in self._sources:
            self._sources[name] = DataSourceHealth(name)
        return self._sources[name]

    def record_ok(self, source: str, latency_ms: float = 0.0) -> None:
        with self._lock:
            self._get(source).record_ok(latency_ms)

    def record_error(self, source: str, error: str) -> None:
        with self._lock:
            src = self._get(source)
            src.record_error(error)
        # Fire alert on repeated failures
        if src.error_count > 0 and src.error_count % 5 == 0:
            get_alert_manager().fire(
                tier=AlertTier.warning,
                category=AlertCategory.data_source,
                title=f"Repeated fetch failures: {source}",
                detail=f"Error count: {src.error_count}. Last: {error}",
                source="data_quality",
            )

    def check_staleness(self) -> None:
        """Scan all sources and fire alerts for stale data."""
        with self._lock:
            sources = list(self._sources.values())
        mgr = get_alert_manager()
        for src in sources:
            stale = src.staleness_seconds
            if stale is not None and stale > self.STALENESS_CRITICAL_S:
                mgr.fire(
                    tier=AlertTier.critical,
                    category=AlertCategory.data_source,
                    title=f"Data source critically stale: {src.name}",
                    detail=f"Last OK {stale / 3600:.1f}h ago",
                    source="data_quality",
                )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            sources = [s.to_dict() for s in self._sources.values()]
        n_green = sum(1 for s in sources if s["governance_level"] == "green")
        n_yellow = sum(1 for s in sources if s["governance_level"] == "yellow")
        n_red = sum(1 for s in sources if s["governance_level"] == "red")
        overall = "green"
        if n_red > 0:
            overall = "red"
        elif n_yellow > 0:
            overall = "yellow"
        return {
            "overall": overall,
            "counts": {"green": n_green, "yellow": n_yellow, "red": n_red},
            "sources": sources,
        }


# ─── Singleton ────────────────────────────────────────────────────────────

_monitor: DataQualityMonitor | None = None


def get_data_quality() -> DataQualityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = DataQualityMonitor()
    return _monitor
