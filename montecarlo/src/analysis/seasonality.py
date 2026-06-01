"""
seasonality.py — Monthly seasonality heatmap, day-of-week analysis, and event patterns.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from .core import DARK_THEME

_C = DARK_THEME


class SeasonalityAnalyzer:
    """Seasonality and calendar-pattern analysis."""

    # ─────────────────────────────────────────────────────────────────────────
    # MONTHLY RETURNS HEATMAP
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=3600)
    def monthly_returns_heatmap(ticker: str, years: int = 10) -> pd.DataFrame:
        """Build a (Years × 12 Months) matrix of monthly returns.

        Args:
            ticker: Ticker symbol.
            years: Number of years of history.

        Returns:
            DataFrame where index = year, columns = months (Jan–Dec),
            plus summary rows: 'Avg' and 'Win Rate %'.
        """
        try:
            df = yf.download(ticker, period=f"{years}y", interval="1mo",
                              auto_adjust=True, progress=False)
        except Exception:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()

        df["Return"] = df["Close"].pct_change() * 100
        df = df.dropna(subset=["Return"])
        df["Year"] = df.index.year
        df["Month"] = df.index.month

        months = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                  7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

        pivot = df.pivot_table(values="Return", index="Year", columns="Month", aggfunc="sum")
        pivot.columns = [months[c] for c in pivot.columns]

        # Add summary rows
        avg_row = pivot.mean()
        win_rate_row = (pivot > 0).mean() * 100

        summary = pd.DataFrame([avg_row, win_rate_row], index=["Avg %", "Win Rate %"])
        result = pd.concat([pivot, summary])
        return result

    def render_monthly_heatmap(self, ticker: str, years: int = 10) -> go.Figure:
        """Render the monthly returns heatmap as a Plotly figure."""
        data = self.monthly_returns_heatmap(ticker, years)
        if data.empty:
            return go.Figure()

        # Separate data and summary
        data_rows = data.drop(index=["Avg %", "Win Rate %"], errors="ignore")
        months_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cols = [m for m in months_order if m in data_rows.columns]
        z = data_rows[cols].values.astype(float)

        # Annotation text
        text = np.where(
            np.isnan(z),
            "",
            [[f"{v:.1f}%" for v in row] for row in z]
        )

        fig = go.Figure(go.Heatmap(
            z=z,
            x=cols,
            y=[str(y) for y in data_rows.index],
            colorscale=[
                [0.0,  "#7f1d1d"],
                [0.35, "#ef4444"],
                [0.48, "#1e293b"],
                [0.52, "#1e293b"],
                [0.65, "#22c55e"],
                [1.0,  "#14532d"],
            ],
            zmid=0,
            text=text,
            texttemplate="%{text}",
            hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>",
            colorbar=dict(
                title="Return %",
                tickfont=dict(color=_C["text"]),
                titlefont=dict(color=_C["text"]),
            ),
        ))

        # Overlay averages at bottom
        avg_row = data.loc["Avg %"] if "Avg %" in data.index else None
        if avg_row is not None:
            avg_vals = [float(avg_row.get(m, 0)) for m in cols]
            for i, (m, v) in enumerate(zip(cols, avg_vals)):
                color = "#22c55e" if v >= 0 else "#ef4444"
                fig.add_annotation(
                    x=m,
                    y=-0.05,
                    text=f"<b>{v:.1f}%</b>",
                    showarrow=False,
                    font=dict(size=10, color=color),
                    xref="x",
                    yref="paper",
                )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{ticker}</b> — Monthly Returns Seasonality ({years}Y)",
            height=max(350, len(data_rows) * 22 + 120),
            xaxis=dict(side="top"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=60, r=60, t=80, b=60),
        )
        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # DAY OF WEEK
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=3600)
    def day_of_week_analysis(ticker: str, years: int = 5) -> pd.DataFrame:
        """Average return by day of week.

        Returns:
            DataFrame with columns [Day, Avg Return %, Win Rate %, Count].
        """
        try:
            df = yf.download(ticker, period=f"{years}y", interval="1d",
                              auto_adjust=True, progress=False)
        except Exception:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()

        df["Return"] = df["Close"].pct_change() * 100
        df["Day"] = df.index.day_name()
        df = df.dropna(subset=["Return"])

        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        result = []
        for day in order:
            subset = df[df["Day"] == day]["Return"]
            if len(subset) > 0:
                result.append({
                    "Day":            day,
                    "Avg Return %":   round(float(subset.mean()), 3),
                    "Win Rate %":     round(float((subset > 0).mean() * 100), 1),
                    "Median Return":  round(float(subset.median()), 3),
                    "Count":          len(subset),
                })

        return pd.DataFrame(result)

    # ─────────────────────────────────────────────────────────────────────────
    # PRE/POST EVENT ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=3600)
    def pre_post_event_analysis(ticker: str,
                                  event_type: str = "earnings") -> Dict:
        """Analyze price behavior before and after recurring events.

        Computes average return in [-5, -1] days before and [+1, +5] days after
        each event occurrence.

        Args:
            ticker: Ticker symbol.
            event_type: 'earnings' (only type supported via yfinance).

        Returns:
            Dict with pre_event_avg, post_event_avg, events list.
        """
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5y", auto_adjust=True)
            earn_hist = t.earnings_history
        except Exception:
            return {}

        if hist is None or hist.empty:
            return {}

        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        close = hist["Close"]
        events = []

        if earn_hist is not None and not earn_hist.empty:
            try:
                dates = earn_hist.index.tolist()
                for d in dates:
                    try:
                        event_date = pd.Timestamp(d).tz_localize(None)
                        # Align to closest trading day
                        window_close = close[close.index <= event_date + pd.Timedelta(days=7)]
                        if len(window_close) < 10:
                            continue
                        idx = window_close.index.get_loc(window_close.index[-1])
                        if idx < 6 or idx > len(close) - 6:
                            continue

                        pre_5d = (float(close.iloc[idx]) - float(close.iloc[idx - 5])) / float(close.iloc[idx - 5]) * 100
                        post_5d = (float(close.iloc[idx + 5]) - float(close.iloc[idx])) / float(close.iloc[idx]) * 100

                        events.append({
                            "date":     str(event_date.date()),
                            "pre_5d":   round(pre_5d, 2),
                            "post_5d":  round(post_5d, 2),
                        })
                    except Exception:
                        continue
            except Exception:
                pass

        if not events:
            return {"events": [], "pre_avg": None, "post_avg": None, "note": "No event data"}

        pre_avgs = [e["pre_5d"] for e in events]
        post_avgs = [e["post_5d"] for e in events]

        note = (
            f"On average, {ticker} moves {np.mean(pre_avgs):.1f}% in the 5 days "
            f"BEFORE earnings and {np.mean(post_avgs):.1f}% in the 5 days AFTER earnings "
            f"(based on {len(events)} events)."
        )

        return {
            "events":     events,
            "pre_avg":    round(float(np.mean(pre_avgs)), 2),
            "post_avg":   round(float(np.mean(post_avgs)), 2),
            "pre_std":    round(float(np.std(pre_avgs)), 2),
            "post_std":   round(float(np.std(post_avgs)), 2),
            "n_events":   len(events),
            "note":       note,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # BEST/WORST PERIODS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=3600)
    def best_worst_periods(ticker: str, period_length: int = 20,
                            top_n: int = 10) -> Dict:
        """Identify the best and worst N-day periods historically.

        Args:
            ticker: Ticker symbol.
            period_length: Rolling window size in trading days.
            top_n: Number of periods to return in each list.

        Returns:
            Dict with 'best' and 'worst' DataFrames.
        """
        try:
            df = yf.download(ticker, period="max", interval="1d",
                              auto_adjust=True, progress=False)
        except Exception:
            return {}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns:
            return {}

        df["rolling_return"] = df["Close"].pct_change(period_length) * 100

        best = (
            df["rolling_return"]
            .dropna()
            .nlargest(top_n)
            .reset_index()
        )
        best.columns = ["Date", f"{period_length}d Return %"]

        worst = (
            df["rolling_return"]
            .dropna()
            .nsmallest(top_n)
            .reset_index()
        )
        worst.columns = ["Date", f"{period_length}d Return %"]

        return {"best": best, "worst": worst, "period_length": period_length}
