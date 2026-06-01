"""
intermarket.py — Cross-asset analysis, regime detection, market breadth indicators.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

from .core import DataFetcher, DARK_THEME

_C = DARK_THEME


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-ASSET PAIRS
# ─────────────────────────────────────────────────────────────────────────────

CROSS_ASSET_PAIRS: Dict[str, Tuple[str, str, str]] = {
    "Stocks vs Bonds":      ("SPY",  "TLT",  "Risk-on / Risk-off"),
    "USD vs Gold":          ("UUP",  "GLD",  "Dollar strength vs haven"),
    "Oil vs Inflation":     ("USO",  "TIP",  "Commodity-driven inflation"),
    "S&P vs VIX":           ("^GSPC","^VIX", "Equity vol relationship"),
    "10Y Yield vs Growth":  ("^TNX", "QQQ",  "Rate sensitivity"),
    "DXY vs EM":            ("UUP",  "EEM",  "Dollar vs Emerging Markets"),
    "Copper vs S&P":        ("CPER", "SPY",  "Dr. Copper macro signal"),
    "HY Spreads proxy":     ("HYG",  "LQD",  "Credit risk appetite"),
}


class IntermarketAnalyzer:
    """Cross-asset correlation analysis and market regime detection."""

    # ─────────────────────────────────────────────────────────────────────────
    # ROLLING CORRELATION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def rolling_correlation(sym1: str, sym2: str,
                             window: int = 60,
                             period: str = "2y") -> pd.Series:
        """Compute rolling Pearson correlation between two assets' returns.

        Args:
            sym1: First symbol.
            sym2: Second symbol.
            window: Rolling window in trading days.
            period: History period.

        Returns:
            pd.Series of rolling correlation.
        """
        try:
            raw = yf.download([sym1, sym2], period=period, interval="1d",
                               auto_adjust=True, progress=False)["Close"]
        except Exception:
            return pd.Series(dtype=float)

        if raw.empty or raw.shape[1] < 2:
            return pd.Series(dtype=float)

        returns = raw.pct_change().dropna()
        if returns.shape[1] < 2:
            return pd.Series(dtype=float)

        cols = returns.columns.tolist()
        return returns[cols[0]].rolling(window).corr(returns[cols[1]])

    # ─────────────────────────────────────────────────────────────────────────
    # CROSS-ASSET DASHBOARD
    # ─────────────────────────────────────────────────────────────────────────

    def cross_asset_dashboard(self, window: int = 60) -> Dict:
        """Compute current cross-asset correlations and anomaly flags.

        Returns:
            Dict mapping relationship label → dict with corr, zscore, flag.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}

        def _compute(label: str, sym1: str, sym2: str, desc: str) -> Tuple[str, Dict]:
            corr_series = IntermarketAnalyzer.rolling_correlation(sym1, sym2, window)
            if corr_series.empty:
                return label, {"label": label, "description": desc, "error": True}

            current = float(corr_series.iloc[-1])
            historical = corr_series.dropna()
            mean_corr = float(historical.mean())
            std_corr = float(historical.std())
            zscore = (current - mean_corr) / std_corr if std_corr > 0 else 0
            pct_rank = float((historical <= current).mean() * 100)

            flag = None
            if abs(zscore) > 2:
                direction = "very high" if zscore > 0 else "very low"
                flag = f"[WARN] Correlation is {direction} vs history (z={zscore:.1f}). Potential regime shift."

            return label, {
                "label":       label,
                "description": desc,
                "sym1":        sym1,
                "sym2":        sym2,
                "current":     round(current, 3),
                "hist_mean":   round(mean_corr, 3),
                "zscore":      round(zscore, 2),
                "pct_rank":    round(pct_rank, 1),
                "flag":        flag,
                "series":      corr_series,
            }

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {
                ex.submit(_compute, label, sym1, sym2, desc): label
                for label, (sym1, sym2, desc) in CROSS_ASSET_PAIRS.items()
            }
            for f in as_completed(futures):
                label, result = f.result()
                results[label] = result

        return results

    def render_cross_asset_chart(self, label: str,
                                  dashboard_data: Optional[Dict] = None) -> go.Figure:
        """Chart rolling correlation for a given pair."""
        if dashboard_data is None:
            dashboard_data = self.cross_asset_dashboard()

        entry = dashboard_data.get(label)
        if not entry or entry.get("error"):
            return go.Figure()

        series = entry["series"].dropna()
        sym1, sym2 = entry["sym1"], entry["sym2"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series.index,
            y=series.values,
            name=f"Corr ({sym1} / {sym2})",
            line=dict(color=_C["blue"], width=2),
            hovertemplate="Date: %{x}<br>Correlation: %{y:.3f}<extra></extra>",
        ))
        fig.add_hline(y=0, line=dict(color=_C["border"], width=1, dash="dash"))
        fig.add_hline(y=entry["hist_mean"],
                      line=dict(color=_C["yellow"], width=1, dash="dot"),
                      annotation_text=f"Avg: {entry['hist_mean']:.2f}",
                      annotation_font=dict(color=_C["yellow"], size=10))

        # Color background by regime
        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{label}</b> — Rolling 60-day Correlation",
            yaxis=dict(range=[-1, 1], gridcolor=_C["border"]),
            xaxis=dict(gridcolor=_C["border"]),
            height=350,
        )
        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # REGIME DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def regime_detection(ticker: str = "^GSPC",
                          vol_window: int = 21,
                          trend_window: int = 63) -> Dict:
        """Detect current market regime using return + volatility.

        Regimes:
        - Bull Quiet:    trending up, low vol
        - Bull Volatile: trending up, high vol (late cycle)
        - Bear Quiet:    trending down, low vol
        - Bear Volatile: trending down, high vol (crisis)

        Args:
            ticker: Market index (e.g., '^GSPC').
            vol_window: Rolling window for volatility.
            trend_window: Rolling window for trend.

        Returns:
            Dict with regime, description, history, vol, trend.
        """
        try:
            df = yf.download(ticker, period="5y", interval="1d",
                              auto_adjust=True, progress=False)
        except Exception:
            return {}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns:
            return {}

        close = df["Close"]
        returns = close.pct_change()

        # Volatility: annualized rolling std
        vol = returns.rolling(vol_window).std() * np.sqrt(252)
        # Trend: returns over trend_window
        trend = close.pct_change(trend_window)

        vol_now = float(vol.iloc[-1])
        trend_now = float(trend.iloc[-1])

        # Thresholds
        vol_median = float(vol.dropna().median())
        high_vol = vol_now > vol_median * 1.25

        if trend_now > 0:
            regime = "Bull Volatile" if high_vol else "Bull Quiet"
        else:
            regime = "Bear Volatile" if high_vol else "Bear Quiet"

        descriptions = {
            "Bull Quiet":    "Steady uptrend with low volatility. Ideal risk-on environment.",
            "Bull Volatile": "Uptrend with elevated volatility. Late-cycle behavior, exercise caution.",
            "Bear Quiet":    "Grinding downtrend. Capital preservation mode.",
            "Bear Volatile": "Crash or crisis mode. High volatility, sharp drawdowns possible.",
        }

        regime_colors = {
            "Bull Quiet":    "#22c55e",
            "Bull Volatile": "#f59e0b",
            "Bear Quiet":    "#94a3b8",
            "Bear Volatile": "#ef4444",
        }

        # Historical regime classification
        regime_history = pd.DataFrame({
            "vol":   vol,
            "trend": trend,
        }).dropna()
        regime_history["regime"] = regime_history.apply(
            lambda row: (
                "Bull Volatile" if row["trend"] > 0 and row["vol"] > vol_median * 1.25
                else "Bull Quiet"   if row["trend"] > 0
                else "Bear Volatile" if row["vol"] > vol_median * 1.25
                else "Bear Quiet"
            ),
            axis=1,
        )

        return {
            "regime":      regime,
            "description": descriptions[regime],
            "color":       regime_colors[regime],
            "vol_current": round(vol_now * 100, 1),
            "vol_median":  round(float(vol_median) * 100, 1),
            "trend_3m":    round(float(trend_now) * 100, 1),
            "history":     regime_history,
        }

    def render_regime_chart(self, ticker: str = "^GSPC") -> go.Figure:
        """Visualize market regime history with color-coded background."""
        regime_data = self.regime_detection(ticker)
        if not regime_data or "history" not in regime_data:
            return go.Figure()

        hist = regime_data["history"]
        try:
            df = yf.download(ticker, period="5y", interval="1d",
                              auto_adjust=True, progress=False)["Close"]
        except Exception:
            return go.Figure()

        if isinstance(df, pd.DataFrame):
            df = df.iloc[:, 0]

        price = df.reindex(hist.index).dropna()

        color_map = {
            "Bull Quiet":    "rgba(34,197,94,0.15)",
            "Bull Volatile": "rgba(245,158,11,0.15)",
            "Bear Quiet":    "rgba(148,163,184,0.15)",
            "Bear Volatile": "rgba(239,68,68,0.20)",
        }

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=price.index, y=price.values, name=ticker,
            line=dict(color=_C["blue"], width=2),
            hovertemplate="%{x}<br>Price: %{y:.2f}<extra></extra>",
        ))

        # Add shaded regions per regime
        prev_regime = None
        start_date = None
        for date, row in hist.iterrows():
            r = row["regime"]
            if r != prev_regime:
                if prev_regime is not None and start_date is not None:
                    fig.add_vrect(
                        x0=start_date, x1=date,
                        fillcolor=color_map.get(prev_regime, "rgba(0,0,0,0.05)"),
                        line_width=0,
                    )
                start_date = date
                prev_regime = r
        if prev_regime and start_date:
            fig.add_vrect(
                x0=start_date, x1=hist.index[-1],
                fillcolor=color_map.get(prev_regime, "rgba(0,0,0,0.05)"),
                line_width=0,
            )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{ticker}</b> — Market Regime Detection",
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            height=450,
        )
        return fig


