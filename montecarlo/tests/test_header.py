"""
tests/test_header.py — Unit tests for global_header.py
"""
import sys
import types
from datetime import datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# ── Stub streamlit so global_header.py imports cleanly ──────────
st_mock = types.ModuleType("streamlit")
st_mock.cache_data = lambda **kw: (lambda f: f)
sys.modules.setdefault("streamlit", st_mock)

import pandas as pd

sys.path.insert(0, "src")
from global_header import (
    MarketAlertEngine,
    MarketHeatStrip,
    MarketPulseTicker,
    MarketSession,
    SessionTimeline,
    WorldMarketClocks,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _nyse() -> MarketSession:
    return WorldMarketClocks.MARKETS[0]  # NYSE


def _tse() -> MarketSession:
    """Tokyo Stock Exchange — has lunch break."""
    return next(m for m in WorldMarketClocks.MARKETS if m.name == "TSE")


def _now_at(market: MarketSession, h: int, m: int = 0, weekday: int = 1) -> datetime:
    """Return a datetime in the market's timezone at given hour:min on a weekday."""
    tz = ZoneInfo(market.timezone)
    base = datetime(2024, 1, 2, h, m, 0, tzinfo=tz)  # Tuesday 2024-01-02
    # shift to desired weekday (0=Mon)
    delta = (weekday - base.weekday()) % 7
    return base + timedelta(days=delta)


# ─────────────────────────────────────────────
# WorldMarketClocks — status tests
# ─────────────────────────────────────────────

class TestWorldMarketClocks:
    clocks = WorldMarketClocks()

    def test_open_status(self):
        nyse = _nyse()
        now = _now_at(nyse, 10, 0)  # 10:00 NYSE = well inside session
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "OPEN"

    def test_open_progress_mid_session(self):
        nyse = _nyse()
        # NYSE opens 9:30, closes 16:00 → mid = ~12:45
        now = _now_at(nyse, 12, 45)
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "OPEN"
        assert 0.3 < s["session_progress_pct"] < 0.7

    def test_progress_zero_at_open(self):
        nyse = _nyse()
        now = _now_at(nyse, 9, 30)
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "OPEN"
        assert s["session_progress_pct"] == pytest.approx(0.0, abs=0.02)

    def test_progress_near_one_at_close(self):
        nyse = _nyse()
        now = _now_at(nyse, 15, 58)  # 2 min before close
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "OPEN"
        assert s["session_progress_pct"] > 0.99

    def test_pre_market_status(self):
        nyse = _nyse()
        now = _now_at(nyse, 7, 0)  # 07:00 = pre-market (opens 9:30)
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "PRE-MARKET"
        assert s["session_progress_pct"] is None

    def test_post_market_status(self):
        nyse = _nyse()
        now = _now_at(nyse, 17, 0)  # after 16:00 close, before 20:00 post end
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "POST-MARKET"

    def test_closed_before_pre_market(self):
        nyse = _nyse()
        now = _now_at(nyse, 1, 0)  # 01:00 — before pre-market
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "CLOSED"

    def test_closed_after_post_market(self):
        nyse = _nyse()
        now = _now_at(nyse, 22, 0)  # after 20:00 post-market end
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "CLOSED"

    def test_weekend_status(self):
        nyse = _nyse()
        now = _now_at(nyse, 10, 0, weekday=5)  # Saturday
        s = self.clocks.get_market_status(nyse, _now=now)
        assert s["status"] == "WEEKEND"
        assert s["session_progress_pct"] is None

    def test_lunch_break_tse(self):
        tse = _tse()
        now = _now_at(tse, 12, 0)  # 12:00 = TSE lunch (11:30–12:30)
        s = self.clocks.get_market_status(tse, _now=now)
        assert s["status"] == "LUNCH"

    def test_tse_open_morning(self):
        tse = _tse()
        now = _now_at(tse, 10, 0)  # before lunch
        s = self.clocks.get_market_status(tse, _now=now)
        assert s["status"] == "OPEN"

    def test_tse_open_afternoon(self):
        tse = _tse()
        now = _now_at(tse, 13, 30)  # after lunch
        s = self.clocks.get_market_status(tse, _now=now)
        assert s["status"] == "OPEN"

    def test_get_all_statuses_returns_all_markets(self):
        statuses = self.clocks.get_all_statuses()
        assert len(statuses) == len(WorldMarketClocks.MARKETS)

    def test_get_all_statuses_open_first(self):
        """At least verify no CLOSED market appears before an OPEN one (when there are both)."""
        statuses = self.clocks.get_all_statuses()
        order_map = {"OPEN": 0, "PRE-MARKET": 1, "LUNCH": 2, "POST-MARKET": 3,
                     "CLOSED": 4, "WEEKEND": 5, "HOLIDAY": 6}
        levels = [order_map[s["status"]] for s in statuses]
        assert levels == sorted(levels)

    def test_next_event_string_not_empty(self):
        statuses = self.clocks.get_all_statuses()
        for s in statuses:
            assert isinstance(s["next_event"], str)
            assert len(s["next_event"]) > 0

    def test_status_colors_present(self):
        statuses = self.clocks.get_all_statuses()
        for s in statuses:
            assert s["status_color"].startswith("#")

    def test_session_overlap_matrix_keys(self):
        ov = self.clocks.get_session_overlap_matrix()
        assert "liquidity_level" in ov
        assert ov["liquidity_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_open_str_format(self):
        statuses = self.clocks.get_all_statuses()
        for s in statuses:
            parts = s["open_str"].split(":")
            assert len(parts) == 2
            assert parts[0].isdigit() and parts[1].isdigit()


# ─────────────────────────────────────────────
# MarketHeatStrip — color & sentiment tests
# ─────────────────────────────────────────────

class TestMarketHeatStrip:
    strip = MarketHeatStrip()

    def _prices(self, sym: str, pct: float) -> dict:
        return {sym: (100 * (1 + pct / 100), 100.0)}

    def test_strong_up_color(self):
        color = self.strip._color_for_pct(3.0)
        assert color == "#00C853"

    def test_up_color(self):
        color = self.strip._color_for_pct(1.0)
        assert color == "#66BB6A"

    def test_flat_color(self):
        color = self.strip._color_for_pct(0.05)
        assert color == "#616161"

    def test_down_color(self):
        color = self.strip._color_for_pct(-1.0)
        assert color == "#EF5350"

    def test_strong_down_color(self):
        color = self.strip._color_for_pct(-3.0)
        assert color == "#FF1744"

    def test_vix_inverted_up_is_red(self):
        """VIX +3% should be red (inverted)."""
        color = self.strip._color_for_pct(3.0, inverted=True)
        assert color == "#FF1744"

    def test_vix_inverted_down_is_green(self):
        color = self.strip._color_for_pct(-3.0, inverted=True)
        assert color == "#00C853"

    def test_compute_heat_with_mock_prices(self):
        prices = {sym: (101.0, 100.0) for sym in MarketHeatStrip.HEAT_INSTRUMENTS}
        cells = self.strip.compute_heat(_prices=prices)
        assert len(cells) == len(MarketHeatStrip.HEAT_INSTRUMENTS)
        for c in cells:
            assert "heat_color" in c
            assert "change_pct" in c
            assert abs(c["change_pct"] - 1.0) < 0.001

    def test_sentiment_risk_on(self):
        cells = [{"symbol": "^GSPC", "change_pct": 3.0, "label": "S&P", "last": 5000}]
        sent = self.strip.compute_global_sentiment(cells)
        assert sent["label"] in ("RISK ON", "CAUTIOUS", "NEUTRAL")  # positive score

    def test_sentiment_panic(self):
        cells = [{"symbol": s, "change_pct": -5.0, "label": s, "last": 100}
                 for s in ["^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^FCHI",
                            "^GDAXI", "^FTSE", "^N225"]]
        sent = self.strip.compute_global_sentiment(cells)
        assert sent["score"] < 0

    def test_sentiment_has_required_keys(self):
        cells = [{"symbol": "^GSPC", "change_pct": 0.5, "label": "S&P", "last": 5000}]
        sent = self.strip.compute_global_sentiment(cells)
        for k in ("score", "label", "color", "emoji", "description"):
            assert k in sent

    def test_sentiment_score_bounded(self):
        cells = [{"symbol": "^GSPC", "change_pct": 999.0, "label": "S&P", "last": 99999}]
        sent = self.strip.compute_global_sentiment(cells)
        assert -100 <= sent["score"] <= 100


# ─────────────────────────────────────────────
# MarketAlertEngine
# ─────────────────────────────────────────────

class TestMarketAlertEngine:
    def _engine(self):
        e = MarketAlertEngine()
        e._cooldown = {}  # reset per test
        return e

    def _data(self, vix_val=15, vix_pct=0, btc_val=50000, btc_pct=0,
              gspc_pct=0, wti_val=80, wti_pct=0):
        heat = [
            {"symbol": "^VIX",   "label": "VIX",  "change_pct": vix_pct,
             "last": vix_val,  "heat_color": "#fff", "heat_level": "flat", "tooltip": ""},
            {"symbol": "^GSPC",  "label": "S&P",  "change_pct": gspc_pct,
             "last": 5000,     "heat_color": "#fff", "heat_level": "flat", "tooltip": ""},
        ]
        ticker = [
            {"symbol": "^VIX",   "name": "VIX",   "icon": "⚡", "last": vix_val,
             "change_pct": vix_pct,  "change_net": 0, "direction": "up"},
            {"symbol": "BTC-USD","name": "BTC",   "icon": "₿", "last": btc_val,
             "change_pct": btc_pct,  "change_net": 0, "direction": "flat"},
            {"symbol": "CL=F",   "name": "WTI",   "icon": "🛢️","last": wti_val,
             "change_pct": wti_pct,  "change_net": 0, "direction": "flat"},
        ]
        return {"heat_cells": heat, "ticker_data": ticker, "calendar": [], "clock_statuses": []}

    def test_vix_spike_alert(self):
        eng = self._engine()
        alerts = eng.scan_alerts(self._data(vix_val=32, vix_pct=6))
        cats = [a["category"] for a in alerts]
        assert "VOL" in cats

    def test_vix_extreme_alert(self):
        eng = self._engine()
        alerts = eng.scan_alerts(self._data(vix_val=45, vix_pct=20))
        critical = [a for a in alerts if a["level"] == "CRITICAL"]
        assert len(critical) >= 1

    def test_no_alert_low_vix(self):
        eng = self._engine()
        alerts = eng.scan_alerts(self._data(vix_val=15))
        vol_alerts = [a for a in alerts if a["category"] == "VOL"]
        assert len(vol_alerts) == 0

    def test_btc_100k_alert(self):
        eng = self._engine()
        alerts = eng.scan_alerts(self._data(btc_val=105000))
        cats = [a["category"] for a in alerts]
        assert "CRYPTO" in cats

    def test_large_equity_mover_alert(self):
        eng = self._engine()
        data = self._data(gspc_pct=4.0)
        alerts = eng.scan_alerts(data)
        assert any(a["category"] == "EQUITY" for a in alerts)

    def test_max_5_alerts(self):
        eng = self._engine()
        data = self._data(vix_val=45, vix_pct=20, gspc_pct=5, btc_pct=-8, wti_val=110, wti_pct=6)
        alerts = eng.scan_alerts(data)
        assert len(alerts) <= 5

    def test_critical_before_warning(self):
        eng = self._engine()
        data = self._data(vix_val=45, vix_pct=20, gspc_pct=4)
        alerts = eng.scan_alerts(data)
        if len(alerts) >= 2:
            order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
            levels = [order[a["level"]] for a in alerts]
            assert levels == sorted(levels)

    def test_cooldown_prevents_duplicate(self):
        eng = self._engine()
        data = self._data(vix_val=35, vix_pct=8)
        alerts1 = eng.scan_alerts(data)
        alerts2 = eng.scan_alerts(data)
        vol1 = sum(1 for a in alerts1 if a["category"] == "VOL")
        vol2 = sum(1 for a in alerts2 if a["category"] == "VOL")
        assert vol2 == 0  # cooldown blocks repeat

    def test_oil_above_100_alert(self):
        eng = self._engine()
        alerts = eng.scan_alerts(self._data(wti_val=105))
        assert any(a["category"] == "COMMODITY" for a in alerts)

    def test_nyse_open_soon_alert(self):
        eng = self._engine()
        clock_status = [{
            "name": "NYSE", "status": "PRE-MARKET",
            "time_to_open": timedelta(minutes=10),
            "time_to_close": None, "flag": "🇺🇸",
        }]
        data = {**self._data(), "clock_statuses": clock_status}
        alerts = eng.scan_alerts(data)
        assert any(a["category"] == "SESSION" and "NYSE" in a["message"] for a in alerts)


# ─────────────────────────────────────────────
# SessionTimeline
# ─────────────────────────────────────────────

class TestSessionTimeline:
    tl = SessionTimeline()

    def test_generate_returns_dict(self):
        data = self.tl.generate_timeline_data()
        assert isinstance(data, dict)
        assert "markets" in data
        assert "current_time_utc" in data

    def test_all_markets_present(self):
        data = self.tl.generate_timeline_data()
        names = {m["market_name"] for m in data["markets"]}
        expected = {m.name for m in WorldMarketClocks.MARKETS}
        assert names == expected

    def test_current_time_utc_range(self):
        data = self.tl.generate_timeline_data()
        assert 0 <= data["current_time_utc"] < 24

    def test_segments_have_required_keys(self):
        data = self.tl.generate_timeline_data()
        for m in data["markets"]:
            for seg in m["segments"]:
                assert "start" in seg
                assert "end" in seg
                assert seg["type"] in ("pre", "open", "lunch", "post")

    def test_segment_hours_in_range(self):
        data = self.tl.generate_timeline_data()
        for m in data["markets"]:
            for seg in m["segments"]:
                assert 0 <= seg["start"] < 24
                assert 0 <= seg["end"] < 24

    def test_is_open_now_is_bool(self):
        data = self.tl.generate_timeline_data()
        for m in data["markets"]:
            assert isinstance(m["is_open_now"], bool)
