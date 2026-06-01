"""
risk/persistence.py — persistence helpers for governed risk snapshots.

Best-effort persistence:
- writes to the configured async database when available;
- falls back gracefully when persistence is inactive;
- normalises nested metrics to JSON-safe primitives for auditability.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select

from app.db.base import async_session
from app.db.models import RiskSnapshot


def _json_safe(value: Any) -> Any:
    """Recursively normalise values to JSON-safe Python primitives."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _snapshot_to_payload(snapshot: RiskSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": str(snapshot.snapshot_id),
        "asset": snapshot.asset,
        "computed_at": snapshot.computed_at.isoformat() if snapshot.computed_at else None,
        "data_source": snapshot.data_source,
        "n_observations": snapshot.n_observations,
        "metrics": snapshot.metrics or {},
        "conventions_used": snapshot.conventions_used or {},
        "governance_summary": snapshot.governance_summary or {},
    }


async def save_risk_snapshot(
    *,
    asset: str,
    report: dict[str, Any],
    data_source: str,
    n_observations: int,
) -> dict[str, Any] | None:
    """
    Persist a governed risk snapshot when the DB is active.

    Returns a serialisable payload if written, otherwise ``None`` when the DB is
    inactive or persistence fails.
    """
    factory = async_session()
    if factory is None:
        return None

    payload_metrics = _json_safe(report)
    conventions_used = _json_safe(report.get("_conventions", {}))
    governance_summary = _json_safe(report.get("_governance_summary", {}))

    async with factory() as session:
        snapshot = RiskSnapshot(
            asset=asset,
            data_source=data_source,
            n_observations=n_observations,
            metrics=payload_metrics,
            conventions_used=conventions_used,
            governance_summary=governance_summary,
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return _snapshot_to_payload(snapshot)


async def list_risk_snapshots(
    *,
    limit: int,
    asset: str | None = None,
) -> list[dict[str, Any]] | None:
    """Load recent risk snapshots from the DB, or return ``None`` if inactive."""
    factory = async_session()
    if factory is None:
        return None

    async with factory() as session:
        query = select(RiskSnapshot).order_by(desc(RiskSnapshot.computed_at)).limit(limit)
        if asset:
            query = query.where(RiskSnapshot.asset == asset)
        result = await session.execute(query)
        snapshots = result.scalars().all()
        return [_snapshot_to_payload(snapshot) for snapshot in snapshots]


def save_risk_snapshot_sync(
    *,
    asset: str,
    report: dict[str, Any],
    data_source: str,
    n_observations: int,
) -> dict[str, Any] | None:
    """Synchronous wrapper for Celery workers."""
    return asyncio.run(
        save_risk_snapshot(
            asset=asset,
            report=report,
            data_source=data_source,
            n_observations=n_observations,
        )
    )
