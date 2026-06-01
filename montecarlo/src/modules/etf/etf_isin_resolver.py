"""
ISIN → Yahoo Finance ticker resolver for UCITS ETFs.

Resolution order:
  1. Local UCITS_ISIN_MAP (instant, no network)
  2. OpenFIGI API  (free, no key required for basic use)
  3. Heuristic suffix stripping  (last resort)
"""

from __future__ import annotations

import requests
import logging

logger = logging.getLogger(__name__)

# ── Hard-coded ISIN → Yahoo ticker map ───────────────────────────────────────
# Covers the most common UCITS ETFs traded on Euronext/LSE/XETRA
UCITS_ISIN_MAP: dict[str, str] = {
    # ── iShares (BlackRock) ──────────────────────────────────────────────────
    "IE00B4L5Y983": "IWDA.AS",      # Core MSCI World USD  (Euronext Amsterdam)
    "IE00B5BMR087": "CSPX.L",       # Core S&P 500 USD  (LSE)
    "IE00BKM4GZ66": "EMIM.AS",      # Core MSCI EM IMI  (Euronext)
    "IE00B4K48X80": "IMEU.AS",      # MSCI Europe  (Euronext)
    "IE0008471009": "EUE.AS",       # Euro Stoxx 50  (Euronext)
    "IE00B3F81409": "AGGG.AS",      # Global Agg Bond  (Euronext)
    "IE00BHZPJ620": "SUWS.L",       # MSCI World ESG Leaders  (LSE)
    "IE00B53SZB19": "CNDX.L",       # NASDAQ-100  (LSE)
    "IE0005042456": "ISF.L",        # Core FTSE 100  (LSE)
    "IE00B52MJD48": "SLXX.L",       # iBoxx GBP Corporate  (LSE)
    "IE00B14X4S71": "IBGX.AS",      # Euro Govt Bond 7-10Y  (Euronext)
    "IE00B4WXJJ64": "IGLO.AS",      # Core Global Govt Bond  (Euronext)
    "IE00B3RBWM25": "VWRL.AS",      # Vanguard FTSE All-World  (Euronext)
    # ── Vanguard ────────────────────────────────────────────────────────────
    "IE00B3XXRP09": "VUSA.AS",      # S&P 500  (Euronext)
    "IE00BK5BQT80": "VWCE.DE",      # FTSE All-World Acc  (XETRA)
    "IE00B18GC888": "VEUR.AS",      # FTSE Developed Europe  (Euronext)
    # ── Amundi / Lyxor ──────────────────────────────────────────────────────
    "LU1681043599": "LCWL.PA",      # MSCI World  (Euronext Paris)
    "FR0007054358": "MSE.PA",       # Euro Stoxx 50  (Euronext Paris)
    "LU0496786574": "LU0496786574.PA",  # Lyxor S&P 500
    "LU1829221024": "PANX.PA",      # NASDAQ-100 Acc  (Euronext Paris)
    # ── Xtrackers (DWS) ─────────────────────────────────────────────────────
    "LU0274208692": "XDWD.DE",      # MSCI World Swap Acc  (XETRA)
    "LU0292096186": "XMEM.DE",      # MSCI EM Swap Acc  (XETRA)
    # ── SPDR (State Street) ─────────────────────────────────────────────────
    "IE00B6YX5D40": "SPXS.L",       # S&P 500 GBP Hdg  (LSE)
    "IE00BWBXM385": "ZPRS.DE",      # Portfolio S&P 500  (XETRA)
    # ── Invesco ─────────────────────────────────────────────────────────────
    "IE00BQQP9G91": "QQQS.L",       # NASDAQ-100 Swap  (LSE)
}

# ── OpenFIGI resolver ─────────────────────────────────────────────────────────
_OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
_OPENFIGI_HEADERS = {"Content-Type": "application/json"}


def _query_openfigi(isin: str) -> str | None:
    """Query OpenFIGI for a ticker given an ISIN. Returns None on failure."""
    try:
        payload = [{"idType": "ID_ISIN", "idValue": isin}]
        resp = requests.post(
            _OPENFIGI_URL,
            json=payload,
            headers=_OPENFIGI_HEADERS,
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or "data" not in data[0]:
            return None
        # Prefer exchange-traded equity items; pick first with a ticker
        for item in data[0]["data"]:
            ticker = item.get("ticker")
            exchange = item.get("exchCode", "")
            if ticker and exchange in ("ETF", "NA", "LN", "GY", "FP", "SW"):
                # Map exchange code to Yahoo suffix
                suffix_map = {
                    "NA": ".AS", "LN": ".L", "GY": ".DE",
                    "FP": ".PA", "SW": ".SW",
                }
                suffix = suffix_map.get(exchange, "")
                return f"{ticker}{suffix}"
        # Fallback: return first ticker without suffix
        for item in data[0]["data"]:
            if item.get("ticker"):
                return item["ticker"]
    except Exception as exc:
        logger.debug("OpenFIGI lookup failed for %s: %s", isin, exc)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def resolve(isin: str, use_openfigi: bool = True) -> str | None:
    """
    Resolve an ISIN to a Yahoo Finance ticker.

    Parameters
    ----------
    isin : str
        12-character ISIN code.
    use_openfigi : bool
        Whether to fall back to the OpenFIGI API when not in local map.

    Returns
    -------
    str | None
        Yahoo Finance ticker string, or None if resolution failed.
    """
    isin = isin.strip().upper()

    # 1. Local map
    if isin in UCITS_ISIN_MAP:
        return UCITS_ISIN_MAP[isin]

    # 2. OpenFIGI
    if use_openfigi:
        ticker = _query_openfigi(isin)
        if ticker:
            logger.info("OpenFIGI resolved %s → %s", isin, ticker)
            return ticker

    logger.warning("Could not resolve ISIN %s", isin)
    return None


def is_valid_isin(isin: str) -> bool:
    """Basic structural validation: 2-letter country code + 9 alphanumeric + 1 check digit."""
    isin = isin.strip().upper()
    if len(isin) != 12:
        return False
    if not isin[:2].isalpha():
        return False
    if not isin[2:].isalnum():
        return False
    return True
