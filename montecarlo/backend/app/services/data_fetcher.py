"""
Data fetching service - yfinance, FRED, CoinGecko, etc.
Handles all external API calls + fallback logic.

Delegates live data to providers/yfinance_adapter.py (Étape 5 complétion).
The provider returns canonical types; this service converts them to the
dict format expected by existing routes and snapshot_service.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

from app.providers.coingecko_adapter import CoinGeckoProvider
from app.providers.fred_adapter import FREDAdapter
from app.providers.yfinance_adapter import YFinanceProvider

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    """Return a timezone-aware UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()

# Constants
INDICES_30 = {
    "^GSPC": ("S&P 500", "Americas"),
    "^INDU": ("Dow Jones", "Americas"),
    "^NDX": ("NASDAQ-100", "Americas"),
    "^RUT": ("Russell 2000", "Americas"),
    "^BVSP": ("IBOVESPA", "Americas"),
    "^STOXX50E": ("EURO STOXX 50", "Europe"),
    "^GDAXI": ("DAX 40", "Europe"),
    "^FCHI": ("CAC 40", "Europe"),
    "^FTSE": ("FTSE 100", "Europe"),
    "^N225": ("Nikkei 225", "Asia-Pacific"),
    "^HSI": ("Hang Seng", "Asia-Pacific"),
    "000001.SS": ("Shanghai Composite", "Asia-Pacific"),
    "^KS11": ("KOSPI", "Asia-Pacific"),
    "^STI": ("STI", "Asia-Pacific"),
    "^AXJO": ("ASX 200", "Asia-Pacific"),
    "^BSESN": ("SENSEX", "Asia-Pacific"),
    "^TASI": ("TASI", "Middle East"),
    "^CASE30": ("EGX 30", "Middle East"),
    "^JKSE": ("JKSE", "Asia-Pacific"),
}

FX_PAIRS_20 = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF",
    "USDCAD=X": "USD/CAD",
    "AUDUSD=X": "AUD/USD",
    "NZDUSD=X": "NZD/USD",
    "EURGBP=X": "EUR/GBP",
    "GBPJPY=X": "GBP/JPY",
    "EUROJPY=X": "EUR/JPY",
}

COMMODITIES = {
    "GC=F": ("Gold", "Metals"),
    "SI=F": ("Silver", "Metals"),
    "PL=F": ("Platinum", "Metals"),
    "CU=F": ("Copper", "Metals"),
    "CL=F": ("WTI Crude", "Energy"),
    "BZ=F": ("Brent Crude", "Energy"),
    "NG=F": ("Natural Gas", "Energy"),
    "ZW=F": ("Wheat", "Agriculture"),
    "ZC=F": ("Corn", "Agriculture"),
    "ZS=F": ("Soybeans", "Agriculture"),
}

CRYPTO_PAIRS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}

