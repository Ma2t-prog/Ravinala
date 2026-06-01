"""
charting.py — Professional multi-panel chart engine powered by Plotly.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .core import DataFetcher, DARK_THEME
from .technical import TechnicalIndicators


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
_COLORS = DARK_THEME
_IND_COLORS = ["#22c55e", "#f59e0b", "#3b82f6", "#a855f7", "#ec4899", "#14b8a6"]


def _dark_layout(**kwargs) -> Dict:
    base = dict(
        paper_bgcolor=_COLORS["bg"],
        plot_bgcolor=_COLORS["panel"],
        font=dict(color=_COLORS["text"], size=12),
        xaxis=dict(
            gridcolor=_COLORS["border"],
            zerolinecolor=_COLORS["border"],
            showgrid=True,
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            gridcolor=_COLORS["border"],
            zerolinecolor=_COLORS["border"],
            showgrid=True,
        ),
        margin=dict(l=60, r=30, t=50, b=40),
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=_COLORS["border"],
            font=dict(size=11),
        ),
    )
    base.update(kwargs)
    return base


class ChartEngine:
    """Professional Plotly chart engine for the Financial Analysis Suite."""

    # ─────────────────────────────────────────────────────────────────────────
    # CHART TYPE CONVERTERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
        """Convert OHLCV to Heikin-Ashi candles."""
        ha = df.copy()
        ha["Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
        ha["Open"] = (df["Open"].shift(1) + df["Close"].shift(1)) / 2
        ha["Open"].iloc[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
        ha["High"] = pd.concat([df["High"], ha["Open"], ha["Close"]], axis=1).max(axis=1)
        ha["Low"] = pd.concat([df["Low"], ha["Open"], ha["Close"]], axis=1).min(axis=1)
        return ha

    @staticmethod
    def renko(df: pd.DataFrame, brick_size: Optional[float] = None) -> pd.DataFrame:
        """Convert OHLCV to Renko bricks.

        Args:
            brick_size: If None, uses ATR(14) as brick size.

        Returns:
            DataFrame with Renko OHLC bricks.
        """
        if brick_size is None:
            brick_size = float(TechnicalIndicators.atr(df, 14).dropna().mean())
        if brick_size <= 0:
            brick_size = float(df["Close"].mean()) * 0.01

        closes = df["Close"].values
        bricks = []
        current = round(closes[0] / brick_size) * brick_size

        for c in closes[1:]:
            while c >= current + brick_size:
                bricks.append({
                    "Open": current,
                    "High": current + brick_size,
                    "Low": current,
                    "Close": current + brick_size,
                    "direction": 1,
                })
                current += brick_size
            while c <= current - brick_size:
                bricks.append({
                    "Open": current,
                    "High": current,
                    "Low": current - brick_size,
                    "Close": current - brick_size,
                    "direction": -1,
                })
                current -= brick_size

        return pd.DataFrame(bricks) if bricks else pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN CHART BUILDER
    # ─────────────────────────────────────────────────────────────────────────

    def render_pro_chart(self, df: pd.DataFrame, symbol: str,
                          config: Optional[Dict] = None) -> go.Figure:
        """Build a professional multi-panel chart.

        Args:
            df: OHLCV DataFrame.
            symbol: Ticker symbol (for title).
            config: Chart configuration dict (see module docstring).

        Returns:
            Plotly Figure.
        """
        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                **_dark_layout(title=f"{symbol} — No data available"),
                height=500,
            )
            return fig

        if config is None:
            config = {}

        chart_type = config.get("chart_type", "candlestick")
        overlays = config.get("overlays", [])
        sub_panels = config.get("sub_panels", [{"type": "volume", "height_ratio": 0.15}])
        levels_cfg = config.get("levels", [])
        log_scale = config.get("log_scale", False)
        theme = config.get("theme", "dark")

        # Build subplot rows
        row_heights = [0.55]  # main price panel
        for sp in sub_panels:
            row_heights.append(sp.get("height_ratio", 0.12))

        n_rows = len(row_heights)
        total = sum(row_heights)
        row_heights = [h / total for h in row_heights]

        fig = make_subplots(
            rows=n_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.025,
            row_heights=row_heights,
        )

        # ── OHLCV data
        if chart_type == "heikin_ashi":
            plot_df = self.heikin_ashi(df)
        else:
            plot_df = df

        # ── Price trace ────────────────────────────────────────────────────
        if chart_type in ("candlestick", "heikin_ashi"):
            fig.add_trace(go.Candlestick(
                x=plot_df.index,
                open=plot_df["Open"],
                high=plot_df["High"],
                low=plot_df["Low"],
                close=plot_df["Close"],
                name=symbol,
                increasing_line_color=_COLORS["green"],
                decreasing_line_color=_COLORS["red"],
                increasing_fillcolor=_COLORS["green"],
                decreasing_fillcolor=_COLORS["red"],
                line=dict(width=1),
            ), row=1, col=1)
        elif chart_type == "ohlc":
            fig.add_trace(go.Ohlc(
                x=plot_df.index,
                open=plot_df["Open"],
                high=plot_df["High"],
                low=plot_df["Low"],
                close=plot_df["Close"],
                name=symbol,
                increasing_line_color=_COLORS["green"],
                decreasing_line_color=_COLORS["red"],
            ), row=1, col=1)
        elif chart_type == "area":
            fig.add_trace(go.Scatter(
                x=plot_df.index,
                y=plot_df["Close"],
                name=symbol,
                mode="lines",
                fill="tozeroy",
                fillcolor="rgba(59,130,246,0.12)",
                line=dict(color=_COLORS["blue"], width=2),
            ), row=1, col=1)
        else:  # line
            fig.add_trace(go.Scatter(
                x=plot_df.index,
                y=plot_df["Close"],
                name=symbol,
                mode="lines",
                line=dict(color=_COLORS["blue"], width=2),
            ), row=1, col=1)

        # ── OVERLAYS ───────────────────────────────────────────────────────
        color_idx = 0
        for ov in overlays:
            ov_type = ov.get("type", "")
            color = ov.get("color", _IND_COLORS[color_idx % len(_IND_COLORS)])
            color_idx += 1

            if ov_type == "sma":
                period = ov.get("period", 20)
                s = TechnicalIndicators.sma(df["Close"], period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=s, name=f"SMA {period}",
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"SMA{period}: %{{y:.2f}}<extra></extra>",
                ), row=1, col=1)

            elif ov_type == "ema":
                period = ov.get("period", 20)
                s = TechnicalIndicators.ema(df["Close"], period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=s, name=f"EMA {period}",
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"EMA{period}: %{{y:.2f}}<extra></extra>",
                ), row=1, col=1)

            elif ov_type == "dema":
                period = ov.get("period", 20)
                s = TechnicalIndicators.dema(df["Close"], period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=s, name=f"DEMA {period}",
                    line=dict(color=color, width=1.5),
                ), row=1, col=1)

            elif ov_type == "hull":
                period = ov.get("period", 20)
                s = TechnicalIndicators.hull_ma(df["Close"], period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=s, name=f"Hull {period}",
                    line=dict(color=color, width=1.5),
                ), row=1, col=1)

            elif ov_type == "bollinger":
                period = ov.get("period", 20)
                std_mult = ov.get("std", 2.0)
                bb = TechnicalIndicators.bollinger_bands(df["Close"], period, std_mult)
                for band, dash in [("bb_upper", "dash"), ("bb_mid", "solid"), ("bb_lower", "dash")]:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=bb[band],
                        name=band.replace("_", " ").upper(),
                        line=dict(color=color, width=1, dash=dash),
                        hovertemplate="%{y:.2f}<extra></extra>",
                    ), row=1, col=1)

            elif ov_type == "keltner":
                period = ov.get("period", 20)
                kc = TechnicalIndicators.keltner_channels(df, period)
                for band, dash in [("kc_upper", "dot"), ("kc_mid", "solid"), ("kc_lower", "dot")]:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=kc[band], name=band,
                        line=dict(color=color, width=1, dash=dash),
                    ), row=1, col=1)

            elif ov_type == "ichimoku":
                ich = TechnicalIndicators.ichimoku(df)
                palette = ["#06b6d4", "#f97316", "#22c55e", "#ef4444", "#94a3b8"]
                for col_name, col_color in zip(
                    ["tenkan", "kijun", "senkou_a", "senkou_b", "chikou"], palette
                ):
                    fig.add_trace(go.Scatter(
                        x=df.index, y=ich[col_name],
                        name=col_name.replace("_", " ").capitalize(),
                        line=dict(color=col_color, width=1),
                        hovertemplate="%{y:.2f}<extra></extra>",
                    ), row=1, col=1)

            elif ov_type == "supertrend":
                period = ov.get("period", 10)
                mult = ov.get("multiplier", 3.0)
                st_df = TechnicalIndicators.supertrend(df, period, mult)
                bull_mask = st_df["direction"] == -1
                bear_mask = st_df["direction"] == 1
                for mask, c in [(bull_mask, _COLORS["green"]), (bear_mask, _COLORS["red"])]:
                    series = st_df["supertrend"].copy()
                    series[~mask] = np.nan
                    fig.add_trace(go.Scatter(
                        x=df.index, y=series,
                        name="SuperTrend",
                        line=dict(color=c, width=2),
                        connectgaps=False,
                    ), row=1, col=1)

            elif ov_type == "vwap":
                vwap = TechnicalIndicators.vwap(df)
                fig.add_trace(go.Scatter(
                    x=df.index, y=vwap, name="VWAP",
                    line=dict(color="#a855f7", width=1.5, dash="dot"),
                ), row=1, col=1)

            elif ov_type == "parabolic_sar":
                psar = TechnicalIndicators.parabolic_sar(df)
                fig.add_trace(go.Scatter(
                    x=df.index, y=psar, name="PSAR",
                    mode="markers",
                    marker=dict(size=3, color=color),
                ), row=1, col=1)

        # ── SUPPORT/RESISTANCE LEVELS ──────────────────────────────────────
        for lv_cfg in levels_cfg:
            lv_type = lv_cfg.get("type", "")
            if lv_type == "support_resistance" and lv_cfg.get("auto", True):
                from .technical import TechnicalIndicators as TI
                levels = TI.auto_support_resistance(df)
                for lv in levels:
                    color = "#22c55e" if lv["type"] == "support" else "#ef4444"
                    fig.add_hline(
                        y=lv["price"], row=1, col=1,
                        line=dict(color=color, width=1, dash="dot"),
                        annotation_text=f"{lv['type'].title()} {lv['price']:.2f} ({lv['touches']}x)",
                        annotation_font=dict(size=10, color=color),
                    )
            elif lv_type == "fibonacci":
                fib = TechnicalIndicators.fibonacci_retracements(df)
                for label, price in fib.items():
                    fig.add_hline(
                        y=price, row=1, col=1,
                        line=dict(color="#f59e0b", width=1, dash="dot"),
                        annotation_text=f"Fib {label}: {price:.2f}",
                        annotation_font=dict(size=9, color="#f59e0b"),
                    )
            elif lv_type == "pivot_points":
                method = lv_cfg.get("method", "standard")
                pp_df = TechnicalIndicators.pivot_points(df, method)
                colors_map = {"pp": "#94a3b8", "r1": "#ef4444", "r2": "#f97316",
                              "r3": "#f59e0b", "s1": "#22c55e", "s2": "#16a34a", "s3": "#15803d"}
                for col_name, pp_color in colors_map.items():
                    if col_name in pp_df.columns:
                        val = float(pp_df[col_name].iloc[-1])
                        fig.add_hline(
                            y=val, row=1, col=1,
                            line=dict(color=pp_color, width=1, dash="dashdot"),
                            annotation_text=f"{col_name.upper()}: {val:.2f}",
                            annotation_font=dict(size=9, color=pp_color),
                        )

        # ── SUB-PANELS ─────────────────────────────────────────────────────
        for row_i, sp in enumerate(sub_panels, start=2):
            sp_type = sp.get("type", "volume")

            if sp_type == "volume":
                colors = [
                    _COLORS["green"] if float(df["Close"].iloc[i]) >= float(df["Open"].iloc[i])
                    else _COLORS["red"]
                    for i in range(len(df))
                ]
                fig.add_trace(go.Bar(
                    x=df.index, y=df["Volume"],
                    name="Volume",
                    marker_color=colors,
                    opacity=0.7,
                ), row=row_i, col=1)

            elif sp_type == "rsi":
                period = sp.get("period", 14)
                rsi = TechnicalIndicators.rsi(df["Close"], period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=rsi, name=f"RSI({period})",
                    line=dict(color="#3b82f6", width=1.5),
                    hovertemplate="RSI: %{y:.1f}<extra></extra>",
                ), row=row_i, col=1)
                fig.add_hline(y=70, row=row_i, col=1,
                              line=dict(color=_COLORS["red"], width=1, dash="dot"),
                              annotation_text="70")
                fig.add_hline(y=30, row=row_i, col=1,
                              line=dict(color=_COLORS["green"], width=1, dash="dot"),
                              annotation_text="30")
                fig.add_hline(y=50, row=row_i, col=1,
                              line=dict(color=_COLORS["border"], width=0.5, dash="dot"))
                fig.update_yaxes(range=[0, 100], row=row_i, col=1)

            elif sp_type == "macd":
                fast = sp.get("fast", 12)
                slow = sp.get("slow", 26)
                signal = sp.get("signal", 9)
                macd_df = TechnicalIndicators.macd(df["Close"], fast, slow, signal)
                fig.add_trace(go.Scatter(
                    x=df.index, y=macd_df["macd"], name="MACD",
                    line=dict(color=_COLORS["blue"], width=1.5),
                ), row=row_i, col=1)
                fig.add_trace(go.Scatter(
                    x=df.index, y=macd_df["macd_signal"], name="Signal",
                    line=dict(color=_COLORS["yellow"], width=1.5),
                ), row=row_i, col=1)
                hist_colors = [
                    _COLORS["green"] if float(v) >= 0 else _COLORS["red"]
                    for v in macd_df["macd_hist"].fillna(0)
                ]
                fig.add_trace(go.Bar(
                    x=df.index, y=macd_df["macd_hist"], name="Histogram",
                    marker_color=hist_colors, opacity=0.7,
                ), row=row_i, col=1)

            elif sp_type == "stochastic":
                k_period = sp.get("k", 14)
                d_period = sp.get("d", 3)
                stoch = TechnicalIndicators.stochastic(df, k_period, d_period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=stoch["stoch_k"], name="%K",
                    line=dict(color=_COLORS["blue"], width=1.5),
                ), row=row_i, col=1)
                fig.add_trace(go.Scatter(
                    x=df.index, y=stoch["stoch_d"], name="%D",
                    line=dict(color=_COLORS["yellow"], width=1.5),
                ), row=row_i, col=1)
                fig.add_hline(y=80, row=row_i, col=1,
                              line=dict(color=_COLORS["red"], width=1, dash="dot"))
                fig.add_hline(y=20, row=row_i, col=1,
                              line=dict(color=_COLORS["green"], width=1, dash="dot"))
                fig.update_yaxes(range=[0, 100], row=row_i, col=1)

            elif sp_type == "obv":
                obv = TechnicalIndicators.obv(df)
                fig.add_trace(go.Scatter(
                    x=df.index, y=obv, name="OBV",
                    line=dict(color="#a855f7", width=1.5),
                ), row=row_i, col=1)

            elif sp_type == "mfi":
                mfi = TechnicalIndicators.mfi(df)
                fig.add_trace(go.Scatter(
                    x=df.index, y=mfi, name="MFI",
                    line=dict(color="#14b8a6", width=1.5),
                ), row=row_i, col=1)
                fig.add_hline(y=80, row=row_i, col=1,
                              line=dict(color=_COLORS["red"], width=1, dash="dot"))
                fig.add_hline(y=20, row=row_i, col=1,
                              line=dict(color=_COLORS["green"], width=1, dash="dot"))

            elif sp_type == "atr":
                period = sp.get("period", 14)
                atr = TechnicalIndicators.atr(df, period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=atr, name=f"ATR({period})",
                    line=dict(color="#f59e0b", width=1.5),
                ), row=row_i, col=1)

            elif sp_type == "cci":
                period = sp.get("period", 20)
                cci = TechnicalIndicators.cci(df, period)
                fig.add_trace(go.Scatter(
                    x=df.index, y=cci, name=f"CCI({period})",
                    line=dict(color="#ec4899", width=1.5),
                ), row=row_i, col=1)
                fig.add_hline(y=100, row=row_i, col=1,
                              line=dict(color=_COLORS["red"], width=1, dash="dot"))
                fig.add_hline(y=-100, row=row_i, col=1,
                              line=dict(color=_COLORS["green"], width=1, dash="dot"))

        # ── LAYOUT ─────────────────────────────────────────────────────────
        current_price = float(df["Close"].iloc[-1])
        price_change = float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2]) if len(df) > 1 else 0
        pct_change = price_change / float(df["Close"].iloc[-2]) * 100 if len(df) > 1 and float(df["Close"].iloc[-2]) != 0 else 0
        sign = "+" if pct_change >= 0 else ""
        color = "green" if pct_change >= 0 else "red"

        fig.update_layout(
            **_dark_layout(
                title=dict(
                    text=f"<b>{symbol}</b>  ${current_price:.2f}  "
                         f"<span style='color:{'#22c55e' if pct_change >= 0 else '#ef4444'}'>"
                         f"{sign}{pct_change:.2f}%</span>",
                    font=dict(size=16),
                )
            ),
            height=600 + (len(sub_panels) - 1) * 120,
            showlegend=True,
        )

        # Log scale on price axis
        if log_scale:
            fig.update_yaxes(type="log", row=1, col=1)

        # Shared x-axis label only on bottom
        fig.update_xaxes(rangeslider_visible=False)

        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # MULTI-TIMEFRAME VIEW
    # ─────────────────────────────────────────────────────────────────────────

    def render_multi_timeframe(self, symbol: str,
                                timeframes: Optional[List[str]] = None,
                                indicators: Optional[List[str]] = None) -> go.Figure:
        """Side-by-side charts for the same asset across multiple timeframes.

        Args:
            symbol: Ticker symbol.
            timeframes: List of timeframes, e.g. ['1h', '4h', '1d', '1w'].
            indicators: Indicator overlays to show on each chart.

        Returns:
            Plotly Figure with a 2×2 grid (or 1×N for fewer TFs).
        """
        if timeframes is None:
            timeframes = ["1h", "4h", "1d", "1w"]
        if indicators is None:
            indicators = ["ema_20", "ema_50"]

        n = len(timeframes)
        cols = min(2, n)
        rows = (n + 1) // 2

        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[f"{symbol} — {tf}" for tf in timeframes],
            shared_yaxes=False,
            vertical_spacing=0.10,
            horizontal_spacing=0.05,
        )

        for idx, tf in enumerate(timeframes):
            row = idx // cols + 1
            col = idx % cols + 1
            df = DataFetcher.ohlcv(symbol, tf)
            if df.empty:
                continue

            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["Open"], high=df["High"],
                low=df["Low"],  close=df["Close"],
                name=tf,
                increasing_line_color=_COLORS["green"],
                decreasing_line_color=_COLORS["red"],
                showlegend=False,
            ), row=row, col=col)

            for ind in indicators:
                parts = ind.split("_")
                ind_type = parts[0]
                period = int(parts[1]) if len(parts) > 1 else 20
                color = _IND_COLORS[period % len(_IND_COLORS)]

                if ind_type == "ema":
                    s = TechnicalIndicators.ema(df["Close"], period)
                    fig.add_trace(go.Scatter(
                        x=df.index, y=s,
                        name=f"EMA{period}",
                        line=dict(color=color, width=1.2),
                        showlegend=False,
                    ), row=row, col=col)
                elif ind_type == "sma":
                    s = TechnicalIndicators.sma(df["Close"], period)
                    fig.add_trace(go.Scatter(
                        x=df.index, y=s,
                        name=f"SMA{period}",
                        line=dict(color=color, width=1.2),
                        showlegend=False,
                    ), row=row, col=col)

        fig.update_layout(
            **_dark_layout(title=f"<b>{symbol}</b> — Multi-Timeframe Analysis"),
            height=700,
        )
        fig.update_xaxes(rangeslider_visible=False)
        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # COMPARISON CHART
    # ─────────────────────────────────────────────────────────────────────────

    def render_comparison_chart(self, symbols: List[str],
                                 timeframe: str = "1d",
                                 period: str = "1y",
                                 normalize: bool = True) -> go.Figure:
        """Compare N assets on the same chart.

        Args:
            symbols: List of ticker symbols.
            timeframe: Candle interval.
            period: Historical period (approximate, uses TIMEFRAME_MAP).
            normalize: If True, base 100 at start of period.

        Returns:
            Plotly Figure.
        """
        fig = go.Figure()
        colors = _IND_COLORS + ["#f43f5e", "#0ea5e9", "#84cc16"]

        for i, sym in enumerate(symbols):
            df = DataFetcher.ohlcv(sym, timeframe)
            if df.empty:
                continue

            series = df["Close"].copy()
            if normalize:
                base = float(series.iloc[0])
                if base != 0:
                    series = series / base * 100

            fig.add_trace(go.Scatter(
                x=df.index,
                y=series,
                name=sym,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate=f"{sym}: %{{y:.2f}}{'%' if normalize else ''}<extra></extra>",
            ))

        ylabel = "Normalized (base 100)" if normalize else "Price"
        fig.update_layout(
            **_dark_layout(title="<b>Asset Comparison</b>"),
            yaxis_title=ylabel,
            height=500,
        )
        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # MINI-CHART (for watchlist)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def mini_chart(df: pd.DataFrame, color: str = "#22c55e",
                    height: int = 60) -> go.Figure:
        """Compact sparkline chart for watchlist display."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=f"{color}15",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0),
            height=height,
            showlegend=False,
        )
        return fig
