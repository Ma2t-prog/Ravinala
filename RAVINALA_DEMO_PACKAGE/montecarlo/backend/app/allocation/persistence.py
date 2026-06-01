"""
allocation/persistence.py - persistence helpers for allocation recommendations.

Stores allocation runs when the async database is active and degrades cleanly
when persistence is not configured.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select

from app.db.base import async_session
from app.db.models import AllocationRun


def _json_safe(value: Any) -> Any:
    """Recursively normalize values to JSON-safe Python primitives."""
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
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        return _json_safe(value.model_dump(mode="json"))
    return value


def _row_to_summary(row: AllocationRun) -> dict[str, Any]:
    recommended_assets = row.recommended_assets or []
    return {
        "run_id": str(row.id),
        "recommendation_id": row.recommendation_id,
        "created_at": row.created_at,
        "amount": row.amount,
        "base_currency": row.base_currency,
        "objective_used": row.objective_used,
        "risk_profile": row.risk_profile,
        "recommended_asset_count": len(recommended_assets),
        "benchmark_preference": (row.investor_policy or {}).get("benchmark_preference", ""),
    }


def _row_to_detail(row: AllocationRun) -> dict[str, Any]:
    return {
        "recommendation_id": row.recommendation_id,
        "run_id": str(row.id),
        "persistence_status": "persisted",
        "policy": row.investor_policy or {},
        "eligibility": row.eligibility_snapshot or {},
        "assumptions": row.assumptions_snapshot or {},
        "risk_inputs": row.risk_inputs_snapshot or {},
        "eligible_tickers": row.eligible_tickers or [],
        "recommended_assets": row.recommended_assets or [],
        "rejected_assets": row.rejected_assets or [],
        "optimization": row.optimization_summary or {},
        "total_allocated_amount": row.total_allocated_amount,
        "cash_reserve_amount": row.cash_reserve_amount,
        "warnings": row.warnings or [],
        "created_at": row.created_at,
    }


async def save_allocation_run(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Persist a recommendation run when DB persistence is active.

    Returns a short serializable summary when persisted, otherwise ``None``.
    """
    factory = async_session()
    if factory is None:
        return None

    row = AllocationRun(
        recommendation_id=str(payload["recommendation_id"]),
        amount=float(payload["policy"]["amount"]),
        base_currency=str(payload["policy"]["base_currency"]),
        objective_used=str(payload["policy"]["objective_used"]),
        risk_profile=str(payload["policy"]["risk_profile"]),
        status="completed",
        investor_policy=_json_safe(payload["policy"]),
        eligibility_snapshot=_json_safe(payload["eligibility"]),
        assumptions_snapshot=_json_safe(payload["assumptions"]),
        risk_inputs_snapshot=_json_safe(payload["risk_inputs"]),
        request_payload=_json_safe(payload["request_payload"]),
        eligible_tickers=_json_safe(payload["eligible_tickers"]),
        recommended_assets=_json_safe(payload["recommended_assets"]),
        rejected_assets=_json_safe(payload["rejected_assets"]),
        optimization_summary=_json_safe(payload["optimization"]),
        warnings=_json_safe(payload["warnings"]),
        total_allocated_amount=float(payload["total_allocated_amount"]),
        cash_reserve_amount=float(payload["cash_reserve_amount"]),
    )

    async with factory() as session:
        session.add(row)
        await session.commit()

    return {
        "run_id": str(row.id),
        "created_at": row.created_at.isoformat(),
    }


async def list_allocation_runs_db(*, limit: int) -> list[dict[str, Any]] | None:
    """Return persisted allocation run summaries, or ``None`` if DB is inactive."""
    factory = async_session()
    if factory is None:
        return None

    async with factory() as session:
        query = select(AllocationRun).order_by(desc(AllocationRun.created_at)).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()
        return [_row_to_summary(row) for row in rows]


async def get_allocation_run_db(run_id: str) -> dict[str, Any] | None:
    """Return a persisted allocation run detail, or ``None`` if DB is inactive."""
    factory = async_session()
    if factory is None:
        return None

    try:
        run_uuid = uuid.UUID(str(run_id))
    except Exception:
        return {}

    async with factory() as session:
        stmt = select(AllocationRun).where(AllocationRun.id == run_uuid)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return {}
        return _row_to_detail(row)


def save_allocation_run_sync(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Synchronous wrapper for sync services/routes."""
    return asyncio.run(save_allocation_run(payload))


__all__ = [
    "get_allocation_run_db",
    "list_allocation_runs_db",
    "save_allocation_run",
    "save_allocation_run_sync",
]