# ─────────────────────────────────────────────────────────────────────────────
# MARKET BREADTH
# ─────────────────────────────────────────────────────────────────────────────

class MarketBreadth:
    """Market breadth indicators: advance/decline, new highs/lows, McClellan."""

    # Representative sample of NYSE/NASDAQ stocks for breadth
    BREADTH_UNIVERSE = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "V", "JNJ",
        "WMT", "PG", "HD", "CVX", "XOM", "BAC", "WFC", "KO", "PEP", "MCD",
        "CSCO", "INTC", "VZ", "T", "ABT", "PFE", "MRK", "ABBV", "LLY", "TMO",
        "UNH", "ACN", "TXN", "QCOM", "HON", "UNP", "CAT", "DE", "MMM", "GE",
        "DIS", "CMCSA", "NFLX", "SBUX", "NKE", "LOW", "TGT", "COST", "AXP", "GS",
    ]

    @staticmethod
    @st.cache_data(ttl=300)
    def compute_breadth(universe: Optional[List[str]] = None) -> Dict:
        """Compute advance/decline and related breadth metrics.

        Args:
            universe: List of tickers. Defaults to BREADTH_UNIVERSE.

        Returns:
            Dict with advances, declines, ad_ratio, new_highs, new_lows, etc.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if universe is None:
            universe = MarketBreadth.BREADTH_UNIVERSE

        def _get_data(sym: str) -> Optional[Dict]:
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="1y", auto_adjust=True)
                if hist is None or len(hist) < 20:
                    return None
                close = hist["Close"]
                price = float(close.iloc[-1])
                prev = float(close.iloc[-2])
                chg = price - prev

                high_52w = float(close.max())
                low_52w  = float(close.min())

                sma200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])

                return {
                    "symbol":   sym,
                    "change":   chg,
                    "is_high_52w": abs(price - high_52w) / high_52w < 0.01,
                    "is_low_52w":  abs(price - low_52w)  / low_52w  < 0.01,
                    "above_sma200": price > sma200,
                }
            except Exception:
                return None

        data = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(_get_data, s) for s in universe]
            for f in as_completed(futures):
                r = f.result()
                if r:
                    data.append(r)

        if not data:
            return {}

        advances = sum(1 for d in data if d["change"] > 0)
        declines = sum(1 for d in data if d["change"] < 0)
        unchanged = len(data) - advances - declines
        new_highs = sum(1 for d in data if d["is_high_52w"])
        new_lows  = sum(1 for d in data if d["is_low_52w"])
        above_200 = sum(1 for d in data if d["above_sma200"])

        ad_ratio = advances / max(declines, 1)

        return {
            "advances":       advances,
            "declines":       declines,
            "unchanged":      unchanged,
            "total":          len(data),
            "ad_ratio":       round(ad_ratio, 2),
            "new_highs":      new_highs,
            "new_lows":       new_lows,
            "pct_above_200":  round(above_200 / len(data) * 100, 1),
            "sentiment":      "Bullish" if ad_ratio > 1.5 else "Bearish" if ad_ratio < 0.67 else "Neutral",
        }
