"""
ml/features.py — Feature engineering from price data.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Builds a standard feature matrix from OHLCV price series.
All features are backward-looking — no future leakage.

Features:
  - Returns (1d, 5d, 21d)
  - Volatility (5d, 21d, 63d realised)
  - Momentum (RSI-14, MACD signal, rate-of-change)
  - Moving-average crossovers (SMA 20/50)
  - Volume ratio (vs 20d avg)
  - Day-of-week, month-of-year (cyclical encoding)
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass

# ── ML feature constants ────────────────────────────────────────────────────
# These values mirror CONVENTIONS (app.risk.conventions.QuantConventions).
# They are defined here as named constants so this module can be imported in
# test/standalone contexts without pulling in the full pydantic settings chain.
# Any deviation from CONVENTIONS must be explicit — see test_quant_conventions.py.
_ANN_FACTOR_VOL: float = 252 ** 0.5   # CONVENTIONS.ann_factor_vol
_VOL_WINDOWS = (5, 21, 63)            # CONVENTIONS.ml_vol_windows
_RSI_PERIOD: int = 14                  # CONVENTIONS.ml_rsi_period
_MACD_FAST: int = 12                   # CONVENTIONS.ml_macd_fast
_MACD_SLOW: int = 26                   # CONVENTIONS.ml_macd_slow
_MACD_SIGNAL: int = 9                  # CONVENTIONS.ml_macd_signal
_ROC_PERIOD: int = 10                  # CONVENTIONS.ml_roc_period
_SMA_SHORT: int = 20                   # CONVENTIONS.ml_sma_short
_SMA_LONG: int = 50                    # CONVENTIONS.ml_sma_long
_VOLUME_MA_PERIOD: int = 20            # CONVENTIONS.ml_volume_ma_period

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE BUILDER
# ═══════════════════════════════════════════════════════════════════════════

_FEATURE_VERSION = "1.0"


def build_features(prices: pd.DataFrame, horizon_days: int = 5) -> pd.DataFrame:
    """
    Build feature matrix from OHLCV DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        Must contain columns: Close (required), Volume (optional).
        Index must be DatetimeIndex.
    horizon_days : int
        Forward return horizon used as target (default 5 trading days).

    Returns
    -------
    pd.DataFrame
        Feature matrix with columns prefixed by category
        (ret_, vol_, mom_, ma_, cal_) plus target column ``fwd_return``.
        Rows with NaN from lookback windows are dropped.
    """
    df = pd.DataFrame(index=prices.index)
    close = prices["Close"].astype(float)

    # ── Returns ──────────────────────────────────────────────────────────
    df["ret_1d"] = close.pct_change(1)
    df["ret_5d"] = close.pct_change(5)
    df["ret_21d"] = close.pct_change(21)

    # ── Realised volatility ──────────────────────────────────────────────
    log_ret = np.log(close / close.shift(1))
    df["vol_5d"] = log_ret.rolling(_VOL_WINDOWS[0]).std() * _ANN_FACTOR_VOL
    df["vol_21d"] = log_ret.rolling(_VOL_WINDOWS[1]).std() * _ANN_FACTOR_VOL
    df["vol_63d"] = log_ret.rolling(_VOL_WINDOWS[2]).std() * _ANN_FACTOR_VOL

    # ── Momentum ─────────────────────────────────────────────────────────
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(_RSI_PERIOD).mean()
    loss = (-delta.clip(upper=0)).rolling(_RSI_PERIOD).mean()
    rs = gain / loss.replace(0, np.nan)
    df["mom_rsi14"] = 100 - (100 / (1 + rs))

    # MACD
    ema_fast = close.ewm(span=_MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=_MACD_SLOW, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=_MACD_SIGNAL, adjust=False).mean()
    df["mom_macd_hist"] = macd - signal

    # Rate of change
    df["mom_roc10"] = close.pct_change(_ROC_PERIOD)

    # ── Moving-average crossovers ────────────────────────────────────────
    sma_s = close.rolling(_SMA_SHORT).mean()
    sma_l = close.rolling(_SMA_LONG).mean()
    df["ma_sma20_dist"] = (close - sma_s) / sma_s  # distance from SMA20
    df["ma_sma50_dist"] = (close - sma_l) / sma_l
    df["ma_cross_20_50"] = (sma_s > sma_l).astype(float)

    # ── Volume ratio (if available) ──────────────────────────────────────
    if "Volume" in prices.columns:
        vol = prices["Volume"].astype(float)
        vol_ma = vol.rolling(_VOLUME_MA_PERIOD).mean()
        df["vol_ratio_20d"] = vol / vol_ma.replace(0, np.nan)
    else:
        df["vol_ratio_20d"] = np.nan

    # ── Calendar features (cyclical encoding) ────────────────────────────
    if hasattr(prices.index, "dayofweek"):
        dow = prices.index.dayofweek
        df["cal_dow_sin"] = np.sin(2 * np.pi * dow / 5)
        df["cal_dow_cos"] = np.cos(2 * np.pi * dow / 5)
        moy = prices.index.month
        df["cal_month_sin"] = np.sin(2 * np.pi * moy / 12)
        df["cal_month_cos"] = np.cos(2 * np.pi * moy / 12)

    # ── Target: forward return (for training only) ───────────────────────
    df["fwd_return"] = close.pct_change(horizon_days).shift(-horizon_days)

    # Drop rows with NaN from lookback windows (keep target NaN for last rows)
    feature_cols = [c for c in df.columns if c != "fwd_return"]
    df = df.dropna(subset=feature_cols)

    logger.info(
        "Features built: %d rows, %d features, horizon=%dd, version=%s",
        len(df), len(feature_cols), horizon_days, _FEATURE_VERSION,
    )
    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Return only the feature column names (exclude target)."""
    return [c for c in df.columns if c != "fwd_return"]


def dataset_hash(df: pd.DataFrame) -> str:
    """Deterministic hash of the feature matrix for reproducibility tracking."""
    raw = pd.util.hash_pandas_object(df).values.tobytes()
    return hashlib.sha256(raw).hexdigest()[:16]
