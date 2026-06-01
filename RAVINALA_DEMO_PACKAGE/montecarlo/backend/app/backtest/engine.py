"""
backtest/engine.py — Core backtesting engine.

Étape 9 — Backtesting traçable
────────────────────────────────
Event-driven backtester with:
  - Temporal integrity (no lookahead)
  - Trade-level persistence
  - Flat-bps cost model (commission + slippage)
  - Mandatory baselines
  - Explicit limitations matrix per run

Strategies:
  - buy_and_hold      — baseline: buy at start, hold
  - equal_weight      — baseline: 1/N rebalance monthly
  - momentum          — long top-N by past-K-days return
  - mean_reversion    — long bottom-N by past-K-days return
  - ml_signal         — use trained ML model for direction

Level classification:
  - "exploration"  — indicative, NOT for live deployment
  - "simulation"   — more rigorous, but documented limits remain
"""

from __future__ import annotations

import logging
import time
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.risk.conventions import CONVENTIONS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LIMITATIONS MATRIX
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_LIMITATIONS: dict[str, dict[str, str]] = {
    "survivorship_bias": {
        "status": "not_corrected",
        "severity": "high",
        "note": "Universe is current constituents only — delisted/bankrupt stocks excluded",
    },
    "universe_bias": {
        "status": "not_corrected",
        "severity": "medium",
        "note": "Fixed universe at run time — no index reconstitution modelled",
    },
    "corporate_actions": {
        "status": "partial",
        "severity": "medium",
        "note": "yfinance auto-adjusts for splits/dividends but may miss some events",
    },
    "fill_assumptions": {
        "status": "simplified",
        "severity": "medium",
        "note": "Trades fill at close price — no intraday, no partial fills",
    },
    "slippage": {
        "status": "simplified",
        "severity": "medium",
        "note": "Flat bps model — no volume-dependent or volatility-dependent slippage",
    },
    "market_impact": {
        "status": "absent",
        "severity": "high",
        "note": "No market impact modelling — assumes infinite liquidity",
    },
    "capacity": {
        "status": "absent",
        "severity": "high",
        "note": "No capacity constraint — strategy may not scale to large AUM",
    },
    "bid_ask_spread": {
        "status": "absent",
        "severity": "medium",
        "note": "No bid-ask spread modelling — flat slippage proxy only",
    },
    "sub_period_analysis": {
        "status": "partial",
        "severity": "low",
        "note": "Rolling metrics computed but not systematically compared across regimes",
    },
    "lookahead_bias": {
        "status": "mitigated",
        "severity": "low",
        "note": "Signals computed on close[t], trades execute at close[t+1]",
    },
}

DEPLOYMENT_POLICY = (
    "EXPLORATION ONLY — This backtest uses simplified assumptions. "
    "Results are indicative and must NOT be used for live trading decisions "
    "until survivorship bias, market impact, and capacity constraints are addressed."
)


# ═══════════════════════════════════════════════════════════════════════════
# COST MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CostModel:
    """Flat basis-points cost model."""
    commission_bps: float = 5.0   # ~$0.50 per $10,000
    slippage_bps: float = 5.0     # ~$0.50 per $10,000

    def total_cost(self, notional: float) -> float:
        """Total round-trip cost for a trade of given notional."""
        return notional * (self.commission_bps + self.slippage_bps) / 10_000

    def commission(self, notional: float) -> float:
        return notional * self.commission_bps / 10_000

    def slippage(self, notional: float) -> float:
        return notional * self.slippage_bps / 10_000


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST RESULT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    trade_date: str
    asset: str
    side: str            # "buy" | "sell"
    quantity: float
    price: float
    commission: float
    slippage: float
    portfolio_value: float
    cash_after: float
    reason: str = ""


