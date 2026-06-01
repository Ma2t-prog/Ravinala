"""
screener.py — Stock screener combining technical + fundamental filters.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from .technical import TechnicalIndicators


# ─────────────────────────────────────────────────────────────────────────────
# PRESET SCREENS
# ─────────────────────────────────────────────────────────────────────────────

PRESET_SCREENS: Dict[str, Dict] = {
    "oversold_quality": {
        "description": "High-quality stocks that are technically oversold",
        "icon": "",
        "filters": {
            "rsi_14": {"max": 35},
            "roe": {"min": 0.10},
            "market_cap": {"min": 2e9},
            "pe_ratio": {"max": 40},
        },
    },
    "breakout_candidates": {
        "description": "Near 52-week highs with increasing volume",
        "icon": "",
        "filters": {
            "pct_from_52w_high": {"max": 5},
            "volume_ratio": {"min": 1.5},
            "rsi_14": {"min": 50},
        },
    },
    "value_plays": {
        "description": "Undervalued with positive free cash flow",
        "icon": "",
        "filters": {
            "pe_ratio": {"max": 15},
            "pb_ratio": {"max": 2},
            "market_cap": {"min": 500e6},
            "net_margin": {"min": 0.05},
        },
    },
    "dividend_champions": {
        "description": "High yield with sustainable payout",
        "icon": "",
        "filters": {
            "dividend_yield": {"min": 0.03},
            "payout_ratio": {"max": 0.75},
            "market_cap": {"min": 1e9},
        },
    },
    "momentum_leaders": {
        "description": "Strong momentum, price above key MAs",
        "icon": "",
        "filters": {
            "rsi_14": {"min": 55, "max": 80},
            "price_above_sma200": True,
            "pct_change_3m": {"min": 5},
        },
    },
    "deep_value": {
        "description": "Low EV/EBITDA with positive earnings",
        "icon": "",
        "filters": {
            "ev_ebitda": {"max": 8},
            "pe_ratio": {"min": 0, "max": 20},
            "market_cap": {"min": 200e6},
        },
    },
    "growth_at_reasonable_price": {
        "description": "PEG < 1.5, strong revenue growth",
        "icon": "",
        "filters": {
            "peg_ratio": {"max": 1.5},
            "revenue_growth": {"min": 0.10},
            "market_cap": {"min": 500e6},
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

def _get_sp500() -> List[str]:
    """Fetch S&P 500 constituents from Wikipedia."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
    except Exception:
        return [
            "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "V",
            "UNH", "XOM", "JNJ", "PG", "MA", "HD", "CVX", "ABBV", "MRK", "LLY",
            "PEP", "KO", "BAC", "COST", "TMO", "AVGO", "MCD", "WMT", "ABT", "PFE",
            "CSCO", "ACN", "CRM", "DHR", "VZ", "WFC", "TXN", "AMD", "NKE", "PM",
            "RTX", "INTC", "BMY", "ADBE", "UNP", "ORCL", "CMCSA", "QCOM", "HON", "MS",
        ]


def _get_nasdaq100() -> List[str]:
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "ASML", "ADBE",
        "COST", "AMD", "NFLX", "QCOM", "TXN", "CSCO", "INTC", "INTU", "PEP", "CMCSA",
        "HON", "AMAT", "ISRG", "BKNG", "REGN", "VRTX", "LRCX", "MU", "ADI", "PANW",
    ]


def _get_cac40() -> List[str]:
    return [
        "MC.PA", "TTE.PA", "SAN.PA", "AIR.PA", "BNP.PA", "STLAM.MI", "RMS.PA", "OR.PA",
        "EL.PA", "CS.PA", "DG.PA", "CAP.PA", "SGO.PA", "ML.PA", "RI.PA", "ACA.PA",
        "ENGI.PA", "VIE.PA", "BN.PA", "GLE.PA", "STM.PA", "SU.PA", "DSY.PA", "ALO.PA",
        "URW.PA", "FP.PA", "ERF.PA", "AI.PA", "WLN.PA", "PUB.PA", "KER.PA", "SAF.PA",
        "SW.PA", "ORA.PA", "EDEN.PA", "RNO.PA", "SG.PA", "HO.PA", "TEP.PA", "VK.PA",
    ]


