"""
volume_profile.py — Volume Profile (POC, Value Area, TPO) analysis.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .core import DARK_THEME

_C = DARK_THEME


class VolumeProfile:
    """Volume Profile and Time Price Opportunity analysis."""

    # ─────────────────────────────────────────────────────────────────────────
    # VOLUME PROFILE COMPUTATION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_profile(df: pd.DataFrame,
                         n_bins: int = 50,
                         value_area_pct: float = 0.70) -> Dict:
        """Compute volume profile for the given OHLCV data.

        Args:
            df: OHLCV DataFrame.
            n_bins: Number of price buckets.
            value_area_pct: Fraction of total volume that defines the Value Area.

        Returns:
            Dict with price_levels, volume_at_price, poc, value_area_high,
            value_area_low, hv_nodes, lv_nodes.
        """
        if df.empty or "Volume" not in df.columns:
            return {}

        price_min = float(df["Low"].min())
        price_max = float(df["High"].max())
        if price_min >= price_max:
            return {}

        bins = np.linspace(price_min, price_max, n_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        volume_at_price = np.zeros(n_bins)

        for _, row in df.iterrows():
            o, h, l, c, v = (
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(row["Volume"]),
            )
            # Distribute volume evenly across the price range of the candle
            low_bin = np.searchsorted(bins, l, side="left")
            high_bin = np.searchsorted(bins, h, side="right")
            low_bin = max(0, low_bin - 1)
            high_bin = min(n_bins, high_bin)
            n_buckets = high_bin - low_bin
            if n_buckets > 0:
                volume_at_price[low_bin:high_bin] += v / n_buckets

        # POC — bin with max volume
        poc_idx = int(np.argmax(volume_at_price))
        poc = float(bin_centers[poc_idx])

        # Value Area — 70% of total volume centered on POC
        total_vol = volume_at_price.sum()
        target_vol = total_vol * value_area_pct

        va_low_idx = poc_idx
        va_high_idx = poc_idx
        accumulated = volume_at_price[poc_idx]

        while accumulated < target_vol:
            can_go_lower = va_low_idx > 0
            can_go_higher = va_high_idx < n_bins - 1

            if not can_go_lower and not can_go_higher:
                break

            add_lower = volume_at_price[va_low_idx - 1] if can_go_lower else 0
            add_higher = volume_at_price[va_high_idx + 1] if can_go_higher else 0

            if add_higher >= add_lower:
                if can_go_higher:
                    va_high_idx += 1
                    accumulated += add_higher
            else:
                if can_go_lower:
                    va_low_idx -= 1
                    accumulated += add_lower

        value_area_high = float(bin_centers[va_high_idx])
        value_area_low = float(bin_centers[va_low_idx])

        # High Volume Nodes (HVN) — bins with volume > 1.5x mean
        mean_vol = float(volume_at_price.mean())
        hv_nodes = [float(bin_centers[i]) for i in range(n_bins)
                    if volume_at_price[i] > 1.5 * mean_vol]

        # Low Volume Nodes (LVN) — bins with volume < 0.4x mean
        lv_nodes = [float(bin_centers[i]) for i in range(n_bins)
                    if 0 < volume_at_price[i] < 0.4 * mean_vol]

        return {
            "price_levels":     bin_centers,
            "volume_at_price":  volume_at_price,
            "poc":              poc,
            "value_area_high":  value_area_high,
            "value_area_low":   value_area_low,
            "hv_nodes":         hv_nodes,
            "lv_nodes":         lv_nodes,
            "price_min":        price_min,
            "price_max":        price_max,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # CHART WITH VOLUME PROFILE OVERLAY
    # ─────────────────────────────────────────────────────────────────────────

    def render_with_profile(self, df: pd.DataFrame, symbol: str,
                             n_bins: int = 40) -> go.Figure:
        """Render a candlestick chart with a horizontal volume profile on the right.

        Args:
            df: OHLCV DataFrame.
            symbol: Symbol for title.
            n_bins: Volume profile bucket count.

        Returns:
            Plotly Figure.
        """
        if df.empty:
            return go.Figure()

        profile = self.compute_profile(df, n_bins)
        if not profile:
            return go.Figure()

        # 2-column layout: price chart | volume profile
        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.80, 0.20],
            shared_yaxes=True,
            horizontal_spacing=0.005,
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"],   close=df["Close"],
            name=symbol,
            increasing_line_color=_C["green"],
            decreasing_line_color=_C["red"],
            showlegend=False,
        ), row=1, col=1)

        # Volume profile histogram (horizontal)
        vap = profile["volume_at_price"]
        levels = profile["price_levels"]
        max_vol = float(vap.max()) if vap.max() > 0 else 1

        bar_colors = []
        for i, price in enumerate(levels):
            if abs(price - profile["poc"]) < (levels[1] - levels[0]) * 0.6:
                bar_colors.append("#f59e0b")  # POC = orange
            elif profile["value_area_low"] <= price <= profile["value_area_high"]:
                bar_colors.append("#3b82f6")  # Value Area = blue
            else:
                bar_colors.append("#475569")  # Outside VA = grey

        fig.add_trace(go.Bar(
            x=vap / max_vol,
            y=levels,
            orientation="h",
            name="Volume Profile",
            marker_color=bar_colors,
            opacity=0.85,
            hovertemplate="Price: %{y:.2f}<br>Vol: %{x:.0%} of max<extra></extra>",
        ), row=1, col=2)

        # POC line on price chart
        fig.add_hline(
            y=profile["poc"], row=1, col=1,
            line=dict(color="#f59e0b", width=1.5, dash="dash"),
            annotation_text=f"POC: {profile['poc']:.2f}",
            annotation_font=dict(size=10, color="#f59e0b"),
        )

        # Value area lines
        fig.add_hline(
            y=profile["value_area_high"], row=1, col=1,
            line=dict(color="#3b82f6", width=1, dash="dot"),
            annotation_text=f"VAH: {profile['value_area_high']:.2f}",
            annotation_font=dict(size=9, color="#3b82f6"),
        )
        fig.add_hline(
            y=profile["value_area_low"], row=1, col=1,
            line=dict(color="#3b82f6", width=1, dash="dot"),
            annotation_text=f"VAL: {profile['value_area_low']:.2f}",
            annotation_font=dict(size=9, color="#3b82f6"),
        )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{symbol}</b> — Volume Profile",
            height=600,
            showlegend=False,
            margin=dict(l=60, r=20, t=50, b=40),
            xaxis=dict(
                gridcolor=_C["border"],
                rangeslider=dict(visible=False),
            ),
            yaxis=dict(gridcolor=_C["border"]),
            xaxis2=dict(visible=False),
        )

        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # TPO (TIME PRICE OPPORTUNITY)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_tpo(df: pd.DataFrame,
                     session_minutes: int = 30) -> pd.DataFrame:
        """Compute Time Price Opportunity (Market Profile).

        Divides each session into periods and marks price levels touched.

        Args:
            df: Intraday OHLCV DataFrame.
            session_minutes: Period size in minutes.

        Returns:
            DataFrame where rows = price levels, columns = period labels (A, B, C…).
        """
        if df.empty:
            return pd.DataFrame()

        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        price_min = float(df["Low"].min())
        price_max = float(df["High"].max())
        tick = (price_max - price_min) / 50

        price_levels = np.arange(price_min, price_max + tick, tick)
        n_prices = len(price_levels)

        # Resample to session_minutes
        try:
            resampled = df[["High", "Low"]].resample(f"{session_minutes}min").agg(
                {"High": "max", "Low": "min"}
            ).dropna()
        except Exception:
            return pd.DataFrame()

        tpo_data: Dict[str, List] = {}
        for i, (ts, row) in enumerate(resampled.iterrows()):
            letter = alphabet[i % len(alphabet)]
            h, l = float(row["High"]), float(row["Low"])
            touched = [
                letter if l <= p <= h else ""
                for p in price_levels
            ]
            tpo_data[str(ts)] = touched

        result = pd.DataFrame(tpo_data, index=price_levels)
        result.index.name = "Price"
        return result