@dataclass
class BacktestResult:
    run_id: _uuid.UUID
    run_name: str
    strategy: str
    level: str
    assets: list[str]
    benchmark: str
    start_date: str
    end_date: str
    params: dict[str, Any]
    seed: int | None
    initial_capital: float
    cost_model_desc: dict[str, float]
    metrics: dict[str, float]
    benchmark_metrics: dict[str, float]
    limitations: dict[str, dict[str, str]]
    deployment_policy: str
    trades: list[TradeRecord]
    equity_curve: list[dict[str, Any]]  # [{date, value}]
    status: str = "completed"
    error_message: str | None = None
    duration_seconds: float = 0.0
    n_trades: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# METRICS CALCULATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_metrics(
    equity: pd.Series,
    risk_free_rate: float | None = None,
) -> dict[str, float]:
    """
    Compute performance metrics from an equity curve.

    Convention source: app.risk.conventions.CONVENTIONS.
    Risk-free rate is annualised and defaults to the governed backend convention.
    """
    if len(equity) < 2:
        return {}

    rf = risk_free_rate if risk_free_rate is not None else CONVENTIONS.risk_free_rate
    returns = equity.pct_change().dropna()
    n_days = len(returns)

    total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1)
    ann_factor = CONVENTIONS.trading_days_per_year / max(n_days, 1)
    ann_return = float((1 + total_return) ** ann_factor - 1)
    ann_vol = float(returns.std() * CONVENTIONS.ann_factor_vol)

    # Sharpe
    daily_rf = (1 + rf) ** (1 / CONVENTIONS.trading_days_per_year) - 1
    excess_returns = returns - daily_rf
    sharpe = (
        float(excess_returns.mean() / excess_returns.std() * CONVENTIONS.ann_factor_vol)
        if excess_returns.std() > 0
        else 0.0
    )

    # Sortino (downside deviation)
    downside = returns[returns < daily_rf] - daily_rf
    downside_std = float(downside.std() * CONVENTIONS.ann_factor_vol) if len(downside) > 0 else 0.0
    sortino = (
        float(excess_returns.mean() * CONVENTIONS.ann_factor_vol / downside_std)
        if downside_std > 0
        else 0.0
    )

    # Max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_dd = float(drawdown.min())

    # Calmar
    calmar = float(ann_return / abs(max_dd)) if max_dd != 0 else 0.0

    # Win rate (daily)
    win_rate = float((returns > 0).mean())

    return {
        "total_return": round(total_return, 6),
        "annualised_return": round(ann_return, 6),
        "annualised_volatility": round(ann_vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "max_drawdown": round(max_dd, 6),
        "calmar_ratio": round(calmar, 4),
        "win_rate_daily": round(win_rate, 4),
        "n_trading_days": n_days,
        "risk_free_rate": rf,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STRATEGY IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

def _run_buy_and_hold(
    prices: pd.DataFrame, assets: list[str], capital: float, costs: CostModel,
) -> tuple[pd.Series, list[TradeRecord]]:
    """Buy & hold baseline: buy equal weight at start, hold to end."""
    closes = prices["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()

    available = [a for a in assets if a in closes.columns]
    if not available:
        raise ValueError("No matching assets in price data")

    trades: list[TradeRecord] = []
    n_assets = len(available)
    alloc_per_asset = capital / n_assets

    # Track positions
    positions: dict[str, float] = {}
    cash = capital

    first_date = closes.index[0]
    for asset in available:
        price = float(closes[asset].iloc[0])
        if price <= 0 or np.isnan(price):
            continue
        qty = alloc_per_asset / price
        cost = costs.total_cost(alloc_per_asset)
        cash -= alloc_per_asset + cost
        positions[asset] = qty
        trades.append(TradeRecord(
            trade_date=str(first_date), asset=asset, side="buy",
            quantity=qty, price=price,
            commission=costs.commission(alloc_per_asset),
            slippage=costs.slippage(alloc_per_asset),
            portfolio_value=capital, cash_after=cash,
            reason="initial_buy_and_hold",
        ))

    # Build equity curve
    equity_values = []
    for dt in closes.index:
        pv = cash
        for asset, qty in positions.items():
            p = float(closes[asset].loc[dt])
            if not np.isnan(p):
                pv += qty * p
        equity_values.append(pv)

    equity = pd.Series(equity_values, index=closes.index, name="equity")
    return equity, trades


def _run_equal_weight(
    prices: pd.DataFrame, assets: list[str], capital: float, costs: CostModel,
    rebalance_freq: int = 21,
) -> tuple[pd.Series, list[TradeRecord]]:
    """Equal-weight (1/N) baseline with periodic rebalancing."""
    closes = prices["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()

    available = [a for a in assets if a in closes.columns]
    if not available:
        raise ValueError("No matching assets in price data")

    trades: list[TradeRecord] = []
    n_assets = len(available)
    positions: dict[str, float] = {}
    cash = capital

    equity_values = []
    last_rebalance = -rebalance_freq  # force rebalance on day 0

    for i, dt in enumerate(closes.index):
        # Rebalance check
        if i - last_rebalance >= rebalance_freq:
            # Calculate current portfolio value
            pv = cash
            for asset, qty in positions.items():
                p = float(closes[asset].loc[dt])
                if not np.isnan(p):
                    pv += qty * p

            # Sell everything
            for asset, qty in list(positions.items()):
                if qty > 0:
                    p = float(closes[asset].loc[dt])
                    if np.isnan(p):
                        continue
                    notional = qty * p
                    cost = costs.total_cost(notional)
                    cash += notional - cost
                    trades.append(TradeRecord(
                        trade_date=str(dt), asset=asset, side="sell",
                        quantity=qty, price=p,
                        commission=costs.commission(notional),
                        slippage=costs.slippage(notional),
                        portfolio_value=pv, cash_after=cash,
                        reason="rebalance_sell",
                    ))
            positions.clear()

            # Buy equal weight
            target_per_asset = cash / n_assets
            for asset in available:
                p = float(closes[asset].loc[dt])
                if p <= 0 or np.isnan(p):
                    continue
                qty = target_per_asset / p
                cost = costs.total_cost(target_per_asset)
                cash -= target_per_asset + cost
                positions[asset] = qty
                trades.append(TradeRecord(
                    trade_date=str(dt), asset=asset, side="buy",
                    quantity=qty, price=p,
                    commission=costs.commission(target_per_asset),
                    slippage=costs.slippage(target_per_asset),
                    portfolio_value=pv, cash_after=cash,
                    reason="rebalance_buy",
                ))

            last_rebalance = i

        # Compute portfolio value
        pv = cash
        for asset, qty in positions.items():
            p = float(closes[asset].loc[dt])
            if not np.isnan(p):
                pv += qty * p
        equity_values.append(pv)

    equity = pd.Series(equity_values, index=closes.index, name="equity")
    return equity, trades


def _run_momentum(
    prices: pd.DataFrame, assets: list[str], capital: float, costs: CostModel,
    lookback: int = 63, top_n: int = 3, rebalance_freq: int = 21,
) -> tuple[pd.Series, list[TradeRecord]]:
    """
    Long momentum: buy top_n assets by past-lookback-days return.
    Rebalance every rebalance_freq days.
    Signal computed on close[t], trades at close[t+1] (anti-lookahead).
    """
    closes = prices["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()

    available = [a for a in assets if a in closes.columns]
    if not available:
        raise ValueError("No matching assets in price data")

    trades: list[TradeRecord] = []
    positions: dict[str, float] = {}
    cash = capital
    equity_values = []
    last_rebalance = -rebalance_freq
    pending_signal: list[str] | None = None

    for i, dt in enumerate(closes.index):
        # Execute pending signal from previous day (anti-lookahead)
        if pending_signal is not None and i > 0:
            pv = cash
            for asset, qty in positions.items():
                p = float(closes[asset].loc[dt])
                if not np.isnan(p):
                    pv += qty * p

            # Sell everything
            for asset, qty in list(positions.items()):
                if qty > 0:
                    p = float(closes[asset].loc[dt])
                    if np.isnan(p):
                        continue
                    notional = qty * p
                    cost = costs.total_cost(notional)
                    cash += notional - cost
                    trades.append(TradeRecord(
                        trade_date=str(dt), asset=asset, side="sell",
                        quantity=qty, price=p,
                        commission=costs.commission(notional),
                        slippage=costs.slippage(notional),
                        portfolio_value=pv, cash_after=cash,
                        reason="momentum_rebalance_sell",
                    ))
            positions.clear()

            # Buy selected assets equal weight
            if pending_signal:
                target_per = cash / len(pending_signal)
                for asset in pending_signal:
                    p = float(closes[asset].loc[dt])
                    if p <= 0 or np.isnan(p):
                        continue
                    qty = target_per / p
                    cost = costs.total_cost(target_per)
                    cash -= target_per + cost
                    positions[asset] = qty
                    trades.append(TradeRecord(
                        trade_date=str(dt), asset=asset, side="buy",
                        quantity=qty, price=p,
                        commission=costs.commission(target_per),
                        slippage=costs.slippage(target_per),
                        portfolio_value=pv, cash_after=cash,
                        reason="momentum_rebalance_buy",
                    ))
            pending_signal = None

        # Generate signal for next day
        if i - last_rebalance >= rebalance_freq and i >= lookback:
            ret_lookback = {}
            for asset in available:
                series = closes[asset].iloc[max(0, i - lookback):i + 1]
                if len(series) >= lookback and series.iloc[0] > 0:
                    ret_lookback[asset] = float(series.iloc[-1] / series.iloc[0] - 1)

            if ret_lookback:
                ranked = sorted(ret_lookback.items(), key=lambda x: x[1], reverse=True)
                pending_signal = [a for a, _ in ranked[:top_n]]
                last_rebalance = i

        # Portfolio value
        pv = cash
        for asset, qty in positions.items():
            p = float(closes[asset].loc[dt])
            if not np.isnan(p):
                pv += qty * p
        equity_values.append(pv)

    equity = pd.Series(equity_values, index=closes.index, name="equity")
    return equity, trades


def _run_mean_reversion(
    prices: pd.DataFrame, assets: list[str], capital: float, costs: CostModel,
    lookback: int = 21, bottom_n: int = 3, rebalance_freq: int = 21,
) -> tuple[pd.Series, list[TradeRecord]]:
    """
    Mean reversion: buy bottom_n assets by past-lookback-days return.
    Same structure as momentum but reversed ranking.
    """
    closes = prices["Close"]
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()

    available = [a for a in assets if a in closes.columns]
    if not available:
        raise ValueError("No matching assets in price data")

    trades: list[TradeRecord] = []
    positions: dict[str, float] = {}
    cash = capital
    equity_values = []
    last_rebalance = -rebalance_freq
    pending_signal: list[str] | None = None

    for i, dt in enumerate(closes.index):
        if pending_signal is not None and i > 0:
            pv = cash
            for asset, qty in positions.items():
                p = float(closes[asset].loc[dt])
                if not np.isnan(p):
                    pv += qty * p
            for asset, qty in list(positions.items()):
                if qty > 0:
                    p = float(closes[asset].loc[dt])
                    if np.isnan(p):
                        continue
                    notional = qty * p
                    cost = costs.total_cost(notional)
                    cash += notional - cost
                    trades.append(TradeRecord(
                        trade_date=str(dt), asset=asset, side="sell",
                        quantity=qty, price=p,
                        commission=costs.commission(notional),
                        slippage=costs.slippage(notional),
                        portfolio_value=pv, cash_after=cash,
                        reason="meanrev_rebalance_sell",
                    ))
            positions.clear()
            if pending_signal:
                target_per = cash / len(pending_signal)
                for asset in pending_signal:
                    p = float(closes[asset].loc[dt])
                    if p <= 0 or np.isnan(p):
                        continue
                    qty = target_per / p
                    cost = costs.total_cost(target_per)
                    cash -= target_per + cost
                    positions[asset] = qty
                    trades.append(TradeRecord(
                        trade_date=str(dt), asset=asset, side="buy",
                        quantity=qty, price=p,
                        commission=costs.commission(target_per),
                        slippage=costs.slippage(target_per),
                        portfolio_value=pv, cash_after=cash,
                        reason="meanrev_rebalance_buy",
                    ))
            pending_signal = None

        if i - last_rebalance >= rebalance_freq and i >= lookback:
            ret_lookback = {}
            for asset in available:
                series = closes[asset].iloc[max(0, i - lookback):i + 1]
                if len(series) >= lookback and series.iloc[0] > 0:
                    ret_lookback[asset] = float(series.iloc[-1] / series.iloc[0] - 1)
            if ret_lookback:
                ranked = sorted(ret_lookback.items(), key=lambda x: x[1])  # ascending = worst performers
                pending_signal = [a for a, _ in ranked[:bottom_n]]
                last_rebalance = i

        pv = cash
        for asset, qty in positions.items():
            p = float(closes[asset].loc[dt])
            if not np.isnan(p):
                pv += qty * p
        equity_values.append(pv)

    equity = pd.Series(equity_values, index=closes.index, name="equity")
    return equity, trades


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

STRATEGY_MAP = {
    "buy_and_hold": _run_buy_and_hold,
    "equal_weight": _run_equal_weight,
    "momentum": _run_momentum,
    "mean_reversion": _run_mean_reversion,
}


def run_backtest(
    prices: pd.DataFrame,
    assets: list[str],
    strategy: str = "momentum",
    benchmark: str = "SPY",
    initial_capital: float = 100_000.0,
    commission_bps: float = 5.0,
    slippage_bps: float = 5.0,
    risk_free_rate: float | None = None,
    params: dict[str, Any] | None = None,
    seed: int | None = None,
) -> BacktestResult:
    """
    Run a single backtest.

    Parameters
    ----------
    prices : pd.DataFrame
        Multi-ticker OHLCV from yfinance (MultiIndex columns or single ticker).
    assets : list[str]
        Tickers to trade.
    strategy : str
        One of STRATEGY_MAP keys.
    benchmark : str
        Ticker for benchmark comparison.
    initial_capital : float
        Starting cash.
    commission_bps, slippage_bps : float
        Cost assumptions in basis points.
    params : dict
        Strategy-specific params.
    seed : int
        Random seed (for stochastic strategies).
    """
    start_time = time.time()
    run_id = _uuid.uuid4()
    run_name = f"bt_{strategy}_{run_id.hex[:8]}"

    if strategy not in STRATEGY_MAP:
        return BacktestResult(
            run_id=run_id, run_name=run_name, strategy=strategy,
            level="exploration", assets=assets, benchmark=benchmark,
            start_date="", end_date="", params=params or {}, seed=seed,
            initial_capital=initial_capital,
            cost_model_desc={"commission_bps": commission_bps, "slippage_bps": slippage_bps},
            metrics={}, benchmark_metrics={}, limitations=DEFAULT_LIMITATIONS,
            deployment_policy=DEPLOYMENT_POLICY, trades=[], equity_curve=[],
            status="failed", error_message=f"Unknown strategy: {strategy}",
        )

    if seed is not None:
        np.random.seed(seed)

    costs = CostModel(commission_bps=commission_bps, slippage_bps=slippage_bps)
    strat_params = dict(params or {})
    if risk_free_rate is not None:
        strat_params["risk_free_rate_override"] = risk_free_rate

    logger.info("Running backtest: %s (strategy=%s, assets=%s)", run_name, strategy, assets)

    try:
        strat_fn = STRATEGY_MAP[strategy]
        # Pass strategy-specific params
        if strategy == "momentum":
            equity, trades = strat_fn(
                prices, assets, initial_capital, costs,
                lookback=strat_params.get("lookback", 63),
                top_n=strat_params.get("top_n", 3),
                rebalance_freq=strat_params.get("rebalance_freq", 21),
            )
        elif strategy == "mean_reversion":
            equity, trades = strat_fn(
                prices, assets, initial_capital, costs,
                lookback=strat_params.get("lookback", 21),
                bottom_n=strat_params.get("bottom_n", 3),
                rebalance_freq=strat_params.get("rebalance_freq", 21),
            )
        elif strategy == "equal_weight":
            equity, trades = strat_fn(
                prices, assets, initial_capital, costs,
                rebalance_freq=strat_params.get("rebalance_freq", 21),
            )
        else:
            equity, trades = strat_fn(prices, assets, initial_capital, costs)

        metrics = compute_metrics(equity, risk_free_rate=risk_free_rate)

    except Exception as exc:
        duration = round(time.time() - start_time, 2)
        logger.error("Backtest failed: %s — %s", run_name, exc)
        return BacktestResult(
            run_id=run_id, run_name=run_name, strategy=strategy,
            level="exploration", assets=assets, benchmark=benchmark,
            start_date="", end_date="", params=strat_params, seed=seed,
            initial_capital=initial_capital,
            cost_model_desc={"commission_bps": commission_bps, "slippage_bps": slippage_bps},
            metrics={}, benchmark_metrics={}, limitations=DEFAULT_LIMITATIONS,
            deployment_policy=DEPLOYMENT_POLICY, trades=[], equity_curve=[],
            status="failed", error_message=str(exc), duration_seconds=duration,
        )

    # Benchmark: buy & hold on benchmark ticker
    benchmark_metrics = {}
    try:
        closes = prices["Close"]
        if isinstance(closes, pd.DataFrame) and benchmark in closes.columns:
            bm_equity, _ = _run_buy_and_hold(prices, [benchmark], initial_capital, costs)
            benchmark_metrics = compute_metrics(bm_equity, risk_free_rate=risk_free_rate)
    except Exception as exc:
        logger.warning("Benchmark computation failed: %s", exc)

    # Build equity curve for response
    eq_curve = [
        {"date": str(dt), "value": round(float(v), 2)}
        for dt, v in zip(equity.index, equity.values)
    ]

    duration = round(time.time() - start_time, 2)
    start_date = str(equity.index[0]) if len(equity) > 0 else ""
    end_date = str(equity.index[-1]) if len(equity) > 0 else ""

    result = BacktestResult(
        run_id=run_id,
        run_name=run_name,
        strategy=strategy,
        level="exploration",
        assets=assets,
        benchmark=benchmark,
        start_date=start_date,
        end_date=end_date,
        params=strat_params,
        seed=seed,
        initial_capital=initial_capital,
        cost_model_desc={"commission_bps": commission_bps, "slippage_bps": slippage_bps},
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
        limitations=DEFAULT_LIMITATIONS,
        deployment_policy=DEPLOYMENT_POLICY,
        trades=trades,
        equity_curve=eq_curve,
        status="completed",
        duration_seconds=duration,
        n_trades=len(trades),
    )

    logger.info(
        "Backtest done: %s | total_return=%.2f%% sharpe=%.2f max_dd=%.2f%% (%d trades, %.1fs)",
        run_name,
        metrics.get("total_return", 0) * 100,
        metrics.get("sharpe_ratio", 0),
        metrics.get("max_drawdown", 0) * 100,
        len(trades),
        duration,
    )

    return result


def run_with_baselines(
    prices: pd.DataFrame,
    assets: list[str],
    strategy: str = "momentum",
    benchmark: str = "SPY",
    initial_capital: float = 100_000.0,
    commission_bps: float = 5.0,
    slippage_bps: float = 5.0,
    risk_free_rate: float | None = None,
    params: dict[str, Any] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Run a strategy AND mandatory baselines (buy_and_hold + equal_weight).

    Returns dict with keys: primary, baseline_buy_hold, baseline_equal_weight, comparison.
    """
    primary = run_backtest(
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
    bh = run_backtest(
        prices, assets, "buy_and_hold", benchmark, initial_capital,
        commission_bps, slippage_bps, risk_free_rate=risk_free_rate, seed=seed,
    )
    ew = run_backtest(
        prices, assets, "equal_weight", benchmark, initial_capital,
        commission_bps,
        slippage_bps,
        risk_free_rate=risk_free_rate,
        params={"rebalance_freq": 21},
        seed=seed,
    )

    # Comparison
    pm = primary.metrics
    bh_m = bh.metrics
    ew_m = ew.metrics
    comparison = {}
    for metric in ["total_return", "sharpe_ratio", "max_drawdown"]:
        pv = pm.get(metric, 0)
        comparison[f"{metric}_vs_buy_hold"] = round(pv - bh_m.get(metric, 0), 6)
        comparison[f"{metric}_vs_equal_weight"] = round(pv - ew_m.get(metric, 0), 6)

    return {
        "primary": primary,
        "baseline_buy_hold": bh,
        "baseline_equal_weight": ew,
        "comparison": comparison,
    }
