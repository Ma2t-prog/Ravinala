"""
heatmap.py — Market heatmap (treemap) like Finviz / TradingView.
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


# S&P 500 sector → tickers mapping (representative subset for speed)
SECTOR_TICKERS: Dict[str, List[str]] = {
    "Technology":       ["AAPL", "MSFT", "NVDA", "AVGO", "AMD", "QCOM", "TXN", "INTC", "ADBE", "CRM",
                          "ORCL", "CSCO", "NOW", "PANW", "AMAT", "KLAC", "LRCX", "MU", "ADI", "MRVL"],
    "Healthcare":       ["UNH", "LLY", "JNJ", "MRK", "ABBV", "PFE", "ABT", "TMO", "DHR", "AMGN",
                          "GILD", "CVS", "ISRG", "SYK", "MDT", "REGN", "VRTX", "ZTS", "BSX", "ELV"],
    "Financials":       ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK",
                          "C", "AXP", "CB", "MMC", "PGR", "MCO", "ICE", "AON", "TFC", "USB"],
    "Consumer Disc.":   ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "BKNG", "TJX", "GM",
                          "F", "ORLY", "AZO", "CMG", "ROST", "EBAY", "MAR", "HLT", "DHI", "LEN"],
    "Communication":    ["GOOGL", "META", "NFLX", "CMCSA", "DIS", "T", "VZ", "TMUS", "CHTR", "EA",
                          "TTWO", "ATVI", "OMC", "WBD", "PARA", "IPG", "LYV", "FOXA", "NWS", "NWSA"],
    "Industrials":      ["GE", "HON", "UNP", "CAT", "RTX", "DE", "LMT", "BA", "UPS", "FDX",
                          "ETN", "EMR", "PH", "ROK", "CMI", "GD", "NOC", "CARR", "OTIS", "IR"],
    "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "MDLZ", "CL", "KMB",
                          "GIS", "K", "SJM", "MKC", "HSY", "CHD", "CLX", "MNST", "STZ", "KR"],
    "Energy":           ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "OXY", "PXD",
                          "HAL", "BKR", "KMI", "WMB", "OKE", "DVN", "FANG", "MRO", "APA", "HES"],
    "Utilities":        ["NEE", "SO", "DUK", "AEP", "D", "EXC", "PCG", "XEL", "ED", "ETR",
                          "WEC", "FE", "ES", "PPL", "AEE", "EIX", "CMS", "DTE", "NI", "SRE"],
    "Real Estate":      ["PLD", "AMT", "EQIX", "PSA", "O", "WELL", "VTR", "SPG", "EQR", "AVB",
                          "DLR", "CBRE", "IRM", "ARE", "WY", "PEAK", "MAA", "ESS", "HST", "KIM"],
    "Materials":        ["LIN", "APD", "SHW", "FCX", "NEM", "DOW", "DD", "PPG", "ALB", "ECL",
                          "NUE", "STLD", "PKG", "IP", "VMC", "MLM", "FMC", "CF", "MOS", "CE"],
}


class MarketHeatmap:
    """Interactive market treemap heatmap."""

    @staticmethod
    def _fetch_one(symbol: str) -> Optional[Dict]:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d", auto_adjust=True)
            if hist is None or len(hist) < 2:
                return None
            price = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            change_1d = (price - prev) / prev * 100 if prev != 0 else 0.0

            info = t.info or {}
            mkt_cap = info.get("marketCap") or 1e9
            name = info.get("shortName", symbol)

            return {
                "symbol":    symbol,
                "name":      name,
                "price":     price,
                "change_1d": change_1d,
                "mkt_cap":   mkt_cap,
            }
        except Exception:
            return None

    @st.cache_data(ttl=300)
    def _fetch_sector_data(_self, sector: str,
                            tickers: List[str]) -> pd.DataFrame:
        rows = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(_self._fetch_one, s): s for s in tickers}
            for f in as_completed(futures):
                try:
                    r = f.result()
                    if r:
                        r["sector"] = sector
                        rows.append(r)
                except Exception:
                    pass
        return pd.DataFrame(rows)

    def generate_heatmap(
        self,
        sectors: Optional[Dict[str, List[str]]] = None,
        color_by: str = "change_1d",
        size_by: str = "mkt_cap",
        max_tickers_per_sector: int = 12,
    ) -> go.Figure:
        """Generate an interactive market treemap.

        Args:
            sectors: Dict sector → tickers. Defaults to SECTOR_TICKERS.
            color_by: Metric used for color ('change_1d' → green/red scale).
            size_by: Metric used for rectangle size ('mkt_cap' or 'volume').
            max_tickers_per_sector: Limit per sector for performance.

        Returns:
            Plotly Figure.
        """
        if sectors is None:
            sectors = SECTOR_TICKERS

        all_rows = []
        for sector, tickers in sectors.items():
            subset = tickers[:max_tickers_per_sector]
            df = self._fetch_sector_data(sector, subset)
            if not df.empty:
                all_rows.append(df)

        if not all_rows:
            fig = go.Figure()
            fig.update_layout(
                paper_bgcolor=_C["bg"],
                font=dict(color=_C["text"]),
                title="No market data available",
                height=600,
            )
            return fig

        data = pd.concat(all_rows, ignore_index=True)

        # Color mapping
        col_vals = data[color_by].fillna(0).values
        max_abs = max(abs(col_vals).max(), 0.01)
        normalized = col_vals / max_abs  # -1 to 1

        def _color(v: float) -> str:
            """Red–grey–green gradient."""
            if v >= 0:
                intensity = min(int(v * 200), 200)
                return f"rgb(0,{100 + intensity},0)"
            else:
                intensity = min(int(-v * 200), 200)
                return f"rgb({100 + intensity},0,0)"

        colors = [_color(n) for n in normalized]

        # Build treemap
        labels, parents, values, customdata = [], [], [], []

        # Root
        labels.append("Market")
        parents.append("")
        values.append(0)
        customdata.append(("", "", 0.0, 0.0))

        # Sectors
        for sector in data["sector"].unique():
            labels.append(sector)
            parents.append("Market")
            values.append(0)
            customdata.append((sector, "", 0.0, 0.0))

        # Tickers
        for _, row in data.iterrows():
            size = max(float(row.get(size_by, 1e9) or 1e9), 1)
            chg = float(row.get("change_1d", 0) or 0)
            labels.append(row["symbol"])
            parents.append(row["sector"])
            values.append(size)
            customdata.append((
                row["name"],
                row["symbol"],
                float(row.get("price", 0) or 0),
                chg,
            ))

        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            customdata=customdata,
            texttemplate=(
                "<b>%{label}</b><br>"
                "%{customdata[3]:.2f}%"
            ),
            hovertemplate=(
                "<b>%{customdata[1]}</b> — %{customdata[0]}<br>"
                "Price: $%{customdata[2]:.2f}<br>"
                "Change: %{customdata[3]:.2f}%<br>"
                "<extra></extra>"
            ),
            marker=dict(
                colors=[_color(n) for n in normalized] + ["transparent"] * (
                    len(data["sector"].unique()) + 1
                ),
                line=dict(width=1.5, color=_C["bg"]),
            ),
            maxdepth=3,
            branchvalues="total",
            textfont=dict(color="white", size=11),
        ))

        change_range = data["change_1d"].abs().max()
        subtitle = f"Color: {color_by.replace('_', ' ')} | Size: {size_by.replace('_', ' ')}"

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            font=dict(color=_C["text"]),
            title=dict(
                text=f"<b>Market Heatmap</b>  <span style='font-size:12px;color:{_C['text_muted']}'>{subtitle}</span>",
                font=dict(size=16),
            ),
            height=650,
            margin=dict(l=10, r=10, t=60, b=10),
        )

        return fig
