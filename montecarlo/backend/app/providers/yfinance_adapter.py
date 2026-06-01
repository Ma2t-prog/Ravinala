"""
providers/yfinance_adapter.py — YFinance implementation of MarketDataProvider.

Wraps all yfinance calls behind the canonical interface so that
DataFetcher never imports yfinance directly.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import yfinance as yf

from app.providers.base import (
    CanonicalBond,
    CanonicalFXRate,
    CanonicalMacro,
    CanonicalQuote,
    DataQualityLevel,
    MarketDataProvider,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class YFinanceProvider(MarketDataProvider):
    """Concrete provider backed by yfinance + static fallbacks for bonds/macro."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        # Use a fresh temp directory for yfinance's SQLite cache to avoid corruption
        import tempfile
        _tmp_cache = tempfile.mkdtemp(prefix="yfinance_")
        try:
            yf.cache.set_tz_cache_location(_tmp_cache)
        except Exception:
            pass

    # ── quotes (indices / equities) ──────────────────────────────────────

    def fetch_quotes(self, symbols: dict[str, tuple[str, str]], limit: int = 30) -> list[CanonicalQuote]:
        results: list[CanonicalQuote] = []
        for ticker, (name, region) in list(symbols.items())[:limit]:
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if hist.empty:
                    logger.warning("No data for %s", ticker)
                    continue
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
                results.append(CanonicalQuote(
                    symbol=ticker,
                    name=name,
                    price=current,
                    change_absolute=current - prev,
                    change_percent=((current - prev) / prev * 100) if prev else 0.0,
                    timestamp=_utcnow(),
                    data_quality=DataQualityLevel.live,
                    source="yfinance",
                ))
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", ticker, exc)
        return results

    # ── FX ────────────────────────────────────────────────────────────────

    def fetch_fx(self, pairs: dict[str, str]) -> list[CanonicalFXRate]:
        results: list[CanonicalFXRate] = []
        for ticker, name in pairs.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if hist.empty:
                    continue
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
                results.append(CanonicalFXRate(
                    pair=name,
                    bid=current * 0.9999,
                    ask=current * 1.0001,
                    mid=current,
                    change_percent=((current - prev) / prev * 100) if prev else 0.0,
                    timestamp=_utcnow(),
                    data_quality=DataQualityLevel.live,
                ))
            except Exception as exc:
                logger.error("Failed to fetch FX %s: %s", ticker, exc)
        return results

    # ── commodities ───────────────────────────────────────────────────────

    def fetch_commodities(self, symbols: dict[str, tuple[str, str]]) -> list[CanonicalQuote]:
        results: list[CanonicalQuote] = []
        for ticker, (name, category) in symbols.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if hist.empty:
                    continue
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
                results.append(CanonicalQuote(
                    symbol=ticker,
                    name=name,
                    price=current,
                    change_absolute=current - prev,
                    change_percent=((current - prev) / prev * 100) if prev else 0.0,
                    timestamp=_utcnow(),
                    data_quality=DataQualityLevel.live,
                    source="yfinance",
                ))
            except Exception as exc:
                logger.error("Failed to fetch commodity %s: %s", ticker, exc)
        return results

    # ── bonds (demo static) ──────────────────────────────────────────────

    def fetch_history(self, ticker: str, period: str = "5d") -> "pd.DataFrame":
        """Fetch raw OHLCV history for a ticker. Used by DataFetcher and routes."""
        try:
            hist = yf.Ticker(ticker).history(period=period)
            return hist
        except Exception as exc:
            logger.error("Failed to fetch history for %s: %s", ticker, exc)
            import pandas as pd
            return pd.DataFrame()

    def fetch_history_batch(self, tickers: list, period: str = "5d") -> "dict":
        """
        Batch-download OHLCV for multiple tickers in a single yfinance call.
        Returns {ticker: DataFrame} — much faster than per-ticker fetch_history calls.
        """
        import pandas as pd
        if not tickers:
            return {}
        try:
            data = yf.download(tickers, period=period, progress=False, group_by="ticker")
            if data is None or data.empty:
                return {}
            result = {}
            if len(tickers) == 1:
                # Single ticker: flat DataFrame
                if not data.empty and data["Close"].count() > 0:
                    result[tickers[0]] = data
            else:
                # Multiple tickers: MultiIndex (ticker, field)
                for ticker in tickers:
                    try:
                        df = data.xs(ticker, axis=1, level=0)
                        if not df.empty and df["Close"].count() > 0:
                            result[ticker] = df
                    except Exception:
                        pass
            return result
        except Exception as exc:
            logger.error("Batch download failed: %s", exc)
            return {}

    def fetch_prices(self, ticker: str, period: str = "5y") -> "pd.DataFrame":
        """Fetch OHLCV data via yfinance download (for ML/risk routes)."""
        import pandas as pd
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if data is None or data.empty:
            raise ValueError(f"No price data returned for {ticker}")
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data

    def fetch_prices_batch(self, tickers: list[str], period: str = "5y") -> "pd.DataFrame":
        """
        Fetch OHLCV data for multiple tickers in one provider call.

        Returns the raw yfinance MultiIndex frame when several tickers are
        requested so downstream engines can keep price-by-ticker semantics.
        """
        unique_tickers = sorted({ticker for ticker in tickers if ticker})
        if not unique_tickers:
            raise ValueError("At least one ticker is required")

        data = yf.download(unique_tickers, period=period, progress=False, auto_adjust=True)
        if data is None or data.empty:
            raise ValueError(f"No price data returned for tickers: {unique_tickers}")
        return data

    def fetch_bonds(self) -> list[CanonicalBond]:
        now = _utcnow()
        return [
            CanonicalBond(country="USA", country_code="US", yield_2y=4.12, yield_5y=4.15, yield_10y=4.22, spread_vs_bund_bp=245, timestamp=now),
            CanonicalBond(country="Germany", country_code="DE", yield_2y=2.18, yield_5y=2.35, yield_10y=2.47, spread_vs_bund_bp=0, timestamp=now),
            CanonicalBond(country="Japan", country_code="JP", yield_2y=0.08, yield_5y=0.25, yield_10y=1.05, spread_vs_bund_bp=-142, timestamp=now),
            CanonicalBond(country="UK", country_code="GB", yield_2y=5.10, yield_5y=5.08, yield_10y=4.98, spread_vs_bund_bp=251, timestamp=now),
            CanonicalBond(country="France", country_code="FR", yield_2y=2.64, yield_5y=2.82, yield_10y=2.98, spread_vs_bund_bp=51, timestamp=now),
        ]

    # ── macro (demo static) ──────────────────────────────────────────────

    def fetch_macro(self) -> list[CanonicalMacro]:
        now = _utcnow()
        return [
            CanonicalMacro(country="USA", indicator="CPI YoY", latest_value=3.4, unit="%", forecast_value=3.2, previous_value=3.5, source="BLS", timestamp=now),
            CanonicalMacro(country="USA", indicator="PMI Manufacturing", latest_value=52.0, unit="index", forecast_value=51.5, previous_value=51.8, source="ISM", timestamp=now),
            CanonicalMacro(country="Eurozone", indicator="Unemployment", latest_value=6.5, unit="%", forecast_value=6.4, previous_value=6.6, source="Eurostat", timestamp=now),
            CanonicalMacro(country="China", indicator="GDP YoY", latest_value=5.2, unit="%", forecast_value=5.0, previous_value=4.9, source="NBS", timestamp=now),
        ]

    # ── health ────────────────────────────────────────────────────────────

    def health_check(self) -> ProviderStatus:
        t0 = time.time()
        try:
            hist = yf.Ticker("^GSPC").history(period="1d")
            ok = not hist.empty
        except Exception:
            ok = False
        return ProviderStatus(
            provider="yfinance",
            reachable=ok,
            latency_ms=round((time.time() - t0) * 1000, 1),
            last_checked=_utcnow(),
        )
