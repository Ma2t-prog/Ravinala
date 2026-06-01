"""
Feature flags registry — single source of truth for disabled/experimental features.

Usage:
    from genesix.utils.feature_flags import is_disabled, is_experimental

    if is_disabled('lstm'):
        raise NotImplementedError("LSTM is disabled")
"""

# Features confirmed disabled — no real implementation exists
DISABLED: dict[str, str] = {
    'lstm': 'No trained LSTM model available',
    'garch': 'No trained GARCH model available',
    'black_litterman': 'Requires full covariance matrix + market cap weights',
    'signal_ml_subsignal': 'No ML model connected',
    'signal_nlp_subsignal': 'No NLP engine connected',
    'signal_technical_subsignal': 'No real-time data source connected',
    'signal_risk_subsignal': 'No risk engine connected',
    'signal_macro_subsignal': 'No macro data source connected',
}

# Features that exist but are experimental / not production-ready
EXPERIMENTAL: dict[str, str] = {
    'regime_detection': 'HMM-based regime detection — needs validation',
    'walk_forward_validation': 'Walk-forward CV — single split only',
}

# Features requiring near-real-time data (not available in demo mode)
NEAR_REAL_TIME_ONLY: dict[str, str] = {
    'live_signals': 'Requires live market data feed',
    'streaming_portfolio': 'Requires WebSocket connection',
}


def is_disabled(feature: str) -> bool:
    """Check if a feature is disabled."""
    return feature in DISABLED


def is_experimental(feature: str) -> bool:
    """Check if a feature is experimental."""
    return feature in EXPERIMENTAL
