"""
backtesting.py — Multi-strategy backtester with proper metrics (Sharpe, max DD, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from genesix.utils.quant_conventions import (
    ANNUALIZATION_FACTOR_VOL,
    RISK_FREE_RATE,
    TRADING_DAYS,
    annualize_geometric_return,
    annualize_volatility,
    sharpe_ratio,
)

from .core import DARK_THEME
from .technical import TechnicalIndicators

_C = DARK_THEME


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: Optional[pd.Timestamp]
    direction: str   # 'long' | 'short'
    entry_price: float
    exit_price: Optional[float]
    shares: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    strategy_name: str
    trades: List[Trade]
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    metrics: Dict = field(default_factory=dict)
    signals: pd.DataFrame = field(default_factory=pd.DataFrame)


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def signal_sma_crossover(df: pd.DataFrame,
                          fast: int = 20, slow: int = 50) -> pd.Series:
    """SMA crossover: +1 when fast > slow, -1 when fast < slow."""
    fast_sma = TechnicalIndicators.sma(df["Close"], fast)
    slow_sma = TechnicalIndicators.sma(df["Close"], slow)
    signal = pd.Series(0, index=df.index)
    signal[fast_sma > slow_sma] = 1
    signal[fast_sma < slow_sma] = -1
    return signal


def signal_rsi_mean_reversion(df: pd.DataFrame,
                               period: int = 14,
                               oversold: float = 30,
                               overbought: float = 70) -> pd.Series:
    """RSI mean reversion: +1 when RSI < oversold, -1 when RSI > overbought, 0 otherwise."""
    rsi = TechnicalIndicators.rsi(df["Close"], period)
    signal = pd.Series(0, index=df.index)
    signal[rsi < oversold] = 1
    signal[rsi > overbought] = -1
    return signal


def signal_macd_crossover(df: pd.DataFrame,
                           fast: int = 12, slow: int = 26, sig: int = 9) -> pd.Series:
    """MACD crossover: +1 when MACD > signal, -1 otherwise."""
    macd = TechnicalIndicators.macd(df["Close"], fast, slow, sig)
    signal = pd.Series(0, index=df.index)
    signal[macd["macd"] > macd["macd_signal"]] = 1
    signal[macd["macd"] < macd["macd_signal"]] = -1
    return signal


def signal_bollinger_breakout(df: pd.DataFrame,
                               period: int = 20, std: float = 2.0) -> pd.Series:
    """Bollinger Band breakout: +1 when price crosses above upper, -1 when below lower."""
    bb = TechnicalIndicators.bollinger_bands(df["Close"], period, std)
    signal = pd.Series(0, index=df.index)
    signal[df["Close"] > bb["bb_upper"]] = 1
    signal[df["Close"] < bb["bb_lower"]] = -1
    return signal


def signal_supertrend(df: pd.DataFrame,
                       period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """SuperTrend: +1 when direction is up (-1 internally), -1 when down."""
    st_df = TechnicalIndicators.supertrend(df, period, multiplier)
    signal = pd.Series(0, index=df.index)
    signal[st_df["direction"] == -1] = 1  # bullish
    signal[st_df["direction"] == 1] = -1  # bearish
    return signal


PRESET_STRATEGIES: Dict[str, Callable] = {
    "SMA Crossover (20/50)":     lambda df: signal_sma_crossover(df, 20, 50),
    "SMA Crossover (50/200)":    lambda df: signal_sma_crossover(df, 50, 200),
    "RSI Mean Reversion":        signal_rsi_mean_reversion,
    "MACD Crossover":            signal_macd_crossover,
    "Bollinger Breakout":        signal_bollinger_breakout,
    "SuperTrend":                signal_supertrend,
}


# ─────────────────────────────────────────────────────────────────────────────
# BACKTESTER
# ─────────────────────────────────────────────────────────────────────────────

class Backtester:
    """Multi-strategy event-driven backtester with realistic execution."""

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005,
        allow_short: bool = True,
        position_sizing: str = "fixed_pct",  # 'fixed_pct' | 'full'
        position_pct: float = 1.0,
        # ── Risk limits ──────────────────────────────────────────────
        max_drawdown_pct: float = 0.0,       # 0 = disabled
        stop_loss_pct: float = 0.0,           # 0 = disabled
        take_profit_pct: float = 0.0,         # 0 = disabled
        max_position_value: float = 0.0,      # 0 = unlimited
        max_leverage: float = 1.0,
        # ── Volume-aware slippage ────────────────────────────────────
        volume_impact: bool = False,
        # ── Quant conventions (retrocompatible defaults) ────────────
        risk_free_rate: float = RISK_FREE_RATE,
        periods_per_year: int = TRADING_DAYS,
    ):
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be > 0")

        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.allow_short = allow_short
        self.position_sizing = position_sizing
        self.position_pct = position_pct
        self.volume_impact = volume_impact
        # Risk limits
        self.max_drawdown_pct = max_drawdown_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_value = max_position_value
        self.max_leverage = max_leverage
        self.risk_free_rate = risk_free_rate
        self.periods_per_year = periods_per_year

    def _compute_slippage(self, price: float, shares: float, volume: float) -> float:
        """Compute realistic slippage based on order size vs available volume.

        Uses square-root market impact model: slippage = base_slippage + sigma * sqrt(shares / ADV)
        where sigma is estimated from recent volatility.

        Falls back to static slippage_pct if volume data unavailable or volume_impact=False.
        """
        if not self.volume_impact or volume <= 0:
            return self.slippage_pct
        participation = abs(shares) / max(volume, 1)
        impact = self.slippage_pct + 0.1 * sqrt(participation)
        return min(impact, 0.02)  # Cap at 2%

    def run(
        self,
        df: pd.DataFrame,
        signal_fn: Callable[[pd.DataFrame], pd.Series],
        strategy_name: str = "Strategy",
        benchmark: Optional[pd.Series] = None,
    ) -> BacktestResult:
        """Execute a backtest.

        Args:
            df: OHLCV DataFrame.
            signal_fn: Function(df) → pd.Series of {-1, 0, 1}.
            strategy_name: Display name.
            benchmark: Optional benchmark close series for comparison.

        Returns:
            BacktestResult with trades, equity curve, metrics.
        """
        if df.empty or len(df) < 30:
            return BacktestResult(
                strategy_name=strategy_name,
                trades=[],
                equity_curve=pd.Series(dtype=float),
                benchmark_curve=pd.Series(dtype=float),
                metrics={},
            )

        signals = signal_fn(df).reindex(df.index).fillna(0)

        trades: List[Trade] = []
        capital = self.initial_capital
        equity = pd.Series(np.nan, index=df.index)
        equity.iloc[0] = capital

        position = 0.0   # shares held (negative = short)
        entry_price = 0.0
        entry_date = None
        prev_signal = 0

        # Risk limit tracking
        peak_equity = capital
        killed = False
        stop_loss_triggers = 0
        take_profit_triggers = 0

        # Pre-compute rolling average volume for volume-impact slippage
        _has_volume = self.volume_impact and "Volume" in df.columns
        if _has_volume:
            _avg_volume = df["Volume"].rolling(window=20, min_periods=1).mean()

        for i in range(1, len(df)):
            sig = int(signals.iloc[i])
            prev_sig = int(signals.iloc[i - 1])
            price = float(df["Close"].iloc[i])
            date = df.index[i]
            _vol_i = float(_avg_volume.iloc[i]) if _has_volume else 0.0

            # ── Risk limit checks (evaluated before signal logic) ─────
            current_equity = capital + position * price

            # 1. Max drawdown kill switch
            if current_equity > peak_equity:
                peak_equity = current_equity
            if self.max_drawdown_pct > 0 and current_equity < (1 - self.max_drawdown_pct) * peak_equity:
                if position != 0 and entry_date is not None:
                    _slip = self._compute_slippage(price, abs(position), _vol_i)
                    exec_price = price * (1 - _slip if position > 0 else 1 + _slip)
                    pnl = position * (exec_price - entry_price)
                    commission = abs(position * exec_price) * self.commission_pct
                    pnl -= commission
                    capital += position * exec_price - commission
                    trades.append(Trade(
                        entry_date=entry_date, exit_date=date,
                        direction="long" if position > 0 else "short",
                        entry_price=entry_price, exit_price=exec_price,
                        shares=abs(position),
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl / abs(position * entry_price) * 100, 2) if entry_price else 0,
                        exit_reason="Max drawdown kill switch",
                    ))
                    position = 0.0
                killed = True
                equity.iloc[i] = capital
                break

            # 2. Stop-loss per trade
            if self.stop_loss_pct > 0 and position != 0 and entry_date is not None:
                pos_pnl = position * (price - entry_price)
                threshold = -self.stop_loss_pct * entry_price * abs(position)
                if pos_pnl < threshold:
                    _slip = self._compute_slippage(price, abs(position), _vol_i)
                    exec_price = price * (1 - _slip if position > 0 else 1 + _slip)
                    pnl = position * (exec_price - entry_price)
                    commission = abs(position * exec_price) * self.commission_pct
                    pnl -= commission
                    capital += position * exec_price - commission
                    trades.append(Trade(
                        entry_date=entry_date, exit_date=date,
                        direction="long" if position > 0 else "short",
                        entry_price=entry_price, exit_price=exec_price,
                        shares=abs(position),
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl / abs(position * entry_price) * 100, 2) if entry_price else 0,
                        exit_reason="Stop-loss triggered",
                    ))
                    position = 0.0
                    entry_date = None
                    stop_loss_triggers += 1
                    equity.iloc[i] = capital
                    continue

            # 3. Take-profit per trade
            if self.take_profit_pct > 0 and position != 0 and entry_date is not None:
                pos_pnl = position * (price - entry_price)
                threshold = self.take_profit_pct * entry_price * abs(position)
                if pos_pnl > threshold:
                    _slip = self._compute_slippage(price, abs(position), _vol_i)
                    exec_price = price * (1 - _slip if position > 0 else 1 + _slip)
                    pnl = position * (exec_price - entry_price)
                    commission = abs(position * exec_price) * self.commission_pct
                    pnl -= commission
                    capital += position * exec_price - commission
                    trades.append(Trade(
                        entry_date=entry_date, exit_date=date,
                        direction="long" if position > 0 else "short",
                        entry_price=entry_price, exit_price=exec_price,
                        shares=abs(position),
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl / abs(position * entry_price) * 100, 2) if entry_price else 0,
                        exit_reason="Take-profit triggered",
                    ))
                    position = 0.0
                    entry_date = None
                    take_profit_triggers += 1
                    equity.iloc[i] = capital
                    continue
            # ── End risk limit checks ─────────────────────────────────

            # Signal change → execute
            if sig != prev_sig:
                # Close existing position
                if position != 0 and entry_date is not None:
                    _slip = self._compute_slippage(price, abs(position), _vol_i)
                    exec_price = price * (1 - _slip if position > 0 else 1 + _slip)
                    pnl = position * (exec_price - entry_price)
                    commission = abs(position * exec_price) * self.commission_pct
                    pnl -= commission
                    capital += position * exec_price - commission

                    trade = Trade(
                        entry_date=entry_date,
                        exit_date=date,
                        direction="long" if position > 0 else "short",
                        entry_price=entry_price,
                        exit_price=exec_price,
                        shares=abs(position),
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl / abs(position * entry_price) * 100, 2) if entry_price else 0,
                        exit_reason="Signal change",
                    )
                    trades.append(trade)
                    position = 0.0

                # Open new position
                if sig != 0:
                    alloc = capital * self.position_pct
                    _est_shares = alloc / price  # estimate for slippage calc
                    _slip = self._compute_slippage(price, _est_shares, _vol_i)
                    exec_price = price * (1 + _slip if sig > 0 else 1 - _slip)
                    shares = alloc / exec_price

                    # 4. Max position size limit
                    if self.max_position_value > 0:
                        max_shares = self.max_position_value / exec_price
                        shares = min(shares, max_shares)

                    # 5. Max leverage limit
                    current_eq = capital + position * price
                    if current_eq > 0:
                        max_exposure = self.max_leverage * current_eq
                        existing_exposure = abs(position * price)
                        available_exposure = max(max_exposure - existing_exposure, 0)
                        max_shares_lev = available_exposure / exec_price
                        shares = min(shares, max_shares_lev)
                    if sig < 0 and not self.allow_short:
                        pass
                    else:
                        actual_alloc = shares * exec_price
                        position = shares if sig > 0 else -shares
                        entry_price = exec_price
                        entry_date = date
                        commission = abs(shares * exec_price) * self.commission_pct
                        capital -= actual_alloc + commission

            # Mark-to-market
            equity.iloc[i] = capital + position * float(df["Close"].iloc[i])

        # Forward fill equity
        equity = equity.ffill()

        # Close final open position
        if position != 0 and entry_date is not None:
            last_price = float(df["Close"].iloc[-1])
            last_date = df.index[-1]
            pnl = position * (last_price - entry_price)
            trades.append(Trade(
                entry_date=entry_date,
                exit_date=last_date,
                direction="long" if position > 0 else "short",
                entry_price=entry_price,
                exit_price=last_price,
                shares=abs(position),
                pnl=round(pnl, 2),
                pnl_pct=round(pnl / abs(position * entry_price) * 100, 2),
                exit_reason="End of data",
            ))

        # Benchmark
        if benchmark is None:
            benchmark = df["Close"]
        bmk_start = float(benchmark.iloc[0])
        benchmark_curve = benchmark / bmk_start * self.initial_capital if bmk_start != 0 else benchmark

        metrics = self._compute_metrics(
            equity,
            trades,
            benchmark_curve,
            risk_free_rate=self.risk_free_rate,
            periods_per_year=self.periods_per_year,
        )
        metrics["killed_by_drawdown"] = killed
        metrics["max_drawdown_limit"] = self.max_drawdown_pct * 100
        metrics["stop_loss_triggers"] = stop_loss_triggers
        metrics["take_profit_triggers"] = take_profit_triggers

        signals_df = pd.DataFrame({"signal": signals, "close": df["Close"]})

        return BacktestResult(
            strategy_name=strategy_name,
            trades=trades,
            equity_curve=equity,
            benchmark_curve=benchmark_curve,
            metrics=metrics,
            signals=signals_df,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # WALK-FORWARD VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        signal_fn: Callable[[pd.DataFrame], pd.Series],
        strategy_name: str = "Strategy",
        benchmark: Optional[pd.Series] = None,
        train_pct: float = 0.70,
        n_folds: int = 1,
    ) -> BacktestResult:
        """Walk-forward backtest: train signals on past data, test on unseen future data.

        Prevents lookahead bias by ensuring signal_fn only sees data up to the
        current point in time.

        Args:
            df: OHLCV DataFrame
            signal_fn: Signal generation function
            strategy_name: Display name
            benchmark: Optional benchmark series
            train_pct: Fraction of data for initial training (default 70%)
            n_folds: Number of walk-forward folds (1 = single split, >1 = rolling)
        """
        n = len(df)
        if n < 30:
            return BacktestResult(
                strategy_name=strategy_name,
                trades=[],
                equity_curve=pd.Series(dtype=float),
                benchmark_curve=pd.Series(dtype=float),
                metrics={},
            )

        if n_folds < 1:
            n_folds = 1

        if n_folds == 1:
            # ── Single temporal split ───────────────────────────────────
            split_idx = int(n * train_pct)
            split_idx = max(split_idx, 30)   # need minimum training data
            split_idx = min(split_idx, n - 30)  # need minimum test data

            # Generate expanding-window signals for the test portion.
            # For efficiency: generate training signals once, then expand
            # through the test set.
            test_signals = pd.Series(0, index=df.index[split_idx:])
            for i in range(split_idx, n):
                historical = df.iloc[: i + 1]
                sig_series = signal_fn(historical)
                test_signals.iloc[i - split_idx] = int(sig_series.iloc[-1])

            # Wrap signal_fn so self.run() uses our pre-computed signals
            test_df = df.iloc[split_idx:].copy()

            def _precomputed_signal(frame: pd.DataFrame) -> pd.Series:
                return test_signals.reindex(frame.index).fillna(0)

            result = self.run(test_df, _precomputed_signal, strategy_name, benchmark)

            # Tag the result and return
            result.metrics["validation_mode"] = "walk_forward"
            result.metrics["n_folds"] = n_folds
            result.metrics["train_pct"] = train_pct
            return result

        else:
            # ── Rolling walk-forward with n_folds ───────────────────────
            initial_train_size = int(n * train_pct)
            initial_train_size = max(initial_train_size, 30)
            test_region = n - initial_train_size
            fold_size = max(test_region // n_folds, 1)

            all_trades: List[Trade] = []
            equity_parts: List[pd.Series] = []
            last_equity_value = self.initial_capital

            for fold in range(n_folds):
                fold_start = initial_train_size + fold * fold_size
                fold_end = (
                    initial_train_size + (fold + 1) * fold_size
                    if fold < n_folds - 1
                    else n
                )
                if fold_start >= n or fold_end <= fold_start:
                    break

                # Generate expanding-window signals for this fold
                fold_signals = pd.Series(0, index=df.index[fold_start:fold_end])
                for i in range(fold_start, fold_end):
                    historical = df.iloc[: i + 1]
                    sig_series = signal_fn(historical)
                    fold_signals.iloc[i - fold_start] = int(sig_series.iloc[-1])

                fold_df = df.iloc[fold_start:fold_end].copy()

                def _make_precomputed(sigs: pd.Series) -> Callable:
                    def _fn(frame: pd.DataFrame) -> pd.Series:
                        return sigs.reindex(frame.index).fillna(0)
                    return _fn

                # Create a sub-backtester that starts with the capital
                # carried over from the previous fold
                sub_bt = Backtester(
                    initial_capital=last_equity_value,
                    commission_pct=self.commission_pct,
                    slippage_pct=self.slippage_pct,
                    allow_short=self.allow_short,
                    position_sizing=self.position_sizing,
                    position_pct=self.position_pct,
                    max_drawdown_pct=self.max_drawdown_pct,
                    stop_loss_pct=self.stop_loss_pct,
                    take_profit_pct=self.take_profit_pct,
                    max_position_value=self.max_position_value,
                    max_leverage=self.max_leverage,
                    volume_impact=self.volume_impact,
                    risk_free_rate=self.risk_free_rate,
                    periods_per_year=self.periods_per_year,
                )
                fold_result = sub_bt.run(
                    fold_df, _make_precomputed(fold_signals), strategy_name, benchmark
                )

                if not fold_result.equity_curve.empty:
                    all_trades.extend(fold_result.trades)
                    equity_parts.append(fold_result.equity_curve)
                    last_equity_value = float(
                        fold_result.equity_curve.dropna().iloc[-1]
                    )

            # Concatenate equity curves across folds
            if equity_parts:
                equity_curve = pd.concat(equity_parts)
                # Remove duplicate indices (fold boundaries)
                equity_curve = equity_curve[~equity_curve.index.duplicated(keep="last")]
            else:
                equity_curve = pd.Series(dtype=float)

            # Benchmark
            if benchmark is None:
                benchmark = df["Close"]
            bmk_start = float(benchmark.iloc[0])
            benchmark_curve = (
                benchmark / bmk_start * self.initial_capital
                if bmk_start != 0
                else benchmark
            )

            metrics = self._compute_metrics(
                equity_curve,
                all_trades,
                benchmark_curve,
                risk_free_rate=self.risk_free_rate,
                periods_per_year=self.periods_per_year,
            )
            metrics["validation_mode"] = "walk_forward"
            metrics["n_folds"] = n_folds
            metrics["train_pct"] = train_pct

            return BacktestResult(
                strategy_name=strategy_name,
                trades=all_trades,
                equity_curve=equity_curve,
                benchmark_curve=benchmark_curve,
                metrics=metrics,
            )

    @staticmethod
    def validate_no_lookahead(
        signal_fn: Callable[[pd.DataFrame], pd.Series],
        df: pd.DataFrame,
        sample_points: int = 5,
    ) -> Dict:
        """Quick check: verify signal at time t doesn't change when future data is added.

        Generates signals on df[:t] and df[:t+50] for several sample points t,
        and checks that signal values at t are identical.

        Args:
            signal_fn: Signal generation function to validate.
            df: OHLCV DataFrame to use for testing.
            sample_points: Number of time points to check.

        Returns:
            Dict with 'passed' (bool), 'details' (list of per-point results),
            and 'message' (str summary).
        """
        n = len(df)
        if n < 100:
            return {
                "passed": False,
                "details": [],
                "message": "Not enough data to validate (need >= 100 rows).",
            }

        # Pick sample points spread across the middle of the data
        margin = 50
        usable_start = max(30, margin)
        usable_end = n - margin
        if usable_end <= usable_start:
            return {
                "passed": False,
                "details": [],
                "message": "Not enough data range after reserving margins.",
            }

        step = max((usable_end - usable_start) // max(sample_points, 1), 1)
        test_indices = list(range(usable_start, usable_end, step))[:sample_points]

        details = []
        all_passed = True

        for t in test_indices:
            # Signal with data up to t only
            sig_short = signal_fn(df.iloc[: t + 1])
            val_short = float(sig_short.iloc[-1])

            # Signal with data up to t+50 (future data added)
            extended = min(t + 50, n)
            sig_long = signal_fn(df.iloc[:extended])
            # Look at the signal value at position t
            val_long = float(sig_long.iloc[t])

            match = val_short == val_long
            if not match:
                all_passed = False

            details.append({
                "index": t,
                "date": str(df.index[t]),
                "signal_without_future": val_short,
                "signal_with_future": val_long,
                "passed": match,
            })

        return {
            "passed": all_passed,
            "details": details,
            "message": (
                "All sample points passed \u2014 no lookahead bias detected."
                if all_passed
                else (
                    f"Lookahead bias detected at "
                    f"{sum(1 for d in details if not d['passed'])}"
                    f"/{len(details)} sample points."
                )
            ),
        }

    @staticmethod
    def _compute_metrics(
        equity: pd.Series,
        trades: List[Trade],
        benchmark: pd.Series,
        *,
        risk_free_rate: float = RISK_FREE_RATE,
        periods_per_year: int = TRADING_DAYS,
    ) -> Dict:
        """Compute comprehensive performance metrics."""
        equity_clean = equity.dropna()
        if len(equity_clean) < 2:
            return {}

        returns = equity_clean.pct_change().dropna()
        if returns.empty:
            return {}

        total_return = (float(equity_clean.iloc[-1]) - float(equity_clean.iloc[0])) / float(equity_clean.iloc[0]) * 100

        # Annualized metrics driven by shared quant conventions.
        annualization_factor_vol = (
            ANNUALIZATION_FACTOR_VOL
            if periods_per_year == TRADING_DAYS
            else sqrt(float(periods_per_year))
        )
        cagr_decimal = annualize_geometric_return(
            returns.values,
            trading_days=periods_per_year,
        )
        cagr = cagr_decimal * 100.0
        vol_ann_decimal = annualize_volatility(
            float(returns.std()),
            annualization_factor=annualization_factor_vol,
        )
        vol_ann = vol_ann_decimal * 100.0
        sharpe = sharpe_ratio(
            cagr_decimal,
            vol_ann_decimal,
            risk_free_rate=risk_free_rate,
        )

        # Drawdown
        peak = equity_clean.cummax()
        dd = (equity_clean - peak) / peak * 100
        max_dd = float(dd.min())

        # Win rate
        pnls = [t.pnl for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        win_rate = wins / len(pnls) * 100 if pnls else 0

        avg_win = np.mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 0
        avg_loss = abs(np.mean([p for p in pnls if p <= 0])) if any(p <= 0 for p in pnls) else 0
        profit_factor = (wins * avg_win) / max(losses * avg_loss, 0.01)

        # Benchmark comparison
        bmk_clean = benchmark.reindex(equity_clean.index).dropna()
        bmk_return = (float(bmk_clean.iloc[-1]) - float(bmk_clean.iloc[0])) / float(bmk_clean.iloc[0]) * 100 if len(bmk_clean) > 1 else 0
        alpha = total_return - bmk_return

        # Calmar ratio
        calmar = abs(cagr / max_dd) if max_dd != 0 else 0

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_vol_decimal = annualize_volatility(
                float(downside_returns.std()),
                annualization_factor=annualization_factor_vol,
            )
        else:
            downside_vol_decimal = 0.0
        sortino = (
            (cagr_decimal - risk_free_rate) / downside_vol_decimal
            if downside_vol_decimal > 0
            else 0.0
        )

        return {
            "total_return":    round(total_return, 2),
            "cagr":            round(cagr, 2),
            "sharpe":          round(sharpe, 2),
            "sortino":         round(sortino, 2),
            "calmar":          round(calmar, 2),
            "max_drawdown":    round(max_dd, 2),
            "volatility_ann":  round(vol_ann, 2),
            "win_rate":        round(win_rate, 1),
            "n_trades":        len(trades),
            "avg_win":         round(avg_win, 2),
            "avg_loss":        round(avg_loss, 2),
            "profit_factor":   round(profit_factor, 2),
            "alpha":           round(alpha, 2),
            "benchmark_return": round(bmk_return, 2),
            "risk_free_rate_used": round(risk_free_rate, 6),
            "periods_per_year_used": int(periods_per_year),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # CHART RENDERING
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def render_result(result: BacktestResult) -> go.Figure:
        """Render equity curve with benchmark overlay and drawdown panel."""
        if result.equity_curve.empty:
            return go.Figure()

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.70, 0.30],
            subplot_titles=["Equity Curve", "Drawdown"],
        )

        # Equity curve
        fig.add_trace(go.Scatter(
            x=result.equity_curve.index,
            y=result.equity_curve.values,
            name=result.strategy_name,
            line=dict(color=_C["blue"], width=2),
        ), row=1, col=1)

        if not result.benchmark_curve.empty:
            fig.add_trace(go.Scatter(
                x=result.benchmark_curve.index,
                y=result.benchmark_curve.values,
                name="Benchmark",
                line=dict(color=_C["text_muted"], width=1.5, dash="dot"),
            ), row=1, col=1)

        # Trade markers
        for t in result.trades:
            if t.exit_date:
                color = _C["green"] if t.pnl > 0 else _C["red"]
                fig.add_trace(go.Scatter(
                    x=[t.entry_date, t.exit_date],
                    y=[t.entry_price, t.exit_price],
                    mode="markers",
                    marker=dict(color=color, size=6, symbol="triangle-up" if t.direction == "long" else "triangle-down"),
                    showlegend=False,
                    hovertemplate=f"{t.direction.upper()}<br>Entry: {t.entry_price:.2f}<br>Exit: {t.exit_price:.2f}<br>P&L: ${t.pnl:.2f}<extra></extra>",
                ), row=1, col=1)

        # Drawdown
        ec = result.equity_curve.dropna()
        peak = ec.cummax()
        dd = (ec - peak) / peak * 100
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            name="Drawdown",
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.2)",
            line=dict(color=_C["red"], width=1),
        ), row=2, col=1)

        m = result.metrics
        title_text = (
            f"<b>{result.strategy_name}</b>  |  "
            f"Return: {m.get('total_return', 0):.1f}%  |  "
            f"Sharpe: {m.get('sharpe', 0):.2f}  |  "
            f"Max DD: {m.get('max_drawdown', 0):.1f}%  |  "
            f"Win Rate: {m.get('win_rate', 0):.0f}%  |  "
            f"Trades: {m.get('n_trades', 0)}"
        )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=dict(text=title_text, font=dict(size=13)),
            height=550,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis2=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            yaxis2=dict(gridcolor=_C["border"], ticksuffix="%"),
        )
        return fig
