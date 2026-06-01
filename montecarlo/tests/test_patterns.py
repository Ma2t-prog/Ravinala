"""
test_patterns.py — Unit tests for PatternDetector (10 tests).
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.patterns import PatternDetector, PatternResult


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def flat_df() -> pd.DataFrame:
    """200-bar flat price (no strong patterns)."""
    np.random.seed(7)
    n = 200
    price = 100.0 + np.cumsum(np.random.normal(0, 0.5, n))
    return pd.DataFrame({
        "Open":   price + np.random.normal(0, 0.3, n),
        "High":   price + np.abs(np.random.normal(0, 0.8, n)),
        "Low":    price - np.abs(np.random.normal(0, 0.8, n)),
        "Close":  price,
        "Volume": np.abs(np.random.normal(500_000, 50_000, n)),
    })


@pytest.fixture
def bullish_engulfing_df() -> pd.DataFrame:
    """DataFrame ending with a clear bullish engulfing pattern (needs ≥ 3 rows for detect_all)."""
    rows = [
        {"Open": 103.0, "High": 104.0, "Low": 102.0, "Close": 103.5, "Volume": 1e6},  # neutral
        {"Open": 102.0, "High": 103.5, "Low": 101.5, "Close": 101.0, "Volume": 1e6},  # bearish
        {"Open": 100.0, "High": 104.5, "Low": 99.5,  "Close": 104.0, "Volume": 1.5e6},  # engulfs
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def doji_df() -> pd.DataFrame:
    """DataFrame ending with a doji candle (needs ≥ 3 rows for detect_all)."""
    rows = [
        {"Open": 99.0,  "High": 100.5, "Low": 98.5,  "Close": 99.5,  "Volume": 1e6},
        {"Open": 99.5,  "High": 100.0, "Low": 99.0,  "Close": 99.8,  "Volume": 1e6},
        {"Open": 100.0, "High": 103.0, "Low": 97.0,  "Close": 100.02, "Volume": 1e6},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def morning_star_df() -> pd.DataFrame:
    """Three-candle morning star pattern."""
    rows = [
        {"Open": 105.0, "High": 105.5, "Low": 101.0, "Close": 101.5, "Volume": 1e6},  # bearish
        {"Open": 101.0, "High": 101.8, "Low": 100.5, "Close": 101.2, "Volume": 0.5e6},  # doji
        {"Open": 101.5, "High": 106.0, "Low": 101.0, "Close": 105.8, "Volume": 1.5e6},  # bullish
    ]
    return pd.DataFrame(rows)


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_detect_all_returns_list(flat_df):
    det = PatternDetector()
    result = det.detect_all(flat_df)
    assert isinstance(result, list)


def test_detect_all_sorted_by_confidence(flat_df):
    det = PatternDetector()
    result = det.detect_all(flat_df)
    confs = [r.confidence for r in result]
    assert confs == sorted(confs, reverse=True)


def test_bullish_engulfing_detected(bullish_engulfing_df):
    det = PatternDetector()
    result = det.detect_all(bullish_engulfing_df)
    names = [r.pattern for r in result]
    assert "Bullish Engulfing" in names


def test_doji_detected(doji_df):
    det = PatternDetector()
    result = det.detect_all(doji_df)
    names = [r.pattern for r in result]
    assert any("Doji" in n for n in names)


def test_morning_star_detected(morning_star_df):
    det = PatternDetector()
    result = det.detect_all(morning_star_df)
    names = [r.pattern for r in result]
    assert "Morning Star" in names


def test_pattern_result_fields(flat_df):
    det = PatternDetector()
    result = det.detect_all(flat_df)
    if result:
        r = result[0]
        assert 0.0 <= r.confidence <= 1.0
        assert r.bias in ("Bullish", "Bearish", "Neutral")
        assert r.strength in ("Weak", "Moderate", "Strong")
        assert isinstance(r.description, str)


def test_chart_patterns_returns_list(flat_df):
    det = PatternDetector()
    result = det.detect_chart_patterns(flat_df)
    assert isinstance(result, list)


def test_divergence_detection(flat_df):
    det = PatternDetector()
    result = det.detect_divergences(flat_df, "RSI")
    assert isinstance(result, list)


def test_detect_all_with_chart_combines(flat_df):
    det = PatternDetector()
    result = det.detect_all_with_chart(flat_df)
    # At least returns a list (may be empty for random data)
    assert isinstance(result, list)


def test_no_crash_on_short_series():
    det = PatternDetector()
    short_df = pd.DataFrame({
        "Open": [100.0], "High": [102.0], "Low": [99.0],
        "Close": [101.0], "Volume": [1e6],
    })
    result = det.detect_all(short_df)
    assert isinstance(result, list)
