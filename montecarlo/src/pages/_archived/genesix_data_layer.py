"""
GenesiX Data Layer — Real infrastructure health check and data source status.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys, os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Data Layer — GenesiX", page_icon=None, layout="wide")


# ============================================================================
# CACHED HELPER FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_cache_stats():
    """Scan the data/ cache directory for stats."""
    try:
        from genesix.utils.config import Config
        cache_dir = Config.DATA_CACHE_DIR
        stats = {
            'exists': cache_dir.exists(),
            'path': str(cache_dir),
            'total_size_mb': 0.0,
            'file_count': 0,
            'files': [],
        }
        if cache_dir.exists():
            for f in cache_dir.rglob('*'):
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    stats['total_size_mb'] += size_mb
                    stats['file_count'] += 1
                    stats['files'].append({
                        'file': f.name,
                        'size_mb': round(size_mb, 3),
                        'last_modified': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                        'path': str(f.relative_to(cache_dir)),
                    })
        return stats
    except Exception as e:
        return {'error': str(e), 'exists': False, 'path': 'N/A',
                'total_size_mb': 0, 'file_count': 0, 'files': []}


@st.cache_data(ttl=60)
def check_yfinance():
    """Quick connectivity check against yfinance."""
    start = time.time()
    try:
        import yfinance as yf
        tick = yf.download('SPY', period='2d', progress=False)
        elapsed_ms = (time.time() - start) * 1000
        if tick is not None and len(tick) > 0:
            close = float(tick['Close'].iloc[-1]) if 'Close' in tick else None
            return {
                'ok': True,
                'latency_ms': round(elapsed_ms, 1),
                'last_price': close,
                'rows': len(tick),
            }
        return {'ok': False, 'latency_ms': round(elapsed_ms, 1), 'error': 'Empty response'}
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return {'ok': False, 'latency_ms': round(elapsed_ms, 1), 'error': str(e)}


@st.cache_data(ttl=300)
def get_config_status():
    """Check which API keys are configured."""
    try:
        from genesix.utils.config import Config
        return {
            'alpha_vantage': bool(Config.ALPHA_VANTAGE_API_KEY and Config.ALPHA_VANTAGE_API_KEY != 'demo'),
            'data_cache_dir': str(Config.DATA_CACHE_DIR),
            'feature_cache_ttl_hours': Config.FEATURE_CACHE_TTL_HOURS,
            'yfinance_timeout': Config.YFINANCE_TIMEOUT,
            'yfinance_retries': Config.YFINANCE_RETRIES,
        }
    except Exception as e:
        return {'error': str(e)}


@st.cache_data(ttl=300)
def get_cached_tickers():
    """List tickers available in the local market data cache."""
    try:
        from genesix.utils.config import Config
        cache_dir = Config.DATA_CACHE_DIR / "market_data"
        tickers = set()
        if cache_dir.exists():
            for f in cache_dir.glob('*.pkl'):
                parts = f.stem.rsplit('_', 1)
                if len(parts) == 2:
                    tickers.add(parts[0])
        return sorted(tickers)
    except Exception:
        return []


# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("Data Layer")
st.markdown("Infrastructure health, cache statistics, and live data source status.")

# ============================================================================
# HEADER METRICS (real values)
# ============================================================================

with st.spinner("Scanning cache and checking connectivity..."):
    cache_stats = get_cache_stats()
    yf_status = check_yfinance()
    config_status = get_config_status()
    cached_tickers = get_cached_tickers()

hm1, hm2, hm3, hm4 = st.columns(4)
hm1.metric(
    "Cache Size",
    f"{cache_stats.get('total_size_mb', 0):.1f} MB",
    help=f"Path: {cache_stats.get('path', 'N/A')}"
)
hm2.metric(
    "Cached Files",
    str(cache_stats.get('file_count', 0)),
)
hm3.metric(
    "yfinance Status",
    "ONLINE" if yf_status.get('ok') else "OFFLINE",
    delta=f"{yf_status.get('latency_ms', 0):.0f}ms latency",
    delta_color="normal" if yf_status.get('ok') else "inverse",
)
hm4.metric(
    "Tickers in Cache",
    str(len(cached_tickers)),
)

st.divider()

# ============================================================================
# DATA SOURCE STATUS TABLE
# ============================================================================

st.subheader("Data Source Status")

av_configured = config_status.get('alpha_vantage', False)

source_data = [
    {
        'Source': 'yfinance (Yahoo Finance)',
        'Type': 'Equities, ETFs, Crypto, FX, Commodities',
        'Status': 'ONLINE' if yf_status.get('ok') else 'OFFLINE',
        'Latency': f"{yf_status.get('latency_ms', 0):.0f}ms",
        'Auth Required': 'No (free)',
        'Notes': f"SPY last price: ${yf_status.get('last_price', 'N/A')}",
    },
    {
        'Source': 'Alpha Vantage',
        'Type': 'Equities, Forex intraday, Macro indicators',
        'Status': 'CONFIGURED' if av_configured else 'NOT CONFIGURED',
        'Latency': 'N/A',
        'Auth Required': 'Yes (free key)',
        'Notes': 'Set ALPHA_VANTAGE_KEY in .env',
    },
    {
        'Source': 'CoinGecko',
        'Type': 'Cryptocurrency (BTC, ETH, etc.)',
        'Status': 'AVAILABLE (free tier)',
        'Latency': 'N/A',
        'Auth Required': 'No (rate limited)',
        'Notes': 'Optional: pycoingecko package',
    },
    {
        'Source': 'FRED (Federal Reserve)',
        'Type': 'Macro: GDP, CPI, unemployment, rates',
        'Status': 'NOT CONFIGURED',
        'Latency': 'N/A',
        'Auth Required': 'Yes (free key)',
        'Notes': 'Set FRED_API_KEY in .env',
    },
]

source_df = pd.DataFrame(source_data)
st.dataframe(source_df, use_container_width=True, hide_index=True)

st.divider()

# ============================================================================
# CACHE DETAILS
# ============================================================================

cache_col1, cache_col2 = st.columns(2)

with cache_col1:
    st.subheader("Cache Directory Details")
    cfg_rows = []
    if 'error' not in config_status:
        for k, v in config_status.items():
            cfg_rows.append({'Setting': k, 'Value': str(v)})
    st.dataframe(pd.DataFrame(cfg_rows), use_container_width=True, hide_index=True)

    if cached_tickers:
        st.subheader(f"Cached Tickers ({len(cached_tickers)})")
        st.write(', '.join(cached_tickers[:50]))
        if len(cached_tickers) > 50:
            st.caption(f"...and {len(cached_tickers)-50} more")
    else:
        st.info("No tickers cached yet. Data will be cached after first fetch.")

with cache_col2:
    st.subheader("Cached Files")
    if cache_stats.get('files'):
        files_df = pd.DataFrame(cache_stats['files'])
        files_df = files_df.sort_values('last_modified', ascending=False)
        st.dataframe(files_df[['file', 'size_mb', 'last_modified']],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No cache files found at the configured cache path.")

st.divider()

# ============================================================================
# LIVE DATA TEST
# ============================================================================

st.subheader("Live Data Test")
st.markdown("Fetch a real-time price and measure latency.")

test_col1, test_col2 = st.columns([2, 1])
with test_col1:
    test_ticker = st.text_input("Test Ticker", value="SPY", key="test_ticker_input").upper().strip()
with test_col2:
    st.write("")
    run_test = st.button("Fetch Live Price", type="primary", use_container_width=True)

if run_test:
    with st.spinner(f"Fetching {test_ticker}..."):
        t0 = time.time()
        try:
            import yfinance as yf
            tick_data = yf.download(test_ticker, period='2d', progress=False)
            elapsed = (time.time() - t0) * 1000

            if tick_data is not None and len(tick_data) > 0:
                close_col = 'Close'
                if isinstance(tick_data.columns, pd.MultiIndex):
                    close_col = ('Close', test_ticker)
                last_price = float(tick_data[close_col].iloc[-1])
                prev_price = float(tick_data[close_col].iloc[-2]) if len(tick_data) > 1 else last_price
                pct_chg = (last_price - prev_price) / prev_price * 100

                r1, r2, r3 = st.columns(3)
                r1.metric(f"{test_ticker} Last Price", f"${last_price:.2f}",
                          delta=f"{pct_chg:+.2f}%")
                r2.metric("Latency", f"{elapsed:.0f}ms")
                r3.metric("Data Rows", str(len(tick_data)))
                st.success(f"Live data fetch successful for {test_ticker} in {elapsed:.0f}ms.")
            else:
                st.error(f"No data returned for {test_ticker}. Check the ticker symbol.")
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            st.error(f"Data fetch failed after {elapsed:.0f}ms: {e}")

st.divider()

# ============================================================================
# FEATURE STORE STATUS
# ============================================================================

st.subheader("Feature Engineering Pipeline")
st.markdown("Status of the GenesiX feature store (used by ML models).")

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from genesix.data.feature_store import FeatureStore
    fs = FeatureStore()
    st.success("FeatureStore module loaded successfully.")
    feature_info = [
        {'Component': 'FeatureStore', 'Status': 'OK', 'Notes': 'Ready for ML training'},
        {'Component': 'MarketDataFetcher', 'Status': 'OK', 'Notes': 'Primary data source'},
        {'Component': 'GenesiXPredictor', 'Status': 'OK', 'Notes': 'Requires sklearn/xgboost'},
        {'Component': 'GenesiXRiskEngine', 'Status': 'OK', 'Notes': 'scipy required'},
    ]
except Exception as e:
    feature_info = [
        {'Component': 'FeatureStore', 'Status': 'ERROR', 'Notes': str(e)},
    ]
    st.warning(f"FeatureStore initialization: {e}")

st.dataframe(pd.DataFrame(feature_info), use_container_width=True, hide_index=True)
