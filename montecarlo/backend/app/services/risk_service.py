"""
services/risk_service.py - shared governed risk computation service.

Centralises the provider -> returns -> governed report -> persistence flow so
HTTP routes and Celery workers share the same application logic.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from datetime import datetime, timezone
from typing import Any

from app.providers.yfinance_adapter import YFinanceProvider
from app.risk.engine import compute_full_risk_report
from app.risk.persistence import list_risk_snapshots, save_risk_snapshot, save_risk_snapshot_sync
from app.schemas.risk_api import RiskComputeResponse, RiskSnapshotRecord

_DATA_SOURCE = "yfinance"
_snapshots_store: list[dict[str, Any]] = []


class RiskPriceFetchError(Exception):
    """Raised when prices/returns required for risk cannot be fetched."""


class RiskComputationError(Exception):
    """Raised when the governed risk engine fails after data retrieval."""


def _fetch_returns_sync(ticker: str, period: str) -> Any:
    """Fetch daily returns via the canonical provider boundary."""
    import pandas as pd

    provider = YFinanceProvider()
    data = provider.fetch_prices(ticker, period=period)
    closes = data["Close"]
    if isinstance(closes, pd.DataFrame):
        closes = closes.iloc[:, 0]
    return closes.pct_change().dropna()


def _compute_risk_bundle_sync(
    *,
    asset: str,
    period: str,
    portfolio_value: float,
) -> tuple[dict[str, Any], int]:
    """Run the shared synchronous risk core: returns fetch + governed report."""
    try:
        returns = _fetch_returns_sync(asset, period)
    except Exception as exc:  # noqa: BLE001
        raise RiskPriceFetchError(f"Price data fetch failed: {exc}") from exc

    try:
        report = compute_full_risk_report(returns, portfolio_value, _DATA_SOURCE)
    except Exception as exc:  # noqa: BLE001
        raise RiskComputationError(f"Risk computation error: {exc}") from exc

    return report, int(len(returns))


def _fallback_snapshot(
    *,
    asset: str,
    report: dict[str, Any],
    n_observations: int,
) -> dict[str, Any]:
    return {
        "snapshot_id": "pending-local-fallback",
        "asset": asset,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "data_source": _DATA_SOURCE,
        "n_observations": n_observations,
        "metrics": report,
        "governance_summary": report.get("_governance_summary", {}),
        "conventions_used": report.get("_conventions", {}),
    }


async def persist_snapshot(
    *,
    asset: str,
    report: dict[str, Any],
    n_observations: int,
) -> dict[str, Any]:
    """Persist a governed risk snapshot, falling back to memory when DB is absent."""
    db_snapshot = await save_risk_snapshot(
        asset=asset,
        report=report,
        data_source=_DATA_SOURCE,
        n_observations=n_observations,
    )
    snapshot = db_snapshot or _fallback_snapshot(
        asset=asset,
        report=report,
        n_observations=n_observations,
    )
    _snapshots_store.append(snapshot)
    if len(_snapshots_store) > 100:
        _snapshots_store.pop(0)
    return snapshot


def persist_snapshot_sync(
    *,
    asset: str,
    report: dict[str, Any],
    n_observations: int,
) -> dict[str, Any]:
    """Synchronous snapshot persistence for Celery or other sync contexts."""
    snapshot = save_risk_snapshot_sync(
        asset=asset,
        report=report,
        data_source=_DATA_SOURCE,
        n_observations=n_observations,
    )
    return snapshot or _fallback_snapshot(
        asset=asset,
        report=report,
        n_observations=n_observations,
    )


async def compute_risk_report(
    *,
    asset: str,
    period: str,
    portfolio_value: float,
    executor: Executor | None = None,
) -> RiskComputeResponse:
    """Run the full governed risk flow and return the typed API payload."""
    loop = asyncio.get_running_loop()
    report, n_observations = await loop.run_in_executor(
        executor,
        lambda: _compute_risk_bundle_sync(
            asset=asset,
            period=period,
            portfolio_value=portfolio_value,
        ),
    )
    await persist_snapshot(asset=asset, report=report, n_observations=n_observations)
    return RiskComputeResponse(asset=asset, period=period, report=report)


def _build_task_payload(
    *,
    asset: str,
    period: str,
    report: dict[str, Any],
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "asset": asset,
        "period": period,
        "governance_summary": report.get("_governance_summary", {}),
        "snapshot_id": snapshot.get("snapshot_id") if snapshot else None,
    }


def compute_risk_task_payload_sync(
    *,
    asset: str,
    period: str,
    portfolio_value: float,
) -> dict[str, Any]:
    """Synchronous risk execution path for Celery workers."""
    report, n_observations = _compute_risk_bundle_sync(
        asset=asset,
        period=period,
        portfolio_value=portfolio_value,
    )
    snapshot = persist_snapshot_sync(
        asset=asset,
        report=report,
        n_observations=n_observations,
    )
    return _build_task_payload(asset=asset, period=period, report=report, snapshot=snapshot)


def list_fallback_snapshots(*, asset: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Return the in-memory fallback snapshots used when DB persistence is absent."""
    snapshots = _snapshots_store.copy()
    if asset:
        snapshots = [snapshot for snapshot in snapshots if snapshot.get("asset") == asset]
    snapshots = snapshots[-limit:]
    snapshots.reverse()
    return snapshots


async def list_risk_snapshots_with_fallback(
    *,
    asset: str | None = None,
    limit: int = 20,
) -> list[RiskSnapshotRecord]:
    """Return typed risk snapshots from DB first, then the in-memory fallback store."""
    db_snapshots = await list_risk_snapshots(limit=limit, asset=asset)
    snapshots = db_snapshots if db_snapshots is not None else list_fallback_snapshots(asset=asset, limit=limit)
    return [RiskSnapshotRecord.model_validate(snapshot) for snapshot in snapshots]
