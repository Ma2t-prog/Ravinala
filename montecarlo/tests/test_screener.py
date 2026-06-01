"""
test_screener.py — Unit tests for StockScreener (5 tests).
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.screener import StockScreener, PRESET_SCREENS


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_preset_screens_defined():
    """All expected preset screens must be present."""
    expected = [
        "oversold_quality", "breakout_candidates", "value_plays",
        "dividend_champions", "momentum_leaders",
    ]
    for key in expected:
        assert key in PRESET_SCREENS, f"Missing preset: {key}"


def test_filter_application_pass():
    """A row that satisfies all filters should pass."""
    screener = StockScreener()
    row = {
        "rsi_14": 28.0,
        "market_cap": 5e9,
        "pe_ratio": 18.0,
        "price_above_sma200": True,
    }
    filters = {
        "rsi_14": {"max": 35},
        "market_cap": {"min": 1e9},
        "price_above_sma200": True,
    }
    assert screener._apply_filter(row, filters) is True


def test_filter_application_fail():
    """A row that violates one filter should fail."""
    screener = StockScreener()
    row = {
        "rsi_14": 65.0,   # exceeds max 35
        "market_cap": 5e9,
    }
    filters = {"rsi_14": {"max": 35}}
    assert screener._apply_filter(row, filters) is False


def test_filter_missing_key_fails():
    """A row missing a required filter key should fail."""
    screener = StockScreener()
    row = {"market_cap": 5e9}  # no rsi_14
    filters = {"rsi_14": {"max": 35}}
    assert screener._apply_filter(row, filters) is False


def test_get_universe_returns_list():
    """get_universe should return a non-empty list for known universe names."""
    screener = StockScreener()
    for name in ["nasdaq100", "cac40", "eurostoxx50"]:
        result = screener.get_universe(name)
        assert isinstance(result, list)
        assert len(result) > 0, f"Universe '{name}' is empty"


def test_screen_empty_universe():
    """Screening an empty universe should return an empty DataFrame."""
    screener = StockScreener()
    result = screener.screen([], {"rsi_14": {"max": 40}})
    assert isinstance(result, pd.DataFrame)
    assert result.empty
