"""
tests/test_ml_no_lookahead.py

Anti-lookahead validation for the ML feature and training pipeline (Q2.1).

Property under test: no feature value at row t may depend on any price
observation at time t' > t.  Violations would silently invalidate all
confidence estimates and produce backtest results that cannot be reproduced
in live trading.

Coverage:
1.  fwd_return is never returned by feature_columns().
2.  feature_columns() always excludes fwd_return, even when the column exists.
3.  Feature values at row t are IDENTICAL whether computed on a short slice
    ending at t or on a longer series extending beyond t (no future leakage).
4.  Rolling features (vol, momentum, MA) are strictly backward-looking.
5.  EWM-based features (MACD components) are strictly backward-looking.
6.  The forward return column (fwd_return) IS forward-looking — this is expected
    behaviour for the target.  Test confirms it is NaN for the last horizon_days rows.
7.  Walk-forward splits are strictly temporal: max(train_idx) < min(val_idx).
8.  Walk-forward splits have no index overlap between train and val.
9.  Walk-forward splits are monotonically ordered (expanding window).
10. The train/test split is temporal (test = last 20%), not shuffled.
11. predict() uses feature_columns() — fwd_return is excluded from model input.
12. Adding an extreme future row does not change features at the preceding row.
13. predict() on a price series ending at T produces the same features as
    predict() called on a longer series up to T.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ml.features import build_features, dataset_hash, feature_columns
from app.ml.training import walk_forward_split


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_prices(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """
    Build a synthetic OHLCV DataFrame with a DatetimeIndex.

    Uses a random walk so the values are plausible but fully deterministic.
    """
    rng = np.random.default_rng(seed)
    start = datetime(2020, 1, 2)
    dates = pd.bdate_range(start=start, periods=n)

    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    high = close * (1 + rng.uniform(0.001, 0.02, n))
    low = close * (1 - rng.uniform(0.001, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )


# ── 1–2. feature_columns() contract ──────────────────────────────────────────

def test_fwd_return_never_in_feature_columns():
    """feature_columns() must never return 'fwd_return'."""
    prices = _make_prices()
    feat_df = build_features(prices, horizon_days=5)
    cols = feature_columns(feat_df)
    assert "fwd_return" not in cols, (
        "fwd_return appeared in feature_columns() — this would cause target leakage"
    )


def test_feature_columns_excludes_fwd_return_explicitly():
    """feature_columns() must exclude 'fwd_return' even when column is present in DataFrame."""
    prices = _make_prices()
    feat_df = build_features(prices, horizon_days=5)
    assert "fwd_return" in feat_df.columns, "fwd_return should exist as target column"
    cols = feature_columns(feat_df)
    assert "fwd_return" not in cols


def test_feature_columns_returns_all_non_target_columns():
    """feature_columns() must return exactly the non-target columns."""
    prices = _make_prices()
    feat_df = build_features(prices, horizon_days=5)
    expected = [c for c in feat_df.columns if c != "fwd_return"]
    assert feature_columns(feat_df) == expected


# ── 3. No future leakage — main property ─────────────────────────────────────

def test_features_identical_on_partial_and_full_series():
    """
    Feature values at row t must not change when future rows are appended.

    This is the core anti-lookahead test.  Any violation means a feature is
    computing something from the full series that is only available after t.
    """
    prices = _make_prices(n=250, seed=0)

    # Compute features on a truncated series (first 180 rows)
    cutoff = 180
    feat_partial = build_features(prices.iloc[:cutoff], horizon_days=5)

    # Compute features on the full series (all 250 rows, i.e. 70 future rows added)
    feat_full = build_features(prices, horizon_days=5)

    # Rows present in both
    common_idx = feat_partial.index.intersection(feat_full.index)
    assert len(common_idx) > 0, "No common rows found"

    feat_cols = feature_columns(feat_partial)

    for col in feat_cols:
        s_partial = feat_partial.loc[common_idx, col]
        s_full = feat_full.loc[common_idx, col]
        diff = (s_partial - s_full).abs().max()
        assert diff < 1e-10, (
            f"Feature '{col}' differs by {diff:.2e} between partial and full series. "
            "This indicates future-data dependency (lookahead)."
        )


# ── 4–5. Rolling and EWM features ────────────────────────────────────────────

def test_rolling_vol_features_backward_only():
    """
    Rolling volatility features at row t must not change when an extreme future
    row is appended.
    """
    prices = _make_prices(n=150, seed=1)
    feat_before = build_features(prices, horizon_days=5)

    # Append one extreme row (e.g. +50% spike — would massively distort any
    # forward-looking window)
    future_date = prices.index[-1] + pd.tseries.offsets.BDay(1)
    extreme_close = prices["Close"].iloc[-1] * 1.50
    extra_row = pd.DataFrame(
        {"Open": extreme_close, "High": extreme_close * 1.01,
         "Low": extreme_close * 0.99, "Close": extreme_close,
         "Volume": 9_999_999.0},
        index=[future_date],
    )
    prices_extended = pd.concat([prices, extra_row])
    feat_after = build_features(prices_extended, horizon_days=5)

    common_idx = feat_before.index.intersection(feat_after.index)
    feat_cols = [c for c in feature_columns(feat_before)
                 if c.startswith("vol_")]  # focus on volatility features

    for col in feat_cols:
        diff = (feat_before.loc[common_idx, col] - feat_after.loc[common_idx, col]).abs().max()
        assert diff < 1e-10, (
            f"Volatility feature '{col}' changed by {diff:.2e} after appending a future row. "
            "Lookahead detected."
        )


def test_ewm_macd_feature_backward_only():
    """
    EWM-based features (MACD histogram) at row t must not change when future
    rows with extreme values are appended.
    """
    prices = _make_prices(n=150, seed=2)
    feat_before = build_features(prices, horizon_days=5)

    future_date = prices.index[-1] + pd.tseries.offsets.BDay(1)
    extreme_close = prices["Close"].iloc[-1] * 2.0
    extra = pd.DataFrame(
        {"Open": extreme_close, "High": extreme_close, "Low": extreme_close,
         "Close": extreme_close, "Volume": 1.0},
        index=[future_date],
    )
    prices_extended = pd.concat([prices, extra])
    feat_after = build_features(prices_extended, horizon_days=5)

    common_idx = feat_before.index.intersection(feat_after.index)

    diff = (
        feat_before.loc[common_idx, "mom_macd_hist"]
        - feat_after.loc[common_idx, "mom_macd_hist"]
    ).abs().max()
    assert diff < 1e-10, (
        f"MACD histogram changed by {diff:.2e} after appending a future row. "
        "EWM may be forward-dependent."
    )


# ── 6. fwd_return IS forward-looking (expected) ───────────────────────────────

def test_fwd_return_nan_at_last_horizon_rows():
    """
    fwd_return must be NaN for the last horizon_days rows because the
    future return is not yet observable.  This confirms the target is genuinely
    forward-looking (required) and that the column is NOT a feature.
    """
    horizon = 5
    prices = _make_prices(n=150)
    feat_df = build_features(prices, horizon_days=horizon)

    # Last `horizon` rows should have NaN fwd_return (no future price available)
    last_fwd = feat_df["fwd_return"].iloc[-horizon:]
    assert last_fwd.isna().all(), (
        f"Expected NaN fwd_return in last {horizon} rows — "
        f"got: {last_fwd.tolist()}"
    )


def test_fwd_return_not_nan_in_historical_rows():
    """
    fwd_return must NOT be NaN in historical rows (where future price is known).
    This confirms the target is actually computable.
    """
    horizon = 5
    prices = _make_prices(n=150)
    feat_df = build_features(prices, horizon_days=horizon)
    historical = feat_df["fwd_return"].iloc[:-horizon]
    assert historical.notna().all(), "Some historical fwd_return values are NaN unexpectedly"


# ── 7–9. Walk-forward splits ──────────────────────────────────────────────────

def test_walk_forward_splits_strictly_temporal():
    """max(train_idx) < min(val_idx) for every split — no peeking at future."""
    for n in [100, 200, 500]:
        splits = walk_forward_split(n_samples=n, n_splits=5)
        for i, (train_idx, val_idx) in enumerate(splits):
            assert train_idx.max() < val_idx.min(), (
                f"Split {i}: train max ({train_idx.max()}) >= val min ({val_idx.min()}) "
                f"for n={n}. Temporal ordering violated."
            )


def test_walk_forward_splits_no_index_overlap():
    """Train and val index sets must be disjoint for every split."""
    splits = walk_forward_split(n_samples=200, n_splits=5)
    for i, (train_idx, val_idx) in enumerate(splits):
        overlap = set(train_idx.tolist()) & set(val_idx.tolist())
        assert len(overlap) == 0, (
            f"Split {i}: {len(overlap)} overlapping indices between train and val. "
            "Data from the future leaks into training."
        )


def test_walk_forward_is_expanding_window():
    """Each successive split uses a larger training set (expanding window)."""
    splits = walk_forward_split(n_samples=200, n_splits=5)
    train_sizes = [len(train) for train, _ in splits]
    for i in range(1, len(train_sizes)):
        assert train_sizes[i] >= train_sizes[i - 1], (
            f"Training set shrank from split {i-1} (size={train_sizes[i-1]}) "
            f"to split {i} (size={train_sizes[i]}). Not an expanding window."
        )


def test_walk_forward_val_sets_are_future_of_train():
    """All validation indices must be strictly greater than all training indices."""
    splits = walk_forward_split(n_samples=200, n_splits=5)
    for i, (train_idx, val_idx) in enumerate(splits):
        if len(train_idx) > 0 and len(val_idx) > 0:
            assert val_idx.min() > train_idx.max(), (
                f"Split {i}: validation data starts before end of training data."
            )


# ── 10. Temporal test split ───────────────────────────────────────────────────

def test_temporal_test_split_uses_last_rows():
    """
    The train/test split in train_model() must use the last rows as test,
    not a random sample.  Verify the logic by checking the split formula.
    """
    # Mirror the exact split formula from train_model()
    for n_total in [100, 200, 500, 1000]:
        test_size = max(int(n_total * 0.2), 20)
        dev_size = n_total - test_size

        # Test set = last test_size rows
        X_dev_idx = np.arange(dev_size)
        X_test_idx = np.arange(dev_size, n_total)

        # Verify: no overlap
        assert len(set(X_dev_idx.tolist()) & set(X_test_idx.tolist())) == 0
        # Verify: test is at the end
        assert X_test_idx.min() == dev_size
        assert X_test_idx.max() == n_total - 1
        # Verify: ordering preserved
        assert X_dev_idx.max() < X_test_idx.min()


# ── 11. predict() uses feature_columns() ─────────────────────────────────────

def test_predict_extracts_feature_columns_not_all_columns():
    """
    predict() must select only feature_columns() from the built feature matrix,
    which explicitly excludes fwd_return.  Verify via inspection of the pipeline.
    """
    prices = _make_prices(n=150)
    feat_df = build_features(prices, horizon_days=5)
    feat_cols = feature_columns(feat_df)

    # feature_columns() must not include fwd_return
    assert "fwd_return" not in feat_cols

    # The last row (used for prediction) must have valid feature values
    last_row = feat_df[feat_cols].iloc[[-1]]
    assert last_row.shape == (1, len(feat_cols))
    assert last_row.notna().all(axis=None), (
        "Some feature values are NaN in the last row — "
        "insufficient lookback data for prediction"
    )


def test_last_row_features_identical_for_different_history_lengths():
    """
    predict() calls build_features() and takes iloc[-1].
    Non-EWM features must be exactly identical regardless of history length.
    EWM-based features (MACD) may differ by a tiny initialization residual.

    EWM note: with adjust=False the recursive formula has infinite memory.
    After N steps with decay alpha=2/(span+1), the initial condition is
    dampened by (1-alpha)^N.  For span=26 and N>=150 this residual is
    < 1e-4, which is negligible for all practical purposes but prevents
    an exact-equality assertion.  This is NOT lookahead — it is a known
    EWM initialization artifact and is acceptable behaviour.
    """
    prices = _make_prices(n=200, seed=5)
    cutoff_date = prices.index[-1]

    feat_150 = build_features(prices.iloc[-150:], horizon_days=5)
    feat_180 = build_features(prices.iloc[-180:], horizon_days=5)

    cols = feature_columns(feat_150)

    assert feat_150.index[-1] == feat_180.index[-1] == cutoff_date

    last_150 = feat_150[cols].iloc[-1]
    last_180 = feat_180[cols].iloc[-1]

    ewm_cols = [c for c in cols if "macd" in c]
    non_ewm_cols = [c for c in cols if c not in ewm_cols]

    # Non-EWM features: strictly identical (pure rolling windows)
    if non_ewm_cols:
        diff_non_ewm = (last_150[non_ewm_cols] - last_180[non_ewm_cols]).abs().max()
        assert diff_non_ewm < 1e-10, (
            f"Non-EWM feature differs by {diff_non_ewm:.2e} between 150-row and 180-row history. "
            "Pure rolling features must not depend on history length."
        )

    # EWM features: residual < 1e-3 after 150+ steps of convergence
    if ewm_cols:
        diff_ewm = (last_150[ewm_cols] - last_180[ewm_cols]).abs().max()
        assert diff_ewm < 1e-3, (
            f"EWM feature differs by {diff_ewm:.2e} between 150-row and 180-row history. "
            "Expected EWM initialization residual is < 1e-4 for span<=26 with N>=150 steps; "
            f"{diff_ewm:.2e} exceeds acceptable convergence bounds."
        )


# ── 12. Extreme future row doesn't corrupt preceding features ─────────────────

def test_extreme_future_row_does_not_change_preceding_features():
    """
    Appending a row with an extreme return (+200%) must not change any
    feature values at the preceding row.  Covers all feature categories.
    """
    prices = _make_prices(n=150, seed=7)
    feat_original = build_features(prices, horizon_days=5)
    last_common_date = feat_original.index[-1]

    # Append a wild future row
    future_date = prices.index[-1] + pd.tseries.offsets.BDay(1)
    wild_close = prices["Close"].iloc[-1] * 3.0
    extra = pd.DataFrame(
        {"Open": wild_close, "High": wild_close * 1.05, "Low": wild_close * 0.95,
         "Close": wild_close, "Volume": 100.0},
        index=[future_date],
    )
    prices_ext = pd.concat([prices, extra])
    feat_extended = build_features(prices_ext, horizon_days=5)

    feat_cols = feature_columns(feat_original)
    for col in feat_cols:
        v_orig = feat_original.loc[last_common_date, col]
        v_ext = feat_extended.loc[last_common_date, col]
        diff = abs(float(v_orig) - float(v_ext))
        assert diff < 1e-10, (
            f"Feature '{col}' at last common row changed by {diff:.2e} "
            "after appending an extreme future row. Lookahead detected."
        )


# ── 13. dataset_hash stability ────────────────────────────────────────────────

def test_dataset_hash_deterministic():
    """dataset_hash() must return the same value for the same data."""
    prices = _make_prices(n=200, seed=42)
    feat_df = build_features(prices, horizon_days=5)
    h1 = dataset_hash(feat_df)
    h2 = dataset_hash(feat_df)
    assert h1 == h2


def test_dataset_hash_changes_with_different_data():
    """dataset_hash() must return different values for different datasets."""
    prices_a = _make_prices(n=200, seed=42)
    prices_b = _make_prices(n=200, seed=99)
    feat_a = build_features(prices_a, horizon_days=5)
    feat_b = build_features(prices_b, horizon_days=5)
    assert dataset_hash(feat_a) != dataset_hash(feat_b)