class DataFetcher:
    """Fetch data from multiple sources with fallback & validation."""

    def __init__(self):
        self.timeout = 10
        self._provider = YFinanceProvider(timeout=self.timeout)
        self._crypto_provider = CoinGeckoProvider(timeout=5)

        # FRED provider — active only when FRED_API_KEY is set in env/config
        try:
            from app.core.config import get_settings
            _fred_key = get_settings().fred_api_key
        except Exception:
            _fred_key = ""
        self._fred: Optional[FREDAdapter] = FREDAdapter(api_key=_fred_key, timeout=self.timeout) if _fred_key else None
        if self._fred:
            logger.info("DataFetcher: FRED provider active (bonds + macro will be live)")
        else:
            logger.info("DataFetcher: FRED_API_KEY not set — bonds/macro use demo_static fallback")

    def _ticker_history(self, ticker: str, period: str = "5d") -> pd.DataFrame:
        """Fetch history via provider (R3 compliant — no direct yfinance)."""
        return self._provider.fetch_history(ticker, period=period)
    
    # ═══════════════════════════════════════════════════════════════════════
    # INDICES
    # ═══════════════════════════════════════════════════════════════════════
    
    def fetch_indices(self, limit: int = 30) -> Dict:
        """Fetch global indices using a single batch download (much faster)."""
        result = {"americas": [], "europe": [], "asia_pacific": [], "middle_east_other": []}
        tickers_config = list(INDICES_30.items())[:limit]
        tickers = [t for t, _ in tickers_config]

        # Single network call for all tickers
        batch = self._provider.fetch_history_batch(tickers)

        for ticker, (name, region) in tickers_config:
            try:
                hist = batch.get(ticker)
                if hist is None or hist.empty:
                    logger.warning(f"⚠️ No data for {ticker}")
                    continue

                close = hist['Close'].dropna()
                if close.empty:
                    continue

                current = float(close.iloc[-1])
                prev = float(close.iloc[-2]) if len(close) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0

                asset = {
                    "symbol": ticker,
                    "name": name,
                    "region": region,
                    "price": current,
                    "change": {
                        "absolute": current - prev,
                        "percent": change_pct,
                        "direction": "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat"),
                        "color": "green" if change_pct > 0 else ("red" if change_pct < 0 else "neutral"),
                    },
                    "timestamp": _utcnow_iso(),
                    "is_stale": False,
                    "data_source": "yfinance",
                }

                region_key = region.lower().replace("-", "_").replace(" ", "_")
                if region_key == "americas":
                    result["americas"].append(asset)
                elif region_key == "europe":
                    result["europe"].append(asset)
                elif region_key.startswith("asia"):
                    result["asia_pacific"].append(asset)
                else:
                    result["middle_east_other"].append(asset)

            except Exception as e:
                logger.error(f"❌ Failed to process {ticker}: {e}")
                continue

        result["last_updated"] = _utcnow_iso()
        result["cache_age_seconds"] = 0
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # FX PAIRS
    # ═══════════════════════════════════════════════════════════════════════
    
    def fetch_fx_pairs(self) -> Dict:
        """Fetch FX pairs using a single batch download."""
        usd_base = []
        crosses = []
        tickers = list(FX_PAIRS_20.keys())

        batch = self._provider.fetch_history_batch(tickers)

        for ticker, name in FX_PAIRS_20.items():
            try:
                hist = batch.get(ticker)
                if hist is None or hist.empty:
                    continue

                close = hist['Close'].dropna()
                if close.empty:
                    continue

                current = float(close.iloc[-1])
                prev = float(close.iloc[-2]) if len(close) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0

                pair_data = {
                    "pair": name,
                    "bid": float(current * 0.9999),
                    "ask": float(current * 1.0001),
                    "mid_price": float(current),
                    "change_percent": float(change_pct),
                    "volatility_percent": 0.5,
                    "last_updated": _utcnow_iso(),
                }

                if "/" in name and name.split("/")[1] == "USD":
                    usd_base.append(pair_data)
                else:
                    crosses.append(pair_data)

            except Exception as e:
                logger.error(f"❌ Failed to process FX {ticker}: {e}")
                continue

        return {
            "usd_base": usd_base,
            "crosses": crosses,
            "last_updated": _utcnow_iso(),
            "cache_age_seconds": 0,
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMMODITIES
    # ═══════════════════════════════════════════════════════════════════════
    
    def fetch_commodities(self) -> Dict:
        """Fetch commodities by category using a single batch download."""
        result = {"metals": [], "energy": [], "agriculture": [], "crypto": []}
        tickers = list(COMMODITIES.keys())

        batch = self._provider.fetch_history_batch(tickers)

        for ticker, (name, category) in COMMODITIES.items():
            try:
                hist = batch.get(ticker)
                if hist is None or hist.empty:
                    continue

                close = hist['Close'].dropna()
                if close.empty:
                    continue

                current = float(close.iloc[-1])
                prev = float(close.iloc[-2]) if len(close) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0

                comm = {
                    "symbol": ticker,
                    "name": name,
                    "category": category,
                    "price": float(current),
                    "unit": "USD",
                    "change_percent": float(change_pct),
                    "timestamp": _utcnow_iso(),
                }

                cat_key = category.lower()
                if cat_key in result:
                    result[cat_key].append(comm)

            except Exception as e:
                logger.error(f"❌ Failed to process commodity {ticker}: {e}")
                continue
        
        # Fetch crypto separately through the provider boundary.
        try:
            data = self._crypto_provider.fetch_simple_prices(
                ids=["bitcoin", "ethereum"],
                vs_currency="usd",
                include_24hr_change=True,
            )
            if "bitcoin" in data:
                result["crypto"].append({
                    "symbol": "BTC-USD",
                    "name": "Bitcoin",
                    "category": "Crypto",
                    "price": float(data["bitcoin"]["usd"]),
                    "unit": "USD",
                    "change_percent": float(data["bitcoin"].get("usd_24h_change", 0)),
                    "timestamp": _utcnow_iso(),
                })
            if "ethereum" in data:
                result["crypto"].append({
                    "symbol": "ETH-USD",
                    "name": "Ethereum",
                    "category": "Crypto",
                    "price": float(data["ethereum"]["usd"]),
                    "unit": "USD",
                    "change_percent": float(data["ethereum"].get("usd_24h_change", 0)),
                    "timestamp": _utcnow_iso(),
                })
        except Exception as e:
            logger.warning(f"⚠️ Crypto fetch failed: {e}")
        
        result["last_updated"] = _utcnow_iso()
        result["cache_age_seconds"] = 0
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # BONDS
    # Live via FRED when FRED_API_KEY is configured; demo_static otherwise.
    # ═══════════════════════════════════════════════════════════════════════

    def fetch_bonds(self) -> Dict:
        """Fetch government bond yields. Live if FRED key set, demo fallback otherwise."""
        if self._fred is not None:
            try:
                live_bonds = self._fred.fetch_bonds()
                if live_bonds:
                    return {
                        "bonds":             live_bonds,
                        "benchmark_country": "Germany",
                        "last_updated":      _utcnow_iso(),
                        "cache_age_seconds": 0,
                        "data_quality":      "live",
                        "data_quality_note": (
                            "US yields live via FRED (DGS2/DGS5/DGS10). "
                            "International 10Y live via FRED OECD series; 2Y/5Y are curve approximations."
                        ),
                    }
                logger.warning("FRED.fetch_bonds() returned empty list — falling back to demo")
            except Exception as exc:
                logger.error("FRED bonds error: %s — falling back to demo", exc)

        # ── Demo fallback ─────────────────────────────────────────────────
        bonds = [
            {
                "country": "USA",        "country_code": "US",
                "yield_2y": 4.12,        "yield_5y": 4.15,   "yield_10y": 4.22,
                "spread_vs_bund_bp": 245, "curve_slope_percent": 0.1, "direction": "up",
                "last_updated": _utcnow_iso(),
            },
            {
                "country": "Germany",    "country_code": "DE",
                "yield_2y": 2.18,        "yield_5y": 2.35,   "yield_10y": 2.47,
                "spread_vs_bund_bp": 0,  "curve_slope_percent": 0.29, "direction": "flat",
                "last_updated": _utcnow_iso(),
            },
            {
                "country": "Japan",      "country_code": "JP",
                "yield_2y": 0.08,        "yield_5y": 0.25,   "yield_10y": 1.05,
                "spread_vs_bund_bp": -142, "curve_slope_percent": 0.97, "direction": "up",
                "last_updated": _utcnow_iso(),
            },
            {
                "country": "UK",         "country_code": "GB",
                "yield_2y": 5.10,        "yield_5y": 5.08,   "yield_10y": 4.98,
                "spread_vs_bund_bp": 251, "curve_slope_percent": -0.12, "direction": "down",
                "last_updated": _utcnow_iso(),
            },
            {
                "country": "France",     "country_code": "FR",
                "yield_2y": 2.64,        "yield_5y": 2.82,   "yield_10y": 2.98,
                "spread_vs_bund_bp": 51,  "curve_slope_percent": 0.34, "direction": "up",
                "last_updated": _utcnow_iso(),
            },
        ]
        return {
            "bonds": bonds,
            "benchmark_country": "Germany",
            "last_updated": _utcnow_iso(),
            "cache_age_seconds": 0,
            "data_quality": "demo_static",
            "data_quality_note": "Bond yields are hardcoded demo values. Set FRED_API_KEY for live data.",
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # MACRO
    # Live via FRED when FRED_API_KEY is configured; demo_static otherwise.
    # ═══════════════════════════════════════════════════════════════════════

    def fetch_macro(self) -> Dict:
        """Fetch macro indicators. Live if FRED key set, demo fallback otherwise."""
        if self._fred is not None:
            try:
                live_indicators = self._fred.fetch_macro()
                if live_indicators:
                    return {
                        "indicators":        live_indicators,
                        "last_updated":      _utcnow_iso(),
                        "cache_age_seconds": 0,
                        "data_quality":      "live",
                        "data_quality_note": (
                            "US: CPI YoY computed from CPIAUCSL, Unemployment from UNRATE, "
                            "GDP from A191RL1Q225SBEA (all via FRED). "
                            "Eurozone: Unemployment from LRHUTTTTEZM156S. "
                            "Limitation: monthly/quarterly series, 1-2 month lag. "
                            "China macro and PMI not covered by free FRED."
                        ),
                    }
                logger.warning("FRED.fetch_macro() returned empty list — falling back to demo")
            except Exception as exc:
                logger.error("FRED macro error: %s — falling back to demo", exc)

        # ── Demo fallback ─────────────────────────────────────────────────
        indicators = [
            {
                "country": "USA",       "indicator": "CPI YoY",
                "latest_value": 3.4,    "unit": "%",
                "forecast_value": 3.2,  "previous_value": 3.5,
                "release_date": _utcnow_iso(), "source": "BLS", "sentiment": "negative",
            },
            {
                "country": "USA",       "indicator": "PMI Manufacturing",
                "latest_value": 52.0,   "unit": "index",
                "forecast_value": 51.5, "previous_value": 51.8,
                "release_date": _utcnow_iso(), "source": "ISM", "sentiment": "positive",
            },
            {
                "country": "Eurozone",  "indicator": "Unemployment",
                "latest_value": 6.5,    "unit": "%",
                "forecast_value": 6.4,  "previous_value": 6.6,
                "release_date": _utcnow_iso(), "source": "Eurostat", "sentiment": "positive",
            },
            {
                "country": "China",     "indicator": "GDP YoY",
                "latest_value": 5.2,    "unit": "%",
                "forecast_value": 5.0,  "previous_value": 4.9,
                "release_date": _utcnow_iso(), "source": "NBS", "sentiment": "positive",
            },
        ]
        return {
            "indicators":        indicators,
            "last_updated":      _utcnow_iso(),
            "cache_age_seconds": 0,
            "data_quality":      "demo_static",
            "data_quality_note": "Macro indicators are hardcoded demo values. Set FRED_API_KEY for live data.",
        }

# Singleton
_data_fetcher = None

def get_data_fetcher() -> DataFetcher:
    """Get or create data fetcher."""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher
