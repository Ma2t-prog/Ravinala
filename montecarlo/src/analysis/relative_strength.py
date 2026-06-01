"""
relative_strength.py — RS ranking and comparison charts.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from .core import DARK_THEME

_C = DARK_THEME


class RelativeStrength:
    """Relative strength ranking and RS charts."""

    @staticmethod
    def rs_score(symbol: str, benchmark: str = "SPY",
                  period_days: int = 252) -> Optional[float]:
        """Compute a simple relative strength score (0–100 percentile).

        Uses the ratio of symbol returns to benchmark returns over the period.

        Returns:
            RS score 0–100, or None on failure.
        """
        try:
            raw = yf.download([symbol, benchmark], period="2y", interval="1d",
                               auto_adjust=True, progress=False)["Close"]
        except Exception:
            return None

        if raw.empty or raw.shape[1] < 2:
            return None

        raw = raw.dropna()
        if len(raw) < period_days:
            period_days = len(raw) - 1

        sym_ret = float((raw[symbol].iloc[-1] - raw[symbol].iloc[-period_days])
                         / raw[symbol].iloc[-period_days] * 100)
        bmk_ret = float((raw[benchmark].iloc[-1] - raw[benchmark].iloc[-period_days])
                         / raw[benchmark].iloc[-period_days] * 100)

        rs_raw = sym_ret - bmk_ret
        return rs_raw

    @staticmethod
    def rs_rank_universe(symbols: List[str], benchmark: str = "SPY",
                          period_days: int = 252) -> pd.DataFrame:
        """Rank a list of symbols by relative strength.

        Args:
            symbols: List of tickers to rank.
            benchmark: Benchmark ticker.
            period_days: Lookback in trading days.

        Returns:
            DataFrame: Rank | Symbol | RS Score | RS Percentile | Trend
        """
        def _compute(sym: str) -> Optional[Dict]:
            score = RelativeStrength.rs_score(sym, benchmark, period_days)
            if score is None:
                return None
            return {"symbol": sym, "rs_score": score}

        rows = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(_compute, s) for s in symbols]
            for f in as_completed(futures):
                r = f.result()
                if r:
                    rows.append(r)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).sort_values("rs_score", ascending=False).reset_index(drop=True)
        df.index += 1
        df.index.name = "Rank"

        n = len(df)
        df["rs_pct"] = [(n - i) / n * 100 for i in range(n)]
        df["rs_pct"] = df["rs_pct"].round(1)
        df["trend"] = df["rs_score"].apply(
            lambda x: "[OK] Leader" if x > 10 else ("[ERR] Laggard" if x < -10 else "[WARN] Neutral")
        )

        return df.reset_index()

    @staticmethod
    def render_rs_chart(symbol: str, benchmark: str = "SPY",
                         period: str = "1y") -> go.Figure:
        """Chart ratio of symbol price to benchmark price.

        Args:
            symbol: Target symbol.
            benchmark: Benchmark to compare against.
            period: Historical period.

        Returns:
            Plotly figure with price ratio and RS momentum.
        """
        try:
            raw = yf.download([symbol, benchmark], period=period, interval="1d",
                               auto_adjust=True, progress=False)["Close"]
        except Exception:
            return go.Figure()

        if raw.empty or raw.shape[1] < 2:
            return go.Figure()

        raw = raw.dropna()
        ratio = raw[symbol] / raw[benchmark]
        ratio_sma = ratio.rolling(20).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ratio.index, y=ratio.values,
            name=f"{symbol}/{benchmark}",
            line=dict(color=_C["blue"], width=2),
            hovertemplate="%{x}<br>RS: %{y:.4f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=ratio_sma.index, y=ratio_sma.values,
            name="SMA(20)",
            line=dict(color=_C["yellow"], width=1.5, dash="dot"),
        ))

        # Color fill when ratio > sma (leading) vs below (lagging)
        bull_ratio = ratio.copy()
        bull_ratio[ratio < ratio_sma] = np.nan
        bear_ratio = ratio.copy()
        bear_ratio[ratio >= ratio_sma] = np.nan

        fig.add_trace(go.Scatter(
            x=bull_ratio.index, y=bull_ratio.values,
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.08)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=bear_ratio.index, y=bear_ratio.values,
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.08)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{symbol}</b> vs <b>{benchmark}</b> — Relative Strength",
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            height=380,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        return fig
