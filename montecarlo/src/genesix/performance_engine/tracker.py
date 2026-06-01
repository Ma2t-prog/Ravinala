"""
GenesiX Performance Tracker — v2.1
NAV calculation, rolling returns, benchmark comparison, calendar returns.

Usage:
    tracker = PerformanceTracker(
        tickers=["AAPL", "MSFT", "GOOGL"],
        weights={"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25},
        benchmark="SPY",
        period="5y",
    )
    snapshot = tracker.run()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from genesix.utils.quant_conventions import (
    ANNUALIZATION_FACTOR_VOL,
    RISK_FREE_RATE as CONVENTION_RISK_FREE_RATE,
    TRADING_DAYS,
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class PerformanceSnapshot:
    """Complete performance analytics for a portfolio."""

    # NAV
    nav: pd.Series  # daily portfolio NAV indexed by datetime
    benchmark_nav: pd.Series  # daily benchmark NAV

    # Returns
    daily_returns: pd.Series
    benchmark_daily_returns: pd.Series
    cumulative_returns: pd.Series
    benchmark_cumulative_returns: pd.Series

    # Rolling returns
    rolling_1m: pd.Series
    rolling_3m: pd.Series
    rolling_6m: pd.Series
    rolling_1y: pd.Series

    # Calendar returns (year × month pivot)
    calendar_returns: pd.DataFrame  # index=year, columns=month name

    # Drawdown
    drawdown_series: pd.Series  # underwater chart
    max_drawdown: float  # worst peak→trough (negative %)

    # Risk-adjusted metrics
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    annual_return: float  # %
    annual_volatility: float  # %

    # Benchmark comparison
    alpha: float  # annualised excess return %
    beta: float
    tracking_error: float  # %
    information_ratio: float

    # Distribution
    skewness: float
    kurtosis: float
    var_95: float  # daily %
    cvar_95: float  # daily %
    best_day: float  # %
    worst_day: float  # %
    win_rate: float  # fraction of positive days

    # Per-instrument attribution
    instrument_returns: Dict[str, float]  # ticker → total return %
    instrument_contribution: Dict[str, float]  # ticker → weighted contribution %


# ============================================================================
# TRACKER
# ============================================================================


class PerformanceTracker:
    """Calculate portfolio performance analytics from ticker weights."""

    # Backward-compatible alias sourced from the shared quant conventions.
    RISK_FREE_RATE = CONVENTION_RISK_FREE_RATE

    def __init__(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        benchmark: str = "SPY",
        period: str = "5y",
        initial_nav: float = 10_000.0,
        risk_free_rate: float | None = None,
    ):
        self.tickers = tickers
        self.weights = weights
        self.benchmark = benchmark
        self.period = period
        self.initial_nav = initial_nav
        self.rf = (
            risk_free_rate
            if risk_free_rate is not None
            else CONVENTION_RISK_FREE_RATE
        )

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def run(self) -> Optional[PerformanceSnapshot]:
        """Fetch data, compute everything, return snapshot."""
        prices = self._fetch_prices()
        if prices is None:
            return None

        benchmark_prices = self._fetch_benchmark()
        if benchmark_prices is None:
            return None

        # Align dates
        common = prices.index.intersection(benchmark_prices.index)
        prices = prices.loc[common]
        benchmark_prices = benchmark_prices.loc[common]

        # Portfolio NAV (buy-and-hold from day 0)
        nav = self._compute_nav(prices)
        bench_nav = self.initial_nav * (benchmark_prices / benchmark_prices.iloc[0])

        # Returns
        daily_ret = nav.pct_change().dropna()
        bench_ret = bench_nav.pct_change().dropna()
        cum_ret = (1 + daily_ret).cumprod() - 1
        bench_cum = (1 + bench_ret).cumprod() - 1

        # Rolling returns (annualised)
        rolling_1m = daily_ret.rolling(21).apply(
            lambda x: (1 + x).prod() ** (TRADING_DAYS / 21) - 1, raw=False
        )
        rolling_3m = daily_ret.rolling(63).apply(
            lambda x: (1 + x).prod() ** (TRADING_DAYS / 63) - 1, raw=False
        )
        rolling_6m = daily_ret.rolling(126).apply(
            lambda x: (1 + x).prod() ** (TRADING_DAYS / 126) - 1, raw=False
        )
        rolling_1y = daily_ret.rolling(TRADING_DAYS).apply(
            lambda x: (1 + x).prod() ** (TRADING_DAYS / TRADING_DAYS) - 1, raw=False
        )

        # Calendar returns
        calendar = self._calendar_returns(daily_ret)

        # Drawdown
        dd_series = self._drawdown_series(nav)
        max_dd = float(dd_series.min()) * 100

        # Metrics
        n = len(daily_ret)
        ann_ret = float((1 + daily_ret).prod() ** (TRADING_DAYS / max(n, 1)) - 1) * 100
        ann_vol = float(daily_ret.std() * ANNUALIZATION_FACTOR_VOL) * 100

        sharpe = (ann_ret / 100 - self.rf) / max(ann_vol / 100, 1e-6)
        down = daily_ret[daily_ret < 0]
        down_vol = (
            float(down.std() * ANNUALIZATION_FACTOR_VOL) if len(down) > 1 else 1e-6
        )
        sortino = (ann_ret / 100 - self.rf) / max(down_vol, 1e-6)
        calmar = (ann_ret / 100) / max(abs(max_dd / 100), 1e-6)

        # Benchmark comparison
        beta = self._beta(daily_ret, bench_ret)
        bench_ann = float(
            (1 + bench_ret).prod() ** (TRADING_DAYS / max(len(bench_ret), 1)) - 1
        )
        alpha_val = (ann_ret / 100) - (self.rf + beta * (bench_ann - self.rf))
        excess = daily_ret.values - bench_ret.reindex(daily_ret.index).fillna(0).values
        te = float(np.std(excess, ddof=1) * ANNUALIZATION_FACTOR_VOL) * 100
        ir = (ann_ret - bench_ann * 100) / max(te, 1e-6)

        # Distribution
        from scipy import stats as sp_stats

        skew = float(sp_stats.skew(daily_ret.values))
        kurt = float(sp_stats.kurtosis(daily_ret.values))
        var95 = float(np.percentile(daily_ret, 5)) * 100
        tail = daily_ret[daily_ret <= np.percentile(daily_ret, 5)]
        cvar95 = float(tail.mean()) * 100 if len(tail) > 0 else var95

        # Attribution
        inst_ret, inst_contrib = self._attribution(prices)

        return PerformanceSnapshot(
            nav=nav,
            benchmark_nav=bench_nav,
            daily_returns=daily_ret,
            benchmark_daily_returns=bench_ret,
            cumulative_returns=cum_ret,
            benchmark_cumulative_returns=bench_cum,
            rolling_1m=rolling_1m,
            rolling_3m=rolling_3m,
            rolling_6m=rolling_6m,
            rolling_1y=rolling_1y,
            calendar_returns=calendar,
            drawdown_series=dd_series,
            max_drawdown=max_dd,
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            calmar_ratio=round(calmar, 3),
            annual_return=round(ann_ret, 2),
            annual_volatility=round(ann_vol, 2),
            alpha=round(alpha_val * 100, 2),
            beta=round(beta, 3),
            tracking_error=round(te, 2),
            information_ratio=round(ir, 3),
            skewness=round(skew, 3),
            kurtosis=round(kurt, 3),
            var_95=round(var95, 3),
            cvar_95=round(cvar95, 3),
            best_day=round(float(daily_ret.max()) * 100, 3),
            worst_day=round(float(daily_ret.min()) * 100, 3),
            win_rate=round(float((daily_ret > 0).mean()), 3),
            instrument_returns=inst_ret,
            instrument_contribution=inst_contrib,
        )

    # ------------------------------------------------------------------
    # DATA FETCHING
    # ------------------------------------------------------------------

    def _fetch_prices(self) -> Optional[pd.DataFrame]:
        """Fetch close prices for portfolio tickers."""
        try:
            data = yf.download(
                self.tickers, period=self.period, progress=False, auto_adjust=True
            )
            if data.empty:
                logger.error("Empty price data")
                return None

            if isinstance(data.columns, pd.MultiIndex):
                prices = data["Close"]
            else:
                prices = data[["Close"]].rename(columns={"Close": self.tickers[0]})

            return prices.dropna()
        except Exception as e:
            logger.error("Price fetch failed: %s", e)
            return None

    def _fetch_benchmark(self) -> Optional[pd.Series]:
        """Fetch benchmark close prices."""
        try:
            data = yf.download(
                self.benchmark, period=self.period, progress=False, auto_adjust=True
            )
            if data.empty:
                return None
            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            return close.dropna()
        except Exception as e:
            logger.error("Benchmark fetch failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # COMPUTATIONS
    # ------------------------------------------------------------------

    def _compute_nav(self, prices: pd.DataFrame) -> pd.Series:
        """Buy-and-hold NAV from initial weights."""
        # Normalise each ticker to 1.0 at start
        normalised = prices / prices.iloc[0]
        # Weighted sum
        weighted = sum(
            normalised[t] * self.weights.get(t, 0)
            for t in prices.columns
            if t in self.weights
        )
        return self.initial_nav * weighted

    @staticmethod
    def _drawdown_series(nav: pd.Series) -> pd.Series:
        """Underwater chart: (NAV - peak) / peak."""
        peak = nav.expanding().max()
        return (nav - peak) / peak

    @staticmethod
    def _calendar_returns(daily_returns: pd.Series) -> pd.DataFrame:
        """Monthly returns pivoted as year × month."""
        monthly = daily_returns.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
        df = monthly.to_frame("ret")
        df["year"] = df.index.year
        df["month"] = df.index.month
        pivot = df.pivot_table(values="ret", index="year", columns="month", aggfunc="sum")
        month_map = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
        }
        pivot = pivot.rename(columns=month_map)
        # Add YTD column
        pivot["YTD"] = pivot.apply(
            lambda row: ((1 + row.dropna() / 100).prod() - 1) * 100, axis=1
        )
        return pivot

    @staticmethod
    def _beta(port_ret: pd.Series, bench_ret: pd.Series) -> float:
        """Calculate portfolio beta vs benchmark."""
        common = port_ret.index.intersection(bench_ret.index)
        if len(common) < 20:
            return 1.0
        p = port_ret.loc[common].values.flatten()
        b = bench_ret.loc[common].values.flatten()
        cov = np.cov(p, b)
        var_b = cov[1, 1]
        if var_b < 1e-12:
            return 1.0
        return float(cov[0, 1] / var_b)

    def _attribution(
        self, prices: pd.DataFrame
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """Per-instrument total return and weighted contribution."""
        inst_ret: Dict[str, float] = {}
        inst_contrib: Dict[str, float] = {}
        for t in self.tickers:
            if t not in prices.columns:
                continue
            total = (prices[t].iloc[-1] / prices[t].iloc[0] - 1) * 100
            inst_ret[t] = round(total, 2)
            inst_contrib[t] = round(total * self.weights.get(t, 0), 2)
        return inst_ret, inst_contrib


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================


def track_portfolio(
    tickers: List[str],
    weights: Dict[str, float],
    benchmark: str = "SPY",
    period: str = "5y",
    initial_nav: float = 10_000.0,
) -> Optional[PerformanceSnapshot]:
    """One-call convenience wrapper."""
    return PerformanceTracker(
        tickers=tickers,
        weights=weights,
        benchmark=benchmark,
        period=period,
        initial_nav=initial_nav,
    ).run()
