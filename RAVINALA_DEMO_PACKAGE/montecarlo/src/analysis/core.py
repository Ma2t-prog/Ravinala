"""
core.py — Data fetching, caching, and base utilities for Financial Analysis Suite.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ─────────────────────────────────────────────────────────────────────────────
# TIMEFRAME MAPPING
# ─────────────────────────────────────────────────────────────────────────────
TIMEFRAME_MAP: Dict[str, Tuple[str, str]] = {
    "1m":  ("7d",   "1m"),
    "5m":  ("60d",  "5m"),
    "15m": ("60d",  "15m"),
    "30m": ("60d",  "30m"),
    "1h":  ("730d", "60m"),
    "4h":  ("730d", "60m"),
    "1d":  ("5y",   "1d"),
    "1w":  ("max",  "1wk"),
    "1M":  ("max",  "1mo"),
}

DARK_THEME = {
    "bg": "#0a0a0f",
    "panel": "#12121a",
    "surface": "#1a1a2e",
    "border": "#2a2a3e",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
    "green": "#22c55e",
    "red": "#ef4444",
    "blue": "#3b82f6",
    "yellow": "#f59e0b",
    "purple": "#a855f7",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHER
# ─────────────────────────────────────────────────────────────────────────────
class DataFetcher:
    """Centralized data-fetching layer with yFinance backend."""

    @staticmethod
    @st.cache_data(ttl=120)
    def ohlcv(symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """Fetch OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'EURUSD=X').
            timeframe: One of '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'.

        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume] or empty DataFrame.
        """
        period, interval = TIMEFRAME_MAP.get(timeframe, ("1y", "1d"))
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                repair=True,
            )
        except Exception:
            return pd.DataFrame()

        if df is None or df.empty:
            return pd.DataFrame()

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(subset=["Close"], inplace=True)

        # Resample 4h from 1h data
        if timeframe == "4h":
            ohlc = df[["Open", "High", "Low", "Close"]].resample("4h").agg(
                {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
            )
            vol = df[["Volume"]].resample("4h").sum()
            df = pd.concat([ohlc, vol], axis=1).dropna()

        return df.copy()

    @staticmethod
    @st.cache_data(ttl=60)
    def snapshot(symbol: str) -> Dict:
        """Fetch latest price snapshot (price, change, market cap, etc.).

        Args:
            symbol: Ticker symbol.

        Returns:
            Dictionary with price data or empty dict on failure.
        """
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
            hist = t.history(period="2d", auto_adjust=True)
        except Exception:
            return {}

        if hist is None or hist.empty:
            return {}

        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        chg = price - prev
        chg_pct = (chg / prev * 100) if prev != 0 else 0.0

        return {
            "symbol": symbol,
            "price": price,
            "change": chg,
            "change_pct": chg_pct,
            "volume": int(hist["Volume"].iloc[-1]),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "name": info.get("shortName", symbol),
            "sector": info.get("sector", ""),
            "currency": info.get("currency", "USD"),
        }

    @staticmethod
    @st.cache_data(ttl=300)
    def ticker_info(symbol: str) -> Dict:
        """Fetch full yfinance .info dict for a symbol.

        Args:
            symbol: Ticker symbol.

        Returns:
            yFinance info dictionary or empty dict.
        """
        try:
            return yf.Ticker(symbol).info or {}
        except Exception:
            return {}

    @staticmethod
    @st.cache_data(ttl=300)
    def multi_snapshot(symbols: List[str]) -> Dict[str, Dict]:
        """Batch-fetch snapshots for a list of symbols.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Dict mapping symbol → snapshot dict.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: Dict[str, Dict] = {}
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(DataFetcher.snapshot, s): s for s in symbols}
            for f in as_completed(futures):
                sym = futures[f]
                try:
                    results[sym] = f.result()
                except Exception:
                    results[sym] = {}
        return results


# ─────────────────────────────────────────────────────────────────────────────
# MARKET DATA CACHE (thin wrapper kept for API compatibility)
# ─────────────────────────────────────────────────────────────────────────────
class MarketDataCache:
    """Simple in-process cache with TTL for market data not covered by st.cache_data."""

    def __init__(self, ttl_seconds: int = 120):
        self._store: Dict[str, Tuple[float, object]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[object]:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return val

    def set(self, key: str, value: object) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()
