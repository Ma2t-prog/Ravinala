"""
services/backtest_service.py - shared backtest application service.

Owns the orchestration between provider fetch, engine execution, persistence,
memory fallback, and route/worker serialization so controllers stay thin.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Executor
from typing import Any

from app.backtest.engine import DEPLOYMENT_POLICY, STRATEGY_MAP, run_with_baselines
from app.providers.yfinance_adapter import YFinanceProvider
from app.schemas.backtest_api import (
    BacktestRunResponse,
    CostModelResponse,
    FullRunResponse,
    RunSummary,
)

logger = logging.getLogger(__name__)

_runs_store: dict[str, dict[str, Any]] = {}


class BacktestServiceError(Exception):
    """Base class for backtest-service failures."""


class InvalidBacktestStrategyError(BacktestServiceError):
    """Raised when a requested strategy is unknown to the backtest engine."""


class BacktestPriceFetchError(BacktestServiceError):
    """Raised when market data cannot be fetched for a backtest request."""


class BacktestExecutionError(BacktestServiceError):
    """Raised when engine execution fails after prices are available."""


class BacktestRunNotFoundError(BacktestServiceError):
    """Raised when a requested backtest bundle cannot be found."""


def validate_strategy(strategy: str) -> None:
    """Validate that a strategy exists in the governed strategy registry."""
    if strategy not in STRATEGY_MAP:
        raise InvalidBacktestStrategyError(
            f"Unknown strategy '{strategy}'. Available: {list(STRATEGY_MAP.keys())}"
        )


def _fetch_prices_sync(tickers: list[str], period: str) -> Any:
    """Fetch OHLCV data via provider (R3 compliant)."""
    provider = YFinanceProvider()
    return provider.fetch_prices_batch(tickers, period=period)


def _result_to_full(result: Any) -> FullRunResponse:
    return FullRunResponse(
        run_id=str(result.run_id),
        run_name=result.run_name,
        strategy=result.strategy,
        level=result.level,
        status=result.status,
        assets=result.assets,
        benchmark=result.benchmark,
        start_date=result.start_date,
        end_date=result.end_date,
        params=result.params,
        seed=result.seed,
        initial_capital=result.initial_capital,
        cost_model=CostModelResponse(
            name="flat_bps",
            commission_bps=result.cost_model_desc.get("commission_bps", 0.0),
            slippage_bps=result.cost_model_desc.get("slippage_bps", 0.0),
        ),
        metrics=result.metrics,
        benchmark_metrics=result.benchmark_metrics,
        risk_free_rate_used=result.metrics.get("risk_free_rate"),
        limitations=result.limitations,
        deployment_policy=result.deployment_policy,
        n_trades=result.n_trades,
        duration_seconds=result.duration_seconds,
        error_message=result.error_message,
    )


def _result_to_summary(result: Any) -> RunSummary:
    return RunSummary(
        run_id=str(result.run_id),
        run_name=result.run_name,
        strategy=result.strategy,
        level=result.level,
        status=result.status,
        assets=result.assets,
        start_date=result.start_date,
        end_date=result.end_date,
        total_return=result.metrics.get("total_return"),
        sharpe_ratio=result.metrics.get("sharpe_ratio"),
        max_drawdown=result.metrics.get("max_drawdown"),
        risk_free_rate_used=result.metrics.get("risk_free_rate"),
        n_trades=result.n_trades,
        deployment_policy=result.deployment_policy,
    )


def _payload_to_full(payload: dict[str, Any]) -> FullRunResponse:
    cost_model = payload.get("cost_model", {})
    return FullRunResponse(
        run_id=payload["run_id"],
        run_name=payload["run_name"],
        strategy=payload["strategy"],
        level=payload["level"],
        status=payload["status"],
        assets=payload["assets"],
        benchmark=payload["benchmark"],
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        params=payload.get("params", {}),
        seed=payload.get("seed"),
        initial_capital=payload["initial_capital"],
        cost_model=CostModelResponse(
            name=cost_model.get("name", "flat_bps"),
            commission_bps=cost_model.get("commission_bps", 0.0),
            slippage_bps=cost_model.get("slippage_bps", 0.0),
        ),
        metrics=payload.get("metrics", {}),
        benchmark_metrics=payload.get("benchmark_metrics", {}),
        risk_free_rate_used=payload.get("risk_free_rate_used"),
        limitations=payload.get("limitations", {}),
        deployment_policy=payload.get("deployment_policy", DEPLOYMENT_POLICY),
        n_trades=payload.get("n_trades", 0),
        duration_seconds=payload.get("duration_seconds", 0.0),
        error_message=payload.get("error_message"),
    )


def _payload_to_summary(payload: dict[str, Any]) -> RunSummary:
    metrics = payload.get("metrics", {})
    return RunSummary(
        run_id=payload["run_id"],
        run_name=payload["run_name"],
        strategy=payload["strategy"],
        level=payload["level"],
        status=payload["status"],
        assets=payload["assets"],
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        total_return=metrics.get("total_return"),
        sharpe_ratio=metrics.get("sharpe_ratio"),
        max_drawdown=metrics.get("max_drawdown"),
        risk_free_rate_used=payload.get("risk_free_rate_used"),
        n_trades=payload.get("n_trades", 0),
        deployment_policy=payload.get("deployment_policy", DEPLOYMENT_POLICY),
    )


def build_backtest_response(result: dict[str, Any]) -> BacktestRunResponse:
    """Translate an engine backtest bundle into the public API schema."""
    return BacktestRunResponse(
        primary=_result_to_full(result["primary"]),
        baseline_buy_hold=_result_to_full(result["baseline_buy_hold"]),
        baseline_equal_weight=_result_to_full(result["baseline_equal_weight"]),
        comparison=result["comparison"],
    )


def build_persisted_backtest_response(bundle: dict[str, Any]) -> BacktestRunResponse:
    """Translate a persisted bundle payload into the public API schema."""
    primary = bundle.get("primary")
    baseline_buy_hold = bundle.get("baseline_buy_hold")
    baseline_equal_weight = bundle.get("baseline_equal_weight")
    if not primary or not baseline_buy_hold or not baseline_equal_weight:
        raise BacktestRunNotFoundError("Run bundle is incomplete")
    return BacktestRunResponse(
        primary=_payload_to_full(primary),
        baseline_buy_hold=_payload_to_full(baseline_buy_hold),
        baseline_equal_weight=_payload_to_full(baseline_equal_weight),
        comparison=bundle.get("comparison", {}),
    )


def execute_backtest_sync(
    *,
    assets: list[str],
    strategy: str,
    benchmark: str,
    period: str,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    risk_free_rate: float | None = None,
    seed: int | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the full provider->engine path synchronously."""
    validate_strategy(strategy)

    try:
        all_tickers = list(set(assets + [benchmark]))
        prices = _fetch_prices_sync(all_tickers, period)
    except Exception as exc:  # noqa: BLE001
        raise BacktestPriceFetchError(f"Price data fetch failed: {exc}") from exc

    try:
        return run_with_baselines(
            prices=prices,
            assets=assets,
            strategy=strategy,
            benchmark=benchmark,
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            risk_free_rate=risk_free_rate,
            params=params,
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001
        raise BacktestExecutionError(f"Backtest engine error: {exc}") from exc


async def run_backtest_bundle(
    *,
    assets: list[str],
    strategy: str,
    benchmark: str,
    period: str,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    risk_free_rate: float | None = None,
    seed: int | None = None,
    params: dict[str, Any] | None = None,
    executor: Executor | None = None,
) -> dict[str, Any]:
    """Async wrapper around the full backtest execution bundle."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        executor,
        lambda: execute_backtest_sync(
            assets=assets,
            strategy=strategy,
            benchmark=benchmark,
            period=period,
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            risk_free_rate=risk_free_rate,
            seed=seed,
            params=params,
        ),
    )


async def persist_or_store_backtest_bundle(result: dict[str, Any]) -> None:
    """Persist the bundle when DB is active, otherwise use the shared memory store."""
    primary = result["primary"]
    try:
        from app.backtest.persistence import save_backtest_bundle

        persisted = await save_backtest_bundle(result)
        if persisted is not None:
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backtest DB persistence failed, using memory fallback: %s", exc)

    _runs_store[str(primary.run_id)] = {
        "primary": primary,
        "baseline_buy_hold": result["baseline_buy_hold"],
        "baseline_equal_weight": result["baseline_equal_weight"],
        "comparison": result["comparison"],
    }


async def list_backtest_runs(
    *,
    strategy: str | None,
    limit: int,
) -> list[RunSummary]:
    """List backtest runs from DB first, then memory fallback."""
    try:
        from app.backtest.persistence import list_backtest_runs_db

        persisted_runs = await list_backtest_runs_db(limit=limit, strategy=strategy)
        if persisted_runs is not None:
            return [_payload_to_summary(run) for run in persisted_runs]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backtest DB listing failed, using memory fallback: %s", exc)

    runs: list[RunSummary] = []
    for run_data in _runs_store.values():
        primary = run_data["primary"]
        if strategy and primary.strategy != strategy:
            continue
        runs.append(_result_to_summary(primary))
    runs = runs[-limit:]
    runs.reverse()
    return runs


async def get_backtest_bundle(run_id: str) -> BacktestRunResponse:
    """Return one full backtest bundle from DB first, then memory fallback."""
    try:
        from app.backtest.persistence import get_backtest_bundle_db

        persisted_bundle = await get_backtest_bundle_db(run_id)
        if persisted_bundle:
            return build_persisted_backtest_response(persisted_bundle)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backtest DB retrieval failed, using memory fallback: %s", exc)

    if run_id not in _runs_store:
        raise BacktestRunNotFoundError(f"Run {run_id} not found")

    return build_backtest_response(_runs_store[run_id])


def serialize_worker_summary(
    result: dict[str, Any],
    *,
    persisted: dict[str, Any] | None,
) -> dict[str, Any]:
    """Serialize a worker result for Celery JSON backends."""

    def _ser(run: Any) -> dict[str, Any]:
        return {
            "run_id": str(run.run_id),
            "run_name": run.run_name,
            "strategy": run.strategy,
            "level": run.level,
            "status": run.status,
            "risk_free_rate_used": run.metrics.get("risk_free_rate"),
        }

    return {
        "status": "ok",
        "primary": _ser(result["primary"]),
        "baseline_buy_hold": _ser(result["baseline_buy_hold"]),
        "baseline_equal_weight": _ser(result["baseline_equal_weight"]),
        "bundle_id": persisted.get("bundle_id") if persisted else None,
    }


__all__ = [
    "BacktestExecutionError",
    "BacktestPriceFetchError",
    "BacktestRunNotFoundError",
    "InvalidBacktestStrategyError",
    "_runs_store",
    "build_backtest_response",
    "build_persisted_backtest_response",
    "execute_backtest_sync",
    "get_backtest_bundle",
    "list_backtest_runs",
    "persist_or_store_backtest_bundle",
    "run_backtest_bundle",
    "serialize_worker_summary",
    "validate_strategy",
]
