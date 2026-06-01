"""
ETF Data Fetcher — yfinance primary, OpenFIGI + FMP supplementary.

Usage (inside Streamlit):
    from etf_data_fetcher import ETFDataFetcher
    fetcher = ETFDataFetcher()
    data = fetcher.fetch("IE00B4L5Y983")   # pass ISIN or ticker
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

from etf_isin_resolver import resolve, is_valid_isin, UCITS_ISIN_MAP
from etf_benchmark_db import get_benchmark, BENCHMARK_DB
from etf_calculations import (
    compute_performance,
    compute_risk,
    compute_tracking,
    PerformanceMetrics,
    RiskMetrics,
    TrackingMetrics,
)

logger = logging.getLogger(__name__)

# ── FMP config ────────────────────────────────────────────────────────────────
_FMP_BASE = "https://financialmodelingprep.com/api/v3"
_FMP_KEY = os.getenv("FMP_API_KEY", "demo")   # set env var for real key


# ── ETFData model ─────────────────────────────────────────────────────────────

@dataclass
class ETFData:
    # Identity
    isin: str = ""
    ticker: str = ""
    name: str = ""
    issuer: str = ""
    currency: str = ""
    domicile: str = ""
    inception_date: str = ""
    asset_class: str = ""
    region: str = ""
    replication: str = ""      # Physical / Synthetic
    distribution: str = ""     # Accumulating / Distributing
    ucits: bool = True

    # Costs
    ter: float | None = None       # Total Expense Ratio (%)
    spread_bps: float | None = None

    # Size
    aum_usd: float | None = None   # AUM in USD millions
    nav: float | None = None       # Latest NAV / price

    # Prices
    prices: pd.Series = field(default_factory=pd.Series)
    benchmark_prices: pd.Series = field(default_factory=pd.Series)
    benchmark_name: str = ""

    # Top holdings
    holdings: list[dict] = field(default_factory=list)
    # Sector/geo allocations
    sector_weights: dict[str, float] = field(default_factory=dict)
    country_weights: dict[str, float] = field(default_factory=dict)

    # Calculated metrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    tracking: TrackingMetrics = field(default_factory=TrackingMetrics)

    # Meta
    error: str = ""
    source: str = ""


# ── Fetcher ───────────────────────────────────────────────────────────────────

class ETFDataFetcher:
    """Fetch ETF data from yfinance (primary) and FMP (supplementary)."""

    def __init__(self, fmp_key: str | None = None):
        self._fmp_key = fmp_key or _FMP_KEY

    # ── Public entry point ────────────────────────────────────────────────────

    def fetch(
        self,
        query: str,
        period_years: int = 5,
    ) -> ETFData:
        """
        Fetch full ETFData for a given ISIN or ticker.

        Parameters
        ----------
        query : str
            Either a 12-char ISIN (e.g. "IE00B4L5Y983") or a Yahoo ticker
            (e.g. "IWDA.AS").
        period_years : int
            How many years of price history to fetch (1–10).
        """
        data = ETFData()
        query = query.strip().upper()

        # Resolve to ticker
        if is_valid_isin(query):
            data.isin = query
            ticker_str = resolve(query)
            if not ticker_str:
                data.error = f"Could not resolve ISIN {query} to a ticker."
                return data
            data.ticker = ticker_str
        else:
            data.ticker = query

        # Fetch price history from yfinance
        prices, info = self._yf_fetch(data.ticker, period_years)
        if prices is None or len(prices) < 5:
            data.error = f"No price data returned for ticker {data.ticker}."
            return data

        data.prices = prices
        data.source = "yfinance"

        # Populate identity from yfinance info
        self._fill_from_yf_info(data, info)

        # Benchmark
        bm_info = get_benchmark(data.isin) if data.isin else None
        if bm_info:
            data.benchmark_name = bm_info["name"]
            bm_prices, _ = self._yf_fetch(bm_info["ticker"], period_years)
            if bm_prices is not None and len(bm_prices) >= 5:
                data.benchmark_prices = bm_prices
        else:
            # Try to infer benchmark from asset class
            data.benchmark_name = self._infer_benchmark(data.asset_class, data.region)
            if data.benchmark_name and data.benchmark_name in BENCHMARK_DB:
                bm_ticker = BENCHMARK_DB[data.benchmark_name]["ticker"]
                bm_prices, _ = self._yf_fetch(bm_ticker, period_years)
                if bm_prices is not None:
                    data.benchmark_prices = bm_prices

        # Compute metrics
        data.performance = compute_performance(data.prices)
        data.risk = compute_risk(
            data.prices,
            data.benchmark_prices if len(data.benchmark_prices) > 5 else None,
        )
        if len(data.benchmark_prices) > 5:
            data.tracking = compute_tracking(data.prices, data.benchmark_prices)

        # FMP supplementary (holdings, sector, TER)
        if data.ticker and self._fmp_key != "demo":
            self._enrich_fmp(data)

        # Holdings fallback via yfinance
        if not data.holdings and info:
            holdings = info.get("holdings", [])
            if holdings:
                data.holdings = [
                    {"name": h.get("holdingName", ""), "weight": h.get("holdingPercent", 0)}
                    for h in holdings[:15]
                ]
            sector_w = info.get("sectorWeightings", [])
            if sector_w:
                for sw in sector_w:
                    for k, v in sw.items():
                        if k and v:
                            data.sector_weights[k] = v
            country_w = info.get("countryWeightings", [])
            if country_w:
                for cw in country_w:
                    for k, v in cw.items():
                        if k and v:
                            data.country_weights[k] = v

        return data

    # ── yfinance helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _yf_fetch(
        ticker: str, period_years: int
    ) -> tuple[pd.Series | None, dict]:
        """Download price history and info dict from yfinance."""
        try:
            end = date.today()
            start = end - timedelta(days=int(period_years * 365.25))
            tk = yf.Ticker(ticker)
            hist = tk.history(start=str(start), end=str(end), auto_adjust=True)
            if hist.empty:
                return None, {}
            prices = hist["Close"].dropna()
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            info = {}
            try:
                info = tk.info or {}
            except Exception:
                pass
            return prices, info
        except Exception as exc:
            logger.warning("yfinance fetch failed for %s: %s", ticker, exc)
            return None, {}

    @staticmethod
    def _fill_from_yf_info(data: ETFData, info: dict) -> None:
        if not info:
            return
        data.name = info.get("longName") or info.get("shortName") or data.ticker
        data.currency = info.get("currency", "")
        data.nav = info.get("navPrice") or info.get("regularMarketPrice")
        data.aum_usd = info.get("totalAssets")
        if data.aum_usd:
            data.aum_usd /= 1e6   # convert to millions
        data.ter = info.get("annualReportExpenseRatio")
        if data.ter:
            data.ter *= 100  # to %
        data.issuer = info.get("fundFamily") or ""
        data.domicile = info.get("domicile") or ""
        data.inception_date = str(info.get("fundInceptionDate") or "")
        data.replication = "Physical" if info.get("isPhysical") else ""
        data.distribution = "Distributing" if info.get("yield", 0) > 0 else "Accumulating"
        # Asset class / region heuristics
        category = info.get("category", "") or ""
        data.asset_class = ETFDataFetcher._map_asset_class(category)
        data.region = info.get("fundRegion") or ETFDataFetcher._map_region(category)

    @staticmethod
    def _map_asset_class(category: str) -> str:
        cat = category.lower()
        if "bond" in cat or "fixed" in cat or "income" in cat:
            return "Fixed Income"
        if "commodity" in cat or "gold" in cat:
            return "Commodity"
        if "real estate" in cat or "reit" in cat:
            return "Real Estate"
        return "Equity"

    @staticmethod
    def _map_region(category: str) -> str:
        cat = category.lower()
        if "world" in cat or "global" in cat:
            return "Global"
        if "europe" in cat or "eurozone" in cat:
            return "Europe"
        if "us" in cat or "america" in cat or "s&p" in cat:
            return "United States"
        if "emerg" in cat:
            return "Emerging Markets"
        if "asia" in cat or "pacific" in cat:
            return "Asia Pacific"
        return "Global"

    @staticmethod
    def _infer_benchmark(asset_class: str, region: str) -> str:
        ac = asset_class.lower()
        reg = region.lower()
        if "fixed" in ac or "bond" in ac:
            if "euro" in reg:
                return "Bloomberg Euro Aggregate"
            return "Bloomberg Global Aggregate"
        if "emerg" in reg:
            return "MSCI Emerging Markets"
        if "europe" in reg or "euro" in reg:
            return "MSCI Europe"
        if "us" in reg or "united states" in reg:
            return "S&P 500"
        return "MSCI World"

    # ── FMP enrichment ────────────────────────────────────────────────────────

    def _enrich_fmp(self, data: ETFData) -> None:
        """Try to add holdings and sector weights from FMP."""
        try:
            # Strip exchange suffix for FMP (it uses bare ticker)
            bare = data.ticker.split(".")[0]
            url = f"{_FMP_BASE}/etf-holder/{bare}?apikey={self._fmp_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                holders = resp.json()
                if isinstance(holders, list) and holders:
                    data.holdings = [
                        {
                            "name": h.get("company", h.get("asset", "")),
                            "weight": h.get("weightPercentage", 0),
                        }
                        for h in holders[:15]
                    ]
        except Exception as exc:
            logger.debug("FMP enrich failed: %s", exc)


# ── Streamlit cache wrapper ───────────────────────────────────────────────────

if _HAS_ST:
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_etf_cached(query: str, period_years: int = 5) -> ETFData:
        """Cached wrapper around ETFDataFetcher.fetch()."""
        return ETFDataFetcher().fetch(query, period_years)
else:
    def fetch_etf_cached(query: str, period_years: int = 5) -> ETFData:
        return ETFDataFetcher().fetch(query, period_years)
