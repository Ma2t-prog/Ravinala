"""
backtest/persistence.py — persistence helpers for backtest bundles.

Persists the primary backtest run and its mandatory baselines as a single
bundle so that list/get endpoints can survive process restarts when the async
database is active. Falls back cleanly when persistence is inactive.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select

from app.db.base import async_session
from app.db.models import BacktestRun, BacktestTrade


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
    return value


def _as_datetime(value: Any) -> datetime:
    """Normalize trade/backtest dates to timezone-aware datetimes."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "to_pydatetime"):
        dt = value.to_pydatetime()
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    raise TypeError(f"Unsupported datetime payload: {type(value)!r}")


def _row_to_payload(row: BacktestRun) -> dict[str, Any]:
    """Convert a persisted ORM row into a route-friendly payload."""
    return {
        "run_id": str(row.id),
        "bundle_id": str(row.bundle_id or row.id),
        "bundle_role": row.bundle_role,
        "run_name": row.run_name,
        "strategy": row.strategy,
        "level": row.level,
        "assets": row.assets or [],
        "benchmark": row.benchmark,
        "start_date": row.start_date.isoformat() if row.start_date else "",
        "end_date": row.end_date.isoformat() if row.end_date else "",
        "params": row.params or {},
        "seed": row.seed,
        "initial_capital": row.initial_capital,
        "cost_model": {
            "name": row.cost_model,
            "commission_bps": row.commission_bps,
            "slippage_bps": row.slippage_bps,
        },
        "metrics": row.metrics or {},
        "benchmark_metrics": row.benchmark_metrics or {},
        "comparison": row.comparison or {},
        "limitations": row.limitations or {},
        "deployment_policy": row.deployment_policy or "",
        "status": row.status,
        "error_message": row.error_message,
        "duration_seconds": row.duration_seconds or 0.0,
        "n_trades": row.n_trades or 0,
        "risk_free_rate_used": (row.metrics or {}).get("risk_free_rate"),
    }


def _build_row(
    run: Any,
    *,
    bundle_id: uuid.UUID,
    bundle_role: str,
    comparison: dict[str, Any] | None = None,
) -> BacktestRun:
    """Map an engine BacktestResult to a persisted BacktestRun row."""
    return BacktestRun(
        id=run.run_id,
        bundle_id=bundle_id,
        bundle_role=bundle_role,
        run_name=run.run_name,
        strategy=run.strategy,
        level=run.level,
        assets=_json_safe(run.assets),
        benchmark=run.benchmark,
        start_date=_as_datetime(run.start_date),
        end_date=_as_datetime(run.end_date),
        params=_json_safe(run.params),
        seed=run.seed,
        initial_capital=float(run.initial_capital),
        commission_bps=float(run.cost_model_desc.get("commission_bps", 0.0)),
        slippage_bps=float(run.cost_model_desc.get("slippage_bps", 0.0)),
        cost_model="flat_bps",
        metrics=_json_safe(run.metrics),
        benchmark_metrics=_json_safe(run.benchmark_metrics),
        comparison=_json_safe(comparison) if comparison else None,
        limitations=_json_safe(run.limitations),
        deployment_policy=getattr(run, "deployment_policy", ""),
        status=run.status,
        error_message=run.error_message,
        duration_seconds=float(run.duration_seconds or 0.0),
        n_trades=int(run.n_trades or 0),
    )


async def save_backtest_bundle(result: dict[str, Any]) -> dict[str, Any] | None:
    """
    Persist a full backtest bundle (primary + baselines + trades) when the DB is active.

    Returns a short serializable summary if written, otherwise ``None`` when
    persistence is inactive.
    """
    factory = async_session()
    if factory is None:
        return None

    primary = result["primary"]
    bundle_id = primary.run_id
    persisted = 0

    runs_to_persist = [
        ("primary", primary, result.get("comparison")),
        ("baseline_buy_hold", result["baseline_buy_hold"], None),
        ("baseline_equal_weight", result["baseline_equal_weight"], None),
    ]

    async with factory() as session:
        for bundle_role, run, comparison in runs_to_persist:
            row = _build_row(
                run,
                bundle_id=bundle_id,
                bundle_role=bundle_role,
                comparison=comparison,
            )
            session.add(row)

            for trade in getattr(run, "trades", []):
                session.add(
                    BacktestTrade(
                        run_id=run.run_id,
                        trade_date=_as_datetime(trade.trade_date),
                        asset=trade.asset,
                        side=trade.side,
                        quantity=float(trade.quantity),
                        price=float(trade.price),
                        commission=float(trade.commission),
                        slippage=float(trade.slippage),
                        portfolio_value=float(trade.portfolio_value),
                        cash_after=float(trade.cash_after),
                        reason=trade.reason,
                    )
                )
            persisted += 1

        await session.commit()

    return {
        "bundle_id": str(bundle_id),
        "primary_run_id": str(primary.run_id),
        "persisted_runs": persisted,
    }


async def list_backtest_runs_db(
    *,
    limit: int,
    strategy: str | None = None,
) -> list[dict[str, Any]] | None:
    """Load persisted primary backtest runs, or ``None`` if DB persistence is inactive."""
    factory = async_session()
    if factory is None:
        return None

    async with factory() as session:
        query = (
            select(BacktestRun)
            .where(BacktestRun.bundle_role == "primary")
            .order_by(desc(BacktestRun.created_at))
            .limit(limit)
        )
        if strategy:
            query = query.where(BacktestRun.strategy == strategy)
        result = await session.execute(query)
        rows = result.scalars().all()
        return [_row_to_payload(row) for row in rows]


async def get_backtest_bundle_db(run_id: str) -> dict[str, Any] | None:
    """Load a persisted backtest bundle by primary run id, or ``None`` if persistence is inactive."""
    factory = async_session()
    if factory is None:
        return None

    try:
        run_uuid = uuid.UUID(str(run_id))
    except Exception:
        return {}

    async with factory() as session:
        primary_stmt = select(BacktestRun).where(BacktestRun.id == run_uuid)
        primary_result = await session.execute(primary_stmt)
        primary = primary_result.scalar_one_or_none()
        if primary is None:
            return {}

        bundle_uuid = primary.bundle_id or primary.id
        bundle_stmt = select(BacktestRun).where(BacktestRun.bundle_id == bundle_uuid)
        bundle_result = await session.execute(bundle_stmt)
        rows = bundle_result.scalars().all()

        if not rows:
            rows = [primary]

        by_role = {row.bundle_role: _row_to_payload(row) for row in rows}
        return {
            "primary": by_role.get("primary"),
            "baseline_buy_hold": by_role.get("baseline_buy_hold"),
            "baseline_equal_weight": by_role.get("baseline_equal_weight"),
            "comparison": (by_role.get("primary") or {}).get("comparison", {}),
        }


def save_backtest_bundle_sync(result: dict[str, Any]) -> dict[str, Any] | None:
    """Synchronous wrapper for Celery workers."""
    return asyncio.run(save_backtest_bundle(result))
