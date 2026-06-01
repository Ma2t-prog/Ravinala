"""
sector_rotation.py — Relative Rotation Graph (RRG) and sector performance analysis.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from .core import DARK_THEME

_C = DARK_THEME


SECTORS: Dict[str, str] = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLE":  "Energy",
    "XLV":  "Healthcare",
    "XLI":  "Industrials",
    "XLY":  "Consumer Disc.",
    "XLP":  "Consumer Staples",
    "XLU":  "Utilities",
    "XLRE": "Real Estate",
    "XLC":  "Communication",
    "XLB":  "Materials",
}

_QUADRANT_COLORS = {
    "Leading":   "#22c55e",
    "Weakening": "#f59e0b",
    "Lagging":   "#ef4444",
    "Improving": "#3b82f6",
}

_QUADRANT_DESCS = {
    "Leading":   "Outperforming market with positive momentum → overweight",
    "Weakening": "Outperforming but momentum fading → watch for exit",
    "Lagging":   "Underperforming with negative momentum → underweight",
    "Improving": "Underperforming but momentum improving → watch for entry",
}


class SectorRotation:
    """Relative Rotation Graph (RRG) — sector rotation visualization."""

    @staticmethod
    @st.cache_data(ttl=300)
    def _get_sector_data(benchmark: str,
                          lookback: int) -> Optional[pd.DataFrame]:
        """Fetch weekly close data for all sectors + benchmark."""
        tickers = list(SECTORS.keys()) + [benchmark]
        try:
            raw = yf.download(tickers, period="3y", interval="1wk",
                               auto_adjust=True, progress=False)["Close"]
        except Exception:
            return None

        if isinstance(raw, pd.Series):
            raw = raw.to_frame()

        if raw.empty:
            return None

        raw = raw.dropna(how="all")
        return raw

    @staticmethod
    def _compute_rrg_values(sector_prices: pd.Series,
                              benchmark_prices: pd.Series,
                              period: int = 10) -> Tuple[pd.Series, pd.Series]:
        """Compute RS-Ratio and RS-Momentum for one sector.

        RS-Ratio:   Normalized relative strength vs benchmark.
        RS-Momentum: Rate of change of RS-Ratio.

        Returns:
            (rs_ratio, rs_momentum) as pd.Series.
        """
        # Relative strength
        rs = sector_prices / benchmark_prices.replace(0, np.nan)
        rs = rs.dropna()

        # Smooth with EMA
        rs_ema = rs.ewm(span=period, adjust=False).mean()

        # Normalize to 100-centered scale
        rs_mean = rs_ema.rolling(period).mean()
        rs_std  = rs_ema.rolling(period).std().replace(0, np.nan)
        rs_ratio = 100 + (rs_ema - rs_mean) / rs_std * 10

        # Momentum = rate of change of RS-Ratio
        rs_momentum = 100 + rs_ratio.pct_change(1) * 100

        return rs_ratio, rs_momentum

    def rrg_chart(self, benchmark: str = "SPY",
                   lookback: int = 12,
                   tail_length: int = 4) -> go.Figure:
        """Render a Relative Rotation Graph.

        Each sector is shown as a dot on (RS-Ratio, RS-Momentum) axes.
        A tail shows the last `tail_length` weeks of trajectory.

        Quadrants:
        - Top-right   (RS>100, Mom>100): Leading
        - Bottom-right (RS>100, Mom<100): Weakening
        - Bottom-left  (RS<100, Mom<100): Lagging
        - Top-left     (RS<100, Mom>100): Improving

        Args:
            benchmark: Benchmark ticker (e.g., 'SPY').
            lookback: Weeks to display in the tail.
            tail_length: Number of history points to show per sector.

        Returns:
            Plotly Figure.
        """
        data = self._get_sector_data(benchmark, lookback)
        if data is None:
            return go.Figure()

        bench = data[benchmark] if benchmark in data.columns else None
        if bench is None:
            return go.Figure()

        fig = go.Figure()

        # Quadrant backgrounds
        for xrange, yrange, qname in [
            ([100, 115], [100, 115], "Leading"),
            ([100, 115], [85, 100],  "Weakening"),
            ([85, 100],  [85, 100],  "Lagging"),
            ([85, 100],  [100, 115], "Improving"),
        ]:
            fig.add_shape(
                type="rect",
                x0=xrange[0], x1=xrange[1],
                y0=yrange[0], y1=yrange[1],
                fillcolor=f"{_QUADRANT_COLORS[qname]}18",
                line=dict(width=0),
                layer="below",
            )
            fig.add_annotation(
                x=(xrange[0] + xrange[1]) / 2,
                y=(yrange[0] + yrange[1]) / 2,
                text=f"<b>{qname}</b>",
                showarrow=False,
                font=dict(
                    size=14,
                    color=f"{_QUADRANT_COLORS[qname]}60",
                ),
            )

        # Center lines
        fig.add_vline(x=100, line=dict(color=_C["border"], width=1, dash="dash"))
        fig.add_hline(y=100, line=dict(color=_C["border"], width=1, dash="dash"))

        # Plot each sector
        sector_tails: Dict[str, Dict] = {}
        for ticker, name in SECTORS.items():
            if ticker not in data.columns:
                continue

            sector_data = data[ticker].dropna()
            bench_aligned = bench.reindex(sector_data.index).dropna()
            sector_aligned = sector_data.reindex(bench_aligned.index)

            if len(sector_aligned) < 20:
                continue

            rs_ratio, rs_momentum = self._compute_rrg_values(
                sector_aligned, bench_aligned
            )
            rs_ratio    = rs_ratio.dropna()
            rs_momentum = rs_momentum.dropna()

            if rs_ratio.empty or rs_momentum.empty:
                continue

            common = rs_ratio.index.intersection(rs_momentum.index)
            if len(common) < 2:
                continue

            rs_ratio    = rs_ratio.reindex(common).iloc[-tail_length:]
            rs_momentum = rs_momentum.reindex(common).iloc[-tail_length:]

            xs = rs_ratio.values.tolist()
            ys = rs_momentum.values.tolist()

            # Determine current quadrant
            x_curr, y_curr = xs[-1], ys[-1]
            if x_curr >= 100 and y_curr >= 100:
                quadrant = "Leading"
            elif x_curr >= 100 and y_curr < 100:
                quadrant = "Weakening"
            elif x_curr < 100 and y_curr < 100:
                quadrant = "Lagging"
            else:
                quadrant = "Improving"

            color = _QUADRANT_COLORS[quadrant]
            sector_tails[ticker] = {"quadrant": quadrant, "x": x_curr, "y": y_curr}

            # Tail (faded line)
            if len(xs) > 1:
                fig.add_trace(go.Scatter(
                    x=xs[:-1], y=ys[:-1],
                    mode="lines",
                    line=dict(color=f"{color}60", width=1.5, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

            # Dot + label
            fig.add_trace(go.Scatter(
                x=[x_curr], y=[y_curr],
                mode="markers+text",
                name=f"{ticker} ({quadrant})",
                marker=dict(
                    size=16,
                    color=color,
                    line=dict(width=2, color="white"),
                    symbol="circle",
                ),
                text=[ticker],
                textposition="top center",
                textfont=dict(size=11, color=_C["text"]),
                hovertemplate=(
                    f"<b>{name} ({ticker})</b><br>"
                    f"Quadrant: {quadrant}<br>"
                    f"RS-Ratio: {x_curr:.1f}<br>"
                    f"RS-Momentum: {y_curr:.1f}<br>"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=dict(
                text=f"<b>Relative Rotation Graph</b> vs {benchmark}",
                font=dict(size=16),
            ),
            xaxis=dict(
                title="RS-Ratio (Relative Strength)",
                range=[85, 115],
                gridcolor=_C["border"],
                zeroline=False,
            ),
            yaxis=dict(
                title="RS-Momentum",
                range=[85, 115],
                gridcolor=_C["border"],
                zeroline=False,
            ),
            height=600,
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10),
                x=1.01,
            ),
            margin=dict(l=60, r=200, t=60, b=60),
        )

        return fig

    @staticmethod
    @st.cache_data(ttl=300)
    def sector_performance_table(periods: Optional[List[str]] = None) -> pd.DataFrame:
        """Build a sector performance table across multiple time periods.

        Args:
            periods: List of yfinance period strings. Defaults to common periods.

        Returns:
            DataFrame: Sector | 1D | 1W | 1M | 3M | 6M | YTD | 1Y
        """
        if periods is None:
            periods = ["5d", "1mo", "3mo", "6mo", "1y"]

        rows = []
        for ticker, name in SECTORS.items():
            row: Dict = {"Sector": name, "ETF": ticker}
            try:
                df = yf.download(ticker, period="2y", interval="1d",
                                  auto_adjust=True, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.empty or "Close" not in df.columns:
                    continue
                close = df["Close"]
                price = float(close.iloc[-1])
                row["Price"] = round(price, 2)

                def _ret(days: int) -> Optional[float]:
                    if len(close) > days:
                        v = float((close.iloc[-1] - close.iloc[-days]) / close.iloc[-days] * 100)
                        return round(v, 2)
                    return None

                row["1D %"]  = _ret(1)
                row["1W %"]  = _ret(5)
                row["1M %"]  = _ret(21)
                row["3M %"]  = _ret(63)
                row["6M %"]  = _ret(126)
                row["1Y %"]  = _ret(252)

                rows.append(row)
            except Exception:
                continue

        if not rows:
            return pd.DataFrame()

        df_result = pd.DataFrame(rows)
        if "1M %" in df_result.columns:
            df_result = df_result.sort_values("1M %", ascending=False)
        return df_result.reset_index(drop=True)
