"""
observability/alerts.py — Two-tier alert / incident classification.

Étape 11 — Observabilité
─────────────────────────
Tier 1 — CRITICAL: immediate action required
  - Data source unreachable (all prices stale > 2 hrs)
  - Risk engine governance downgrade
  - Portfolio constraint violation
  - ML prediction outside historical range (>5σ)

Tier 2 — WARNING: inform, don't block
  - Data freshness degradation (>30 min delay)
  - Cache miss rate spike (>20% from baseline)
  - Risk metric governance level changed
  - Backtest completed with anomalies

Alerts are stored in memory (last 500) and exposed via the monitoring API.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AlertTier(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertCategory(str, Enum):
    data_source = "data_source"
    risk_engine = "risk_engine"
    ml_model = "ml_model"
    portfolio = "portfolio"
    cache = "cache"
    system = "system"


class Alert:
    """Immutable alert record."""

    __slots__ = ("id", "tier", "category", "title", "detail",
                 "created_at", "resolved_at", "source")

    def __init__(self, tier: AlertTier, category: AlertCategory,
                 title: str, detail: str = "", source: str = ""):
        self.id = uuid.uuid4().hex[:12]
        self.tier = tier
        self.category = category
        self.title = title
        self.detail = detail
        self.source = source
        self.created_at = datetime.now(timezone.utc)
        self.resolved_at: datetime | None = None

    def resolve(self) -> None:
        self.resolved_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "category": self.category.value,
            "title": self.title,
            "detail": self.detail,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_active": self.resolved_at is None,
        }


class AlertManager:
    """
    In-memory alert store (FIFO capped at 500).

    Thread-safe.  In production, alerts would be forwarded to
    PagerDuty / Slack / email via webhooks.
    """

    MAX_ALERTS = 500

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alerts: list[Alert] = []

    def fire(self, tier: AlertTier, category: AlertCategory,
             title: str, detail: str = "", source: str = "") -> Alert:
        """Create and store a new alert."""
        alert = Alert(tier=tier, category=category, title=title,
                      detail=detail, source=source)
        with self._lock:
            self._alerts.append(alert)
            if len(self._alerts) > self.MAX_ALERTS:
                self._alerts = self._alerts[-self.MAX_ALERTS:]
        return alert

    def resolve(self, alert_id: str) -> bool:
        """Mark an alert as resolved. Returns True if found."""
        with self._lock:
            for a in self._alerts:
                if a.id == alert_id:
                    a.resolve()
                    return True
        return False

    def active(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return unresolved alerts (most recent first), optionally capped."""
        with self._lock:
            alerts = [a.to_dict() for a in reversed(self._alerts)
                      if a.resolved_at is None]
            return alerts[:limit] if limit is not None else alerts

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return most recent alerts (resolved or not)."""
        with self._lock:
            return [a.to_dict() for a in reversed(self._alerts)][:limit]

    def summary(self) -> dict[str, Any]:
        """Aggregate alert counts by tier and category."""
        with self._lock:
            active = [a for a in self._alerts if a.resolved_at is None]
            by_tier = {}
            by_category = {}
            for a in active:
                by_tier[a.tier.value] = by_tier.get(a.tier.value, 0) + 1
                by_category[a.category.value] = by_category.get(a.category.value, 0) + 1
            return {
                "total_active": len(active),
                "total_all_time": len(self._alerts),
                "by_tier": by_tier,
                "by_category": by_category,
            }


# ─── Singleton ────────────────────────────────────────────────────────────

_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    global _manager
    if _manager is None:
        _manager = AlertManager()
    return _manager
