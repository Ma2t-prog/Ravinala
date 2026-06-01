from __future__ import annotations

import sys
from math import isclose, sqrt
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.backtest.engine import compute_metrics
from app.core.config import Settings
from app.ml import features as _feat
from app.risk.conventions import CONVENTIONS
from app.schemas.portfolio import OptimizeResponse


def test_settings_default_risk_free_rate_matches_conventions() -> None:
    settings = Settings()
    assert settings.risk_free_rate == CONVENTIONS.risk_free_rate
    assert settings.risk_free_rate_source == CONVENTIONS.risk_free_rate_source
    assert settings.risk_free_rate_last_updated == CONVENTIONS.risk_free_rate_last_updated


def test_compute_metrics_uses_governed_default_risk_free_rate() -> None:
    equity = pd.Series([100.0, 101.0, 102.5, 101.7, 103.1])
    metrics = compute_metrics(equity)
    assert metrics["risk_free_rate"] == CONVENTIONS.risk_free_rate


def test_compute_metrics_accepts_explicit_override() -> None:
    equity = pd.Series([100.0, 101.0, 99.5, 103.0, 104.0])
    metrics = compute_metrics(equity, risk_free_rate=0.02)
    assert metrics["risk_free_rate"] == 0.02


def test_optimize_response_requires_risk_free_rate_used() -> None:
    response = OptimizeResponse(
        objective="max_sharpe",
        weights=[],
        expected_return=0.12,
        expected_volatility=0.08,
        sharpe_ratio=1.1,
        risk_free_rate_used=CONVENTIONS.risk_free_rate,
        diversification_ratio=None,
        efficient_frontier=[],
    )
    assert response.risk_free_rate_used == CONVENTIONS.risk_free_rate


# ── Q5.1 — consistency: features.py constants must mirror CONVENTIONS ─────────

def test_features_ann_factor_matches_conventions() -> None:
    """features._ANN_FACTOR_VOL must equal CONVENTIONS.ann_factor_vol (Q5.1)."""
    assert isclose(_feat._ANN_FACTOR_VOL, CONVENTIONS.ann_factor_vol, rel_tol=1e-12), (
        f"features._ANN_FACTOR_VOL={_feat._ANN_FACTOR_VOL} != "
        f"CONVENTIONS.ann_factor_vol={CONVENTIONS.ann_factor_vol}"
    )


def test_features_vol_windows_match_conventions() -> None:
    """features._VOL_WINDOWS must equal CONVENTIONS.ml_vol_windows (Q5.1)."""
    assert tuple(_feat._VOL_WINDOWS) == tuple(CONVENTIONS.ml_vol_windows), (
        f"features._VOL_WINDOWS={_feat._VOL_WINDOWS} != "
        f"CONVENTIONS.ml_vol_windows={CONVENTIONS.ml_vol_windows}"
    )


def test_features_rsi_period_matches_conventions() -> None:
    assert _feat._RSI_PERIOD == CONVENTIONS.ml_rsi_period


def test_features_macd_params_match_conventions() -> None:
    assert _feat._MACD_FAST == CONVENTIONS.ml_macd_fast
    assert _feat._MACD_SLOW == CONVENTIONS.ml_macd_slow
    assert _feat._MACD_SIGNAL == CONVENTIONS.ml_macd_signal


def test_features_roc_sma_volume_match_conventions() -> None:
    assert _feat._ROC_PERIOD == CONVENTIONS.ml_roc_period
    assert _feat._SMA_SHORT == CONVENTIONS.ml_sma_short
    assert _feat._SMA_LONG == CONVENTIONS.ml_sma_long
    assert _feat._VOLUME_MA_PERIOD == CONVENTIONS.ml_volume_ma_period


def test_conventions_ann_factor_vol_formula() -> None:
    """ann_factor_vol = sqrt(trading_days_per_year) — formula integrity check."""
    expected = sqrt(CONVENTIONS.trading_days_per_year)
    assert isclose(CONVENTIONS.ann_factor_vol, expected, rel_tol=1e-12)


def test_conventions_ann_factor_return_formula() -> None:
    """ann_factor_return = trading_days_per_year — formula integrity check."""
    assert isclose(CONVENTIONS.ann_factor_return, float(CONVENTIONS.trading_days_per_year), rel_tol=1e-12)
