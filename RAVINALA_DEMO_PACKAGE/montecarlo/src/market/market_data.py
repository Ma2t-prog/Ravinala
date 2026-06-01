"""
Ravinala by TSIVAHINY Matthias — Free Market Data Integration.
Zero-config live data: yfinance (equities, options, rates) + ECB REST API (EUR).
"""

import numpy as np
import pandas as pd
import requests
from typing import Optional, Dict, Tuple

from genesix.utils.quant_conventions import (
    ANNUALIZATION_FACTOR_VOL,
)
from genesix.utils.rate_policy import (
    RateQuote,
    live_rate_quote,
    policy_rate_quote,
)


RiskFreeRateQuote = RateQuote

# Key market instruments for the overview page
OVERVIEW_TICKERS: Dict[str, str] = {
    "^GSPC":     "S&P 500",
    "^NDX":      "Nasdaq 100",
    "^STOXX50E": "Euro Stoxx 50",
    "^FTSE":     "FTSE 100",
    "^N225":     "Nikkei 225",
    "^VIX":      "VIX",
    "GC=F":      "Gold",
    "CL=F":      "WTI Crude",
    "EURUSD=X":  "EUR/USD",
    "GBPUSD=X":  "GBP/USD",
    "^IRX":      "US 13W T-Bill",
    "^TNX":      "US 10Y Yield",
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. SPOT / HIST-VOL / DIVIDEND
# ─────────────────────────────────────────────────────────────────────────────

def fetch_spot_vol_div(ticker: str, vol_period: str = "1y") -> Dict:
    """
    Fetch spot price, 1-year annualized historical volatility, and dividend yield.

    Returns
    -------
    dict with keys: spot, hist_vol, div_yield, name, quote_type, error
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper().strip())
        fast = t.fast_info

        spot = fast.last_price
        if not spot or spot <= 0:
            return {"error": f"No price data for '{ticker}'"}

        hist = t.history(period=vol_period)
        if hist.empty:
            return {"error": f"No price history for '{ticker}'"}

        returns = hist["Close"].pct_change().dropna()
        hist_vol = float(returns.std() * ANNUALIZATION_FACTOR_VOL)

        try:
            info = t.info
            div_yield  = float(info.get("dividendYield") or 0.0)
            name       = info.get("longName", ticker.upper())
            quote_type = info.get("quoteType", "")
        except Exception:
            div_yield  = 0.0
            name       = ticker.upper()
            quote_type = ""

        return {
            "spot":       round(spot, 4),
            "hist_vol":   round(hist_vol, 4),
            "div_yield":  round(div_yield, 4),
            "name":       name,
            "quote_type": quote_type,
            "error":      None,
        }

    except Exception as exc:
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# 2. ATM IMPLIED VOLATILITY
# ─────────────────────────────────────────────────────────────────────────────

def fetch_atm_implied_vol(ticker: str) -> Optional[float]:
    """
    Fetch ATM implied volatility from the second-nearest options expiry.
    Returns float (e.g. 0.25) or None if unavailable.
    """
    try:
        import yfinance as yf

        t    = yf.Ticker(ticker.upper().strip())
        exps = t.options
        if not exps:
            return None

        spot   = t.fast_info.last_price
        expiry = exps[min(1, len(exps) - 1)]        # second expiry is more liquid
        calls  = t.option_chain(expiry).calls.copy()

        calls = calls[calls["impliedVolatility"] > 0.005]
        if calls.empty:
            return None

        atm_idx = (calls["strike"] - spot).abs().idxmin()
        iv = float(calls.loc[atm_idx, "impliedVolatility"])
        return round(iv, 4) if iv > 0 else None

    except Exception:
        return None


def fetch_vol_surface(ticker: str, n_expiries: int = 6) -> Optional[pd.DataFrame]:
    """
    Build a mini implied-vol surface: (strike / spot, expiry) → IV.
    Returns a DataFrame indexed by strike_ratio, columns = expiry strings.
    """
    try:
        import yfinance as yf

        t    = yf.Ticker(ticker.upper().strip())
        exps = t.options[:n_expiries]
        spot = t.fast_info.last_price

        frames = {}
        for exp in exps:
            calls = t.option_chain(exp).calls
            calls = calls[(calls["impliedVolatility"] > 0.005) & (calls["volume"] > 0)]
            if calls.empty:
                continue
            calls = calls.set_index("strike")["impliedVolatility"]
            frames[exp] = calls

        if not frames:
            return None

        surface = pd.DataFrame(frames)
        surface.index = (surface.index / spot).round(3)   # moneyness K/S
        surface.index.name = "Moneyness (K/S)"
        surface = surface.dropna(how="all").sort_index()
        return surface

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3. RISK-FREE RATES
# ─────────────────────────────────────────────────────────────────────────────

def fetch_risk_free_rate_quote(currency: str) -> RiskFreeRateQuote:
    """
    Fetch risk-free rate with explicit provenance metadata.

    The returned quote is the authoritative policy object for UI and analytics.
    Legacy callers can still use `fetch_risk_free_rate(...)`.
    """
    ccy = (currency or "USD").upper().strip()

    # ── USD: 13-week T-Bill ──────────────────────────────────────────────────
    if ccy == "USD":
        try:
            import yfinance as yf

            rate = yf.Ticker("^IRX").fast_info.last_price / 100
            if 0 < rate < 0.25:
                return live_rate_quote(
                    ccy,
                    round(float(rate), 5),
                    "US 13W T-Bill (^IRX, live)",
                )
        except Exception:
            pass
        return policy_rate_quote(ccy)

    # ── EUR: €STER via ECB REST API (no key needed) ──────────────────────────
    if ccy == "EUR":
        try:
            url = (
                "https://data-api.ecb.europa.eu/service/data/EST/"
                "B.EU000A2X2A25.WT?lastNObservations=1&format=jsondata"
            )
            r = requests.get(url, timeout=7, headers={"Accept": "application/json"})
            val = r.json()["dataSets"][0]["series"]["0:0:0"]["observations"]["0"][0]
            rate = float(val) / 100
            if 0 < rate < 0.20:
                return live_rate_quote(
                    ccy,
                    round(float(rate), 5),
                    "€STER (ECB, live)",
                )
        except Exception:
            pass
        return policy_rate_quote(ccy)

    # ── GBP: SONIA via Bank of England ───────────────────────────────────────
    if ccy == "GBP":
        try:
            url = (
                "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"
                "?CodeVer=new&xml.x=yes&Datefrom=01/Jan/2025&Dateto=now"
                "&SeriesCodes=IUDSOIA&CSVF=TT&UsingCodes=Y"
            )
            r = requests.get(url, timeout=7)
            rows = [ln for ln in r.text.strip().split("\n") if ln and not ln.startswith("DATE")]
            if rows:
                rate = float(rows[-1].split(",")[-1].strip()) / 100
                if 0 < rate < 0.20:
                    return live_rate_quote(
                        ccy,
                        round(float(rate), 5),
                        "SONIA (BOE, live)",
                    )
        except Exception:
            pass
        return policy_rate_quote(ccy)

    # ── JPY: BOJ policy rate (static — near zero) ────────────────────────────
    if ccy == "JPY":
        return policy_rate_quote(ccy)

    return policy_rate_quote(ccy)


def fetch_risk_free_rate(currency: str) -> Tuple[float, str]:
    """
    Fetch the current overnight/short-term risk-free rate for a currency.
    Returns (rate_decimal, source_label).
    """
    quote = fetch_risk_free_rate_quote(currency)
    return quote.rate, quote.source_label


# ─────────────────────────────────────────────────────────────────────────────
# 4. MARKET OVERVIEW SNAPSHOT
# ─────────────────────────────────────────────────────────────────────────────

def fetch_market_overview() -> Dict[str, Dict]:
    """
    Fetch a snapshot of key global indices, rates, FX, and commodities.
    Returns {ticker: {name, price, change_pct}} for each available instrument.
    """
    results: Dict[str, Dict] = {}
    try:
        import yfinance as yf

        raw = yf.download(
            list(OVERVIEW_TICKERS.keys()),
            period="5d",
            progress=False,
            auto_adjust=True,
        )
        close = raw["Close"]

        for tkr, name in OVERVIEW_TICKERS.items():
            try:
                series = close[tkr].dropna()
                if len(series) >= 2:
                    price = float(series.iloc[-1])
                    prev  = float(series.iloc[-2])
                    chg   = (price - prev) / prev * 100
                    results[tkr] = {"name": name, "price": price, "change_pct": chg}
            except Exception:
                pass

    except Exception:
        pass

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 5. PRICE HISTORY FOR CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def fetch_price_history(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV history for a ticker. Returns DataFrame or None.
    Uses Ticker.history() which returns single-level columns (yfinance-version safe).
    """
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker.upper().strip()).history(period=period)
        return hist if not hist.empty else None
    except Exception:
        return None
