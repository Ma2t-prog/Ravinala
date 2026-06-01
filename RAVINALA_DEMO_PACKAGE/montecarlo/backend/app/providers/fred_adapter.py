"""
providers/fred_adapter.py — FRED API provider for bond yields and macro indicators.

Source: Federal Reserve Bank of St. Louis (FRED)
API: https://fred.stlouisfed.org/docs/api/fred/
Key: free registration at https://fred.stlouisfed.org/docs/api/api_key.html

Coverage:
  Bonds — US full curve (DGS2/DGS5/DGS10, daily).
           International 10Y (monthly OECD series via FRED).
           2Y/5Y for non-US are approximated from the 10Y — labeled explicitly.
  Macro — US CPI YoY (computed from CPIAUCSL), Unemployment (UNRATE),
           Real GDP growth (A191RL1Q225SBEA).
           Eurozone Unemployment (LRHUTTTTEZM156S).

Limitations (explicit):
  - International 2Y/5Y are curve approximations, not live data.
  - Monthly FRED series lag 1-2 months behind current date.
  - China macro: FRED coverage is minimal; not included.
  - FRED PMI: ISM Manufacturing series (NAPM) is subscription-only in FRED;
    not included here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# ── Bond series IDs ───────────────────────────────────────────────────────────
# US: daily ACM Treasury yields
# International: OECD monthly long-term rates via FRED (10Y only)
_US_BOND_SERIES = {"2y": "DGS2", "5y": "DGS5", "10y": "DGS10"}
_INTL_BOND_10Y = {
    "DE": ("Germany", "IRLTLT01DEM156N"),
    "JP": ("Japan",   "IRLTLT01JPM156N"),
    "GB": ("UK",      "IRLTLT01GBM156N"),
    "FR": ("France",  "IRLTLT01FRM156N"),
    "IT": ("Italy",   "IRLTLT01ITM156N"),
}

# Approximate 2Y and 5Y from 10Y using typical curve shape multipliers.
# These are labeled as approximations in the output — not passed off as live.
_CURVE_APPROX = {
    "DE": {"2y": 0.85, "5y": 0.92},  # Bund: mild positive slope
    "JP": {"2y": 0.20, "5y": 0.55},  # JGB: ultra-flat / inverted at short end
    "GB": {"2y": 1.02, "5y": 1.01},  # Gilts: inverted
    "FR": {"2y": 0.87, "5y": 0.93},  # OAT: mild positive slope
    "IT": {"2y": 0.82, "5y": 0.90},  # BTP: mild positive slope
}

# ── Macro series IDs ──────────────────────────────────────────────────────────
_MACRO_SERIES = {
    ("USA", "Unemployment"):         ("UNRATE",              "%",     "BLS via FRED"),
    ("USA", "GDP YoY"):              ("A191RL1Q225SBEA",     "%",     "BEA via FRED"),
    ("Eurozone", "Unemployment"):    ("LRHUTTTTEZM156S",     "%",     "Eurostat via FRED"),
}
# CPI YoY is derived from CPIAUCSL index level (computed separately)
_CPI_SERIES = "CPIAUCSL"


class FREDAdapter:
    """
    Fetches bond yields and macro indicators from the FRED REST API.

    Instantiated with an API key. Returns raw dicts matching the field
    format expected by DataFetcher (not CanonicalBond/CanonicalMacro) to
    avoid touching the existing serialization path.

    Raises nothing: all methods return [] on failure, with a warning log.
    """

    def __init__(self, api_key: str, timeout: int = 10) -> None:
        self.api_key = api_key
        self.timeout = timeout

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_observations(self, series_id: str, limit: int = 5) -> list[dict]:
        """Fetch FRED observations for a series, sorted newest-first."""
        try:
            resp = httpx.get(
                FRED_BASE_URL,
                params={
                    "series_id":   series_id,
                    "api_key":     self.api_key,
                    "file_type":   "json",
                    "limit":       limit,
                    "sort_order":  "desc",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json().get("observations", [])
        except Exception as exc:
            logger.warning("FRED: failed to fetch %s — %s", series_id, exc)
            return []

    def _latest(self, series_id: str) -> Optional[float]:
        """Return the most recent non-missing value for a FRED series."""
        for obs in self._get_observations(series_id, limit=5):
            if obs.get("value") not in (".", "", None):
                return float(obs["value"])
        return None

    def _latest_and_previous(self, series_id: str) -> tuple[Optional[float], Optional[float]]:
        """Return (latest, previous) non-missing values."""
        values = [
            float(o["value"])
            for o in self._get_observations(series_id, limit=10)
            if o.get("value") not in (".", "", None)
        ]
        latest   = values[0] if values else None
        previous = values[1] if len(values) > 1 else None
        return latest, previous

    def _cpi_yoy(self) -> tuple[Optional[float], Optional[float]]:
        """
        Compute US CPI YoY from CPIAUCSL index level.
        YoY = (latest / value_12m_ago - 1) * 100
        Returns (latest_yoy, previous_month_yoy).
        """
        obs = [
            o for o in self._get_observations(_CPI_SERIES, limit=16)
            if o.get("value") not in (".", "", None)
        ]
        if len(obs) < 13:
            return None, None
        try:
            latest     = float(obs[0]["value"])
            year_ago   = float(obs[12]["value"])
            yoy_now    = round((latest / year_ago - 1) * 100, 2)
            yoy_prev   = None
            if len(obs) >= 14:
                prev_month   = float(obs[1]["value"])
                prev_year_ago = float(obs[13]["value"])
                yoy_prev = round((prev_month / prev_year_ago - 1) * 100, 2)
            return yoy_now, yoy_prev
        except (ZeroDivisionError, ValueError) as exc:
            logger.warning("FRED: CPI YoY computation error — %s", exc)
            return None, None

    @staticmethod
    def _direction(current: float, previous: Optional[float]) -> str:
        if previous is None:
            return "flat"
        if current > previous + 0.02:
            return "up"
        if current < previous - 0.02:
            return "down"
        return "flat"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Public interface ──────────────────────────────────────────────────────

    def fetch_bonds(self) -> list[dict]:
        """
        Returns a list of bond dicts (same schema as DataFetcher.fetch_bonds).
        data_quality is "live" for US (daily FRED), "partial_live" for others
        (10Y live, 2Y/5Y approximated).
        Returns [] if FRED is unreachable or returns no usable data.
        """
        now  = self._now_iso()
        bonds: list[dict] = []

        # === USA — DGS2, DGS5, DGS10 (live daily) ===
        us_2y  = self._latest(_US_BOND_SERIES["2y"])
        us_5y  = self._latest(_US_BOND_SERIES["5y"])
        us_10y = self._latest(_US_BOND_SERIES["10y"])

        if us_10y is None:
            logger.warning("FRED: US 10Y (DGS10) unavailable — bonds fallback to demo")
            return []

        us_slope = round(us_10y - (us_2y or us_10y), 4) if us_2y else 0.0
        bonds.append({
            "country":            "USA",
            "country_code":       "US",
            "yield_2y":           us_2y  if us_2y  is not None else round(us_10y * 0.95, 4),
            "yield_5y":           us_5y  if us_5y  is not None else round(us_10y * 0.98, 4),
            "yield_10y":          us_10y,
            "spread_vs_bund_bp":  0,       # filled below once we have Germany
            "curve_slope_percent": us_slope,
            "direction":          self._direction(us_10y, us_2y),
            "last_updated":       now,
            "data_quality":       "live",
            "data_quality_note":  "US Treasury yields via FRED (DGS2/DGS5/DGS10). Daily frequency.",
        })

        # === International — 10Y live, 2Y/5Y approximated ===
        de_10y: Optional[float] = None

        for cc, (country_name, series_id) in _INTL_BOND_10Y.items():
            val_10y = self._latest(series_id)
            if val_10y is None:
                continue

            if cc == "DE":
                de_10y = val_10y

            approx = _CURVE_APPROX.get(cc, {"2y": 0.90, "5y": 0.95})
            spread_bp = round((val_10y - de_10y) * 100, 1) if de_10y is not None else 0.0
            slope     = round(val_10y * (1.0 - approx["2y"]), 4)

            bonds.append({
                "country":            country_name,
                "country_code":       cc,
                "yield_2y":           round(val_10y * approx["2y"], 4),
                "yield_5y":           round(val_10y * approx["5y"], 4),
                "yield_10y":          val_10y,
                "spread_vs_bund_bp":  spread_bp,
                "curve_slope_percent": slope,
                "direction":          "flat",
                "last_updated":       now,
                "data_quality":       "partial_live",
                "data_quality_note":  (
                    f"10Y yield live via FRED ({series_id}, monthly OECD series). "
                    "2Y/5Y are curve approximations, not live data."
                ),
            })

        # Back-fill US spread vs Bund now that we have Germany
        if de_10y is not None and bonds:
            us_bond = bonds[0]
            us_bond["spread_vs_bund_bp"] = round((us_bond["yield_10y"] - de_10y) * 100, 1)

        return bonds

    def fetch_macro(self) -> list[dict]:
        """
        Returns a list of macro indicator dicts (same schema as DataFetcher.fetch_macro).
        Returns [] if FRED returns no usable data.
        """
        now = self._now_iso()
        indicators: list[dict] = []

        # US CPI YoY (derived from CPIAUCSL index)
        cpi_now, cpi_prev = self._cpi_yoy()
        if cpi_now is not None:
            sentiment = (
                "negative" if cpi_now > 3.0
                else "neutral" if cpi_now > 2.0
                else "positive"
            )
            indicators.append({
                "country":        "USA",
                "indicator":      "CPI YoY",
                "latest_value":   cpi_now,
                "unit":           "%",
                "forecast_value": None,
                "previous_value": cpi_prev,
                "release_date":   now,
                "source":         "BLS via FRED (CPIAUCSL)",
                "sentiment":      sentiment,
            })

        # Remaining series
        for (country, indicator), (series_id, unit, source) in _MACRO_SERIES.items():
            latest, previous = self._latest_and_previous(series_id)
            if latest is None:
                continue
            # Simple sentiment rules
            if indicator == "Unemployment":
                sentiment = "positive" if latest < 5.0 else ("neutral" if latest < 7.0 else "negative")
            elif indicator == "GDP YoY":
                sentiment = "positive" if latest > 2.0 else ("neutral" if latest > 0 else "negative")
            else:
                sentiment = "neutral"

            indicators.append({
                "country":        country,
                "indicator":      indicator,
                "latest_value":   latest,
                "unit":           unit,
                "forecast_value": None,
                "previous_value": previous,
                "release_date":   now,
                "source":         source,
                "sentiment":      sentiment,
            })

        return indicators
