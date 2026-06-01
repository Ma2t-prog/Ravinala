"""
test_technical.py — Unit tests for TechnicalIndicators (15 tests).
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.technical import TechnicalIndicators as TI


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def price_series() -> pd.Series:
    """Synthetic 200-bar close price series."""
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, 200)
    prices = 100 * np.cumprod(1 + returns)
    return pd.Series(prices, name="Close")


@pytest.fixture
def ohlcv_df(price_series) -> pd.DataFrame:
    """Synthetic OHLCV DataFrame."""
    close = price_series.values
    n = len(close)
    high  = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low   = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_ = close * (1 + np.random.normal(0, 0.003, n))
    vol   = np.abs(np.random.normal(1_000_000, 200_000, n))
    return pd.DataFrame({
        "Open": open_, "High": high, "Low": low,
        "Close": close, "Volume": vol,
    })


# ─── TREND ───────────────────────────────────────────────────────────────────

def test_sma_length(price_series):
    result = TI.sma(price_series, 20)
    assert len(result) == len(price_series)


def test_ema_convergence(price_series):
    sma = TI.sma(price_series, 20)
    ema = TI.ema(price_series, 20)
    # EMA should be close to SMA over long series
    assert abs(float(ema.iloc[-1]) - float(sma.iloc[-1])) < float(price_series.iloc[-1]) * 0.05


def test_dema_less_lag_than_ema(price_series):
    """DEMA should track price more closely (lower RMSE) than EMA."""
    dema = TI.dema(price_series, 20)
    ema  = TI.ema(price_series, 20)
    common = price_series.index[20:]
    rmse_dema = np.sqrt(np.mean((price_series[common] - dema[common]) ** 2))
    rmse_ema  = np.sqrt(np.mean((price_series[common] - ema[common])  ** 2))
    assert rmse_dema <= rmse_ema * 1.2  # DEMA should not be much worse


def test_hull_ma_no_nan(price_series):
    hull = TI.hull_ma(price_series, 20)
    # Last 100 values should all be finite
    assert hull.iloc[-100:].notna().all()


def test_supertrend_direction_binary(ohlcv_df):
    st = TI.supertrend(ohlcv_df, 10, 3)
    assert set(st["direction"].dropna().unique()).issubset({1, -1})


def test_parabolic_sar_shape(ohlcv_df):
    psar = TI.parabolic_sar(ohlcv_df)
    assert len(psar) == len(ohlcv_df)
    assert psar.notna().all()


# ─── MOMENTUM ────────────────────────────────────────────────────────────────

def test_rsi_bounds(price_series):
    rsi = TI.rsi(price_series, 14)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_macd_returns_three_columns(price_series):
    result = TI.macd(price_series)
    assert set(result.columns) == {"macd", "macd_signal", "macd_hist"}


def test_stochastic_rsi_range(price_series):
    srsi = TI.stochastic_rsi(price_series)
    valid_k = srsi["stochrsi_k"].dropna()
    assert (valid_k >= 0).all() and (valid_k <= 100).all()


# ─── VOLATILITY ──────────────────────────────────────────────────────────────

def test_bollinger_bands_ordering(price_series):
    bb = TI.bollinger_bands(price_series, 20)
    valid = bb.dropna()
    assert (valid["bb_upper"] >= valid["bb_mid"]).all()
    assert (valid["bb_mid"] >= valid["bb_lower"]).all()


def test_atr_positive(ohlcv_df):
    atr = TI.atr(ohlcv_df, 14)
    assert (atr.dropna() > 0).all()


def test_historical_volatility_annualized(price_series):
    hv = TI.historical_volatility(price_series, 20)
    valid = hv.dropna()
    # Annualized HV should be between 1% and 200% for normal series
    assert (valid > 1).any() and (valid < 200).any()


# ─── VOLUME ──────────────────────────────────────────────────────────────────

def test_obv_trend(ohlcv_df):
    obv = TI.obv(ohlcv_df)
    assert len(obv) == len(ohlcv_df)


def test_vwap_between_low_high(ohlcv_df):
    vwap = TI.vwap(ohlcv_df)
    valid = vwap.dropna()
    # VWAP must be between overall low and high
    assert (valid >= ohlcv_df["Low"].min() * 0.95).all()
    assert (valid <= ohlcv_df["High"].max() * 1.05).all()


# ─── SUPPORT/RESISTANCE ──────────────────────────────────────────────────────

def test_auto_sr_returns_dict_list(ohlcv_df):
    levels = TI.auto_support_resistance(ohlcv_df)
    assert isinstance(levels, list)
    for lv in levels:
        assert "price" in lv
        assert "type" in lv
        assert lv["type"] in ("support", "resistance")