def _get_eurostoxx50() -> List[str]:
    return [
        "ABI.BR", "ADYEN.AS", "AIR.PA", "ALV.DE", "ASML.AS", "AXA.PA", "BBVA.MC",
        "BNP.PA", "BMW.DE", "CRH.L", "CS.PA", "DG.PA", "DB1.DE", "DHL.DE", "DTEn.DE",
        "ENEL.MI", "ENI.MI", "IBE.MC", "IFX.DE", "ITX.MC", "KER.PA", "MC.PA", "MBG.DE",
        "MNDI.L", "MUV2.DE", "OR.PA", "PHIA.AS", "PRX.AS", "RAND.AS", "RMS.PA", "SAN.MC",
        "SAN.PA", "SAP.DE", "SG.PA", "STLAM.MI", "TEF.MC", "TTE.PA", "VIV.PA", "VO.PA",
        "VWS.CO",
    ]


UNIVERSES: Dict[str, Any] = {
    "sp500":       _get_sp500,
    "nasdaq100":   _get_nasdaq100,
    "cac40":       _get_cac40,
    "eurostoxx50": _get_eurostoxx50,
}


class StockScreener:
    """Stock screener with combined technical and fundamental filters.

    Features:
    - 30+ filter criteria (technical + fundamental)
    - Parallel data fetching (ThreadPoolExecutor)
    - Preset screens
    - Custom filter builder
    """

    # ─────────────────────────────────────────────────────────────────────────
    # UNIVERSE LOADER
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_universe(name: str) -> List[str]:
        """Return ticker list for a named universe.

        Args:
            name: 'sp500' | 'nasdaq100' | 'cac40' | 'eurostoxx50' or list.

        Returns:
            List of ticker strings.
        """
        if name in UNIVERSES:
            return UNIVERSES[name]()
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # SINGLE TICKER DATA FETCH
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch_ticker_data(symbol: str) -> Optional[Dict]:
        """Fetch all screening metrics for one ticker.

        Returns None on failure.
        """
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
            hist = t.history(period="1y", auto_adjust=True)
        except Exception:
            return None

        if hist is None or hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            return None

        # Technical metrics
        rsi_val = None
        try:
            rsi_val = float(TechnicalIndicators.rsi(close, 14).iloc[-1])
        except Exception:
            pass

        sma_20 = float(TechnicalIndicators.sma(close, 20).iloc[-1])
        sma_50 = float(TechnicalIndicators.sma(close, 50).iloc[-1])
        sma_200 = float(TechnicalIndicators.sma(close, 200).iloc[-1])

        high_52w = float(close.rolling(min(252, len(close))).max().iloc[-1])
        low_52w = float(close.rolling(min(252, len(close))).min().iloc[-1])

        pct_from_52w_high = (price - high_52w) / high_52w * 100 if high_52w else 0
        pct_from_52w_low = (price - low_52w) / low_52w * 100 if low_52w else 0

        vol_avg20 = float(hist["Volume"].rolling(20).mean().iloc[-1]) if "Volume" in hist.columns else 1
        vol_last = float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
        volume_ratio = vol_last / vol_avg20 if vol_avg20 > 0 else 1

        def ret(days: int) -> float:
            if len(close) > days:
                return float((close.iloc[-1] - close.iloc[-days]) / close.iloc[-days] * 100)
            return float("nan")

        # Fundamental metrics
        def safe(key: str):
            v = info.get(key)
            return v if v is not None else np.nan

        return {
            "symbol":             symbol,
            "name":               info.get("shortName", symbol),
            "sector":             info.get("sector", ""),
            "industry":           info.get("industry", ""),
            "price":              price,
            # Technical
            "rsi_14":             rsi_val,
            "price_above_sma20":  price > sma_20,
            "price_above_sma50":  price > sma_50,
            "price_above_sma200": price > sma_200,
            "pct_from_52w_high":  pct_from_52w_high,
            "pct_from_52w_low":   pct_from_52w_low,
            "volume_ratio":       volume_ratio,
            "pct_change_1d":      ret(1),
            "pct_change_5d":      ret(5),
            "pct_change_1m":      ret(21),
            "pct_change_3m":      ret(63),
            "pct_change_6m":      ret(126),
            "pct_change_1y":      ret(252),
            # Fundamental
            "market_cap":         safe("marketCap"),
            "pe_ratio":           safe("trailingPE"),
            "forward_pe":         safe("forwardPE"),
            "peg_ratio":          safe("pegRatio"),
            "pb_ratio":           safe("priceToBook"),
            "ps_ratio":           safe("priceToSalesTrailing12Months"),
            "ev_ebitda":          safe("enterpriseToEbitda"),
            "dividend_yield":     safe("dividendYield"),
            "payout_ratio":       safe("payoutRatio"),
            "roe":                safe("returnOnEquity"),
            "roa":                safe("returnOnAssets"),
            "gross_margin":       safe("grossMargins"),
            "operating_margin":   safe("operatingMargins"),
            "net_margin":         safe("profitMargins"),
            "revenue_growth":     safe("revenueGrowth"),
            "earnings_growth":    safe("earningsGrowth"),
            "debt_equity":        safe("debtToEquity"),
            "current_ratio":      safe("currentRatio"),
            "fcf":                safe("freeCashflow"),
            "beta":               safe("beta"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # FILTER APPLICATION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_filter(row: Dict, filters: Dict) -> bool:
        """Return True if row passes all filters."""
        for key, condition in filters.items():
            val = row.get(key)

            # Boolean filter
            if isinstance(condition, bool):
                if condition and val is not True:
                    return False
                if not condition and val is not False:
                    return False
                continue

            # Range filter
            if isinstance(condition, dict):
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    return False
                min_val = condition.get("min")
                max_val = condition.get("max")
                if min_val is not None and val < min_val:
                    return False
                if max_val is not None and val > max_val:
                    return False

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN SCREEN METHOD
    # ─────────────────────────────────────────────────────────────────────────

    def screen(
        self,
        universe: List[str] | str,
        filters: Dict,
        sort_by: str = "market_cap",
        ascending: bool = False,
        limit: int = 50,
        max_workers: int = 30,
    ) -> pd.DataFrame:
        """Run a screen against a universe.

        Args:
            universe: List of tickers or universe name ('sp500', 'nasdaq100', etc.).
            filters: Dict of filter conditions (see module docstring).
            sort_by: Column to sort results by.
            ascending: Sort direction.
            limit: Maximum results to return.
            max_workers: Parallel fetch workers.

        Returns:
            DataFrame with screening results, sorted and limited.
        """
        if isinstance(universe, str):
            tickers = self.get_universe(universe)
        else:
            tickers = list(universe)

        if not tickers:
            return pd.DataFrame()

        rows = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(self._fetch_ticker_data, s): s for s in tickers}
            for f in as_completed(futures):
                try:
                    data = f.result()
                    if data and self._apply_filter(data, filters):
                        rows.append(data)
                except Exception:
                    pass

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Sort
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending, na_position="last")

        return df.head(limit).reset_index(drop=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PRESET SCREENS
    # ─────────────────────────────────────────────────────────────────────────

    def run_preset(self, preset_name: str,
                   universe: str = "nasdaq100") -> pd.DataFrame:
        """Run one of the predefined preset screens.

        Args:
            preset_name: Key from PRESET_SCREENS.
            universe: Universe to scan.

        Returns:
            DataFrame of results.
        """
        if preset_name not in PRESET_SCREENS:
            return pd.DataFrame()
        return self.screen(
            universe,
            PRESET_SCREENS[preset_name]["filters"],
            sort_by="market_cap",
        )
