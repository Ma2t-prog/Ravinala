"""
tests/test_fred_provider_boundaries.py

Validates:
  1. FREDAdapter.fetch_bonds() returns correct structure from mocked HTTP responses.
  2. FREDAdapter.fetch_macro() returns correct structure from mocked HTTP responses.
  3. DataFetcher.fetch_bonds() falls back to demo_static when FRED key is absent.
  4. DataFetcher.fetch_bonds() uses FRED data when FRED key is present and adapter returns data.
  5. FREDAdapter handles missing "." values and empty responses gracefully.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.providers.fred_adapter import FREDAdapter


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_obs(value: str, date: str = "2026-03-01") -> dict:
    return {"date": date, "value": value}


def _obs_list(*values) -> dict:
    """Build FRED JSON response from a list of (value, date) or just value strings."""
    obs = []
    for i, v in enumerate(values):
        month = str(i + 1).zfill(2)
        obs.append({"date": f"2026-{month}-01", "value": str(v)})
    return {"observations": obs}


# ── FREDAdapter unit tests ────────────────────────────────────────────────────

class TestFREDAdapterBonds:
    def test_fetch_bonds_returns_us_with_real_series(self):
        adapter = FREDAdapter(api_key="fake_key")

        series_map = {
            "DGS2":              _obs_list("4.10"),
            "DGS5":              _obs_list("4.15"),
            "DGS10":             _obs_list("4.22"),
            "IRLTLT01DEM156N":   _obs_list("2.47"),
            "IRLTLT01JPM156N":   _obs_list("1.05"),
            "IRLTLT01GBM156N":   _obs_list("4.98"),
            "IRLTLT01FRM156N":   _obs_list("2.98"),
            "IRLTLT01ITM156N":   _obs_list("3.60"),
        }

        def fake_get(url, params, timeout):
            sid = params["series_id"]
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = series_map.get(sid, {"observations": []})
            return resp

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            bonds = adapter.fetch_bonds()

        assert len(bonds) >= 1, "Should return at least US bond"

        us = next((b for b in bonds if b["country_code"] == "US"), None)
        assert us is not None
        assert us["yield_10y"] == pytest.approx(4.22)
        assert us["yield_2y"]  == pytest.approx(4.10)
        assert us["yield_5y"]  == pytest.approx(4.15)
        assert us["data_quality"] == "live"

        de = next((b for b in bonds if b["country_code"] == "DE"), None)
        assert de is not None
        assert de["yield_10y"] == pytest.approx(2.47)
        assert de["data_quality"] == "partial_live"

        # US spread vs Bund should be filled
        assert us["spread_vs_bund_bp"] == pytest.approx((4.22 - 2.47) * 100, abs=1)

    def test_fetch_bonds_returns_empty_when_dgs10_missing(self):
        adapter = FREDAdapter(api_key="fake_key")

        def fake_get(url, params, timeout):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"observations": [_make_obs(".")]}
            return resp

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            bonds = adapter.fetch_bonds()

        assert bonds == [], "Should return [] when DGS10 has only missing values"

    def test_fetch_bonds_skips_dot_values(self):
        adapter = FREDAdapter(api_key="fake_key")

        series_map = {
            "DGS2":  {"observations": [_make_obs("."), _make_obs("4.10")]},
            "DGS5":  {"observations": [_make_obs("4.15")]},
            "DGS10": {"observations": [_make_obs("4.22")]},
        }

        def fake_get(url, params, timeout):
            sid = params["series_id"]
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = series_map.get(sid, {"observations": []})
            return resp

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            bonds = adapter.fetch_bonds()

        us = next((b for b in bonds if b["country_code"] == "US"), None)
        assert us is not None
        assert us["yield_2y"] == pytest.approx(4.10), "Should skip '.' and use next valid value"

    def test_fetch_bonds_handles_http_error_gracefully(self):
        adapter = FREDAdapter(api_key="fake_key")

        def fake_get(url, params, timeout):
            raise Exception("Network error")

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            bonds = adapter.fetch_bonds()

        assert bonds == []


class TestFREDAdapterMacro:
    def _make_cpi_obs(self) -> dict:
        """15 monthly CPI index values for YoY computation."""
        # Simulate CPI rising from 300 to 312 over 12 months (~4% YoY)
        base = 300.0
        obs = []
        for i in range(15):
            val = base + i * 1.0
            month = str(i + 1).zfill(2)
            obs.append({"date": f"2025-{month}-01", "value": str(round(val, 2))})
        return {"observations": list(reversed(obs))}  # newest first

    def test_fetch_macro_returns_us_cpi(self):
        adapter = FREDAdapter(api_key="fake_key")

        macro_map = {
            "CPIAUCSL":          self._make_cpi_obs(),
            "UNRATE":            _obs_list("4.1", "4.2"),
            "A191RL1Q225SBEA":   _obs_list("2.5", "2.3"),
            "LRHUTTTTEZM156S":   _obs_list("6.2", "6.3"),
        }

        def fake_get(url, params, timeout):
            sid = params["series_id"]
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = macro_map.get(sid, {"observations": []})
            return resp

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            indicators = adapter.fetch_macro()

        assert len(indicators) >= 1

        cpi = next((i for i in indicators if i["indicator"] == "CPI YoY"), None)
        assert cpi is not None
        assert cpi["country"] == "USA"
        assert cpi["unit"] == "%"
        assert isinstance(cpi["latest_value"], float)
        assert cpi["sentiment"] in ("positive", "neutral", "negative")

        unemp = next((i for i in indicators if i["indicator"] == "Unemployment" and i["country"] == "USA"), None)
        assert unemp is not None
        assert unemp["latest_value"] == pytest.approx(4.1)
        assert unemp["previous_value"] == pytest.approx(4.2)

    def test_fetch_macro_returns_empty_on_all_failures(self):
        adapter = FREDAdapter(api_key="fake_key")

        def fake_get(url, params, timeout):
            raise Exception("Timeout")

        with patch("app.providers.fred_adapter.httpx.get", side_effect=fake_get):
            indicators = adapter.fetch_macro()

        assert indicators == []


# ── DataFetcher integration tests ─────────────────────────────────────────────

class TestDataFetcherFREDFallback:
    def test_fetch_bonds_demo_when_no_fred_key(self):
        """DataFetcher without FRED key must return demo_static data."""
        from app.services.data_fetcher import DataFetcher

        with patch("app.services.data_fetcher.FREDAdapter", return_value=None):
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.fred_api_key = ""
                fetcher = DataFetcher()
                fetcher._fred = None  # explicitly no FRED

        result = fetcher.fetch_bonds()

        assert result["data_quality"] == "demo_static"
        assert len(result["bonds"]) > 0
        assert "FRED_API_KEY" in result["data_quality_note"]

    def test_fetch_bonds_live_when_fred_returns_data(self):
        """DataFetcher with FRED key must use FRED data and mark data_quality=live."""
        from app.services.data_fetcher import DataFetcher

        fake_bonds = [
            {
                "country": "USA", "country_code": "US",
                "yield_2y": 4.10, "yield_5y": 4.15, "yield_10y": 4.22,
                "spread_vs_bund_bp": 175, "curve_slope_percent": 0.12,
                "direction": "up", "last_updated": "2026-03-24T10:00:00+00:00",
                "data_quality": "live", "data_quality_note": "live",
            }
        ]

        mock_fred = MagicMock()
        mock_fred.fetch_bonds.return_value = fake_bonds

        fetcher = DataFetcher.__new__(DataFetcher)
        fetcher._fred = mock_fred

        result = fetcher.fetch_bonds()

        assert result["data_quality"] == "live"
        assert result["bonds"] == fake_bonds

    def test_fetch_macro_demo_when_no_fred_key(self):
        """DataFetcher without FRED key must return demo_static macro data."""
        from app.services.data_fetcher import DataFetcher

        fetcher = DataFetcher.__new__(DataFetcher)
        fetcher._fred = None

        result = fetcher.fetch_macro()

        assert result["data_quality"] == "demo_static"
        assert len(result["indicators"]) > 0

    def test_fetch_bonds_falls_back_to_demo_on_fred_error(self):
        """DataFetcher falls back to demo_static if FRED raises an exception."""
        from app.services.data_fetcher import DataFetcher

        mock_fred = MagicMock()
        mock_fred.fetch_bonds.side_effect = RuntimeError("FRED down")

        fetcher = DataFetcher.__new__(DataFetcher)
        fetcher._fred = mock_fred

        result = fetcher.fetch_bonds()

        assert result["data_quality"] == "demo_static"

    def test_fetch_bonds_falls_back_when_fred_returns_empty(self):
        """DataFetcher falls back to demo_static if FRED returns []."""
        from app.services.data_fetcher import DataFetcher

        mock_fred = MagicMock()
        mock_fred.fetch_bonds.return_value = []

        fetcher = DataFetcher.__new__(DataFetcher)
        fetcher._fred = mock_fred

        result = fetcher.fetch_bonds()

        assert result["data_quality"] == "demo_static"
