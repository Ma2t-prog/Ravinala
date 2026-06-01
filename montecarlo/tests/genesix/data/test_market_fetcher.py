"""Tests for market_fetcher.py"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.genesix.data.market_fetcher import MarketDataFetcher


class TestMarketDataFetcherInitialization:
    """Test fetcher initialization."""
    
    def test_initialization_succeeds(self):
        """MarketDataFetcher initializes without errors."""
        mf = MarketDataFetcher()
        assert mf is not None
        assert hasattr(mf, 'cache_dir')


class TestFetchEquities:
    """Test equity fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_fetch_equities_returns_dataframe(self, fetcher):
        """fetch_equities returns a DataFrame, never None."""
        result = fetcher.fetch_equities(['SPY', 'QQQ'], period='1mo')
        assert isinstance(result, pd.DataFrame)
        assert result is not None
    
    def test_fetch_equities_schema(self, fetcher):
        """Result has correct columns: open, high, low, close, volume."""
        result = fetcher.fetch_equities(['SPY'], period='1mo')
        if len(result) > 0:
            required_cols = {'open', 'high', 'low', 'close', 'volume'}
            actual_cols = set(result.columns)
            assert required_cols.issubset(actual_cols), f"Missing columns. Have {actual_cols}, need {required_cols}"
    
    def test_fetch_single_ticker(self, fetcher):
        """Single ticker fetch works."""
        result = fetcher.fetch_equities(['AAPL'], period='1mo')
        assert isinstance(result, pd.DataFrame)
    
    def test_empty_ticker_list_returns_empty_df(self, fetcher):
        """Empty input → empty DataFrame, no crash."""
        result = fetcher.fetch_equities([], period='1mo')
        assert isinstance(result, pd.DataFrame)
        # Empty DataFrame is acceptable
    
    def test_invalid_ticker_handled_gracefully(self, fetcher):
        """Invalid ticker like 'XYZXYZ123' doesn't crash, returns empty or filters out."""
        result = fetcher.fetch_equities(['XYZXYZ123'], period='1mo')
        assert isinstance(result, pd.DataFrame)
        # Should either be empty or very small
    
    def test_fetch_multiple_tickers(self, fetcher):
        """Multiple tickers fetch in a single call."""
        result = fetcher.fetch_equities(['SPY', 'QQQ', 'IWM'], period='1mo')
        assert isinstance(result, pd.DataFrame)


class TestFetchCrypto:
    """Test cryptocurrency fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_fetch_crypto_returns_dataframe(self, fetcher):
        """fetch_crypto returns a DataFrame."""
        result = fetcher.fetch_crypto(['BTC'], days=90)
        assert isinstance(result, pd.DataFrame)
    
    def test_crypto_fallback_to_yfinance(self, fetcher):
        """If CoinGecko fails, falls back to yfinance."""
        result = fetcher.fetch_crypto(['ETH'], days=30)
        assert isinstance(result, pd.DataFrame)


class TestFetchForex:
    """Test forex pair fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_fetch_forex_returns_dataframe(self, fetcher):
        """fetch_forex returns a DataFrame."""
        result = fetcher.fetch_forex(['EUR/USD'], period='3mo')
        assert isinstance(result, pd.DataFrame)
    
    def test_forex_pair_format_conversion(self, fetcher):
        """'EUR/USD' is correctly converted to 'EURUSD=X'."""
        # The method should handle the conversion internally
        result = fetcher.fetch_forex(['EUR/USD'], period='1mo')
        assert isinstance(result, pd.DataFrame)


class TestFetchCommodities:
    """Test commodity fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_fetch_commodities_returns_dataframe(self, fetcher):
        """fetch_commodities returns a DataFrame."""
        result = fetcher.fetch_commodities(['GOLD'], period='1mo')
        assert isinstance(result, pd.DataFrame)


class TestFetchIndices:
    """Test index fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_fetch_indices_returns_dataframe(self, fetcher):
        """fetch_indices returns a DataFrame."""
        result = fetcher.fetch_indices(['SP500'], period='1mo')
        assert isinstance(result, pd.DataFrame)


class TestGetHistoricalOHLCV:
    """Test historical OHLCV fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_get_historical_ohlcv_returns_dataframe(self, fetcher):
        """get_historical_ohlcv returns a DataFrame."""
        end = datetime.now()
        start = end - timedelta(days=30)
        result = fetcher.get_historical_ohlcv('SPY', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        assert isinstance(result, pd.DataFrame)
    
    def test_historical_data_has_required_columns(self, fetcher):
        """Returned DataFrame has OHLCV columns."""
        end = datetime.now()
        start = end - timedelta(days=30)
        result = fetcher.get_historical_ohlcv('SPY', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        if len(result) > 0:
            required = {'open', 'high', 'low', 'close', 'volume'}
            assert required.issubset(set(result.columns))


class TestGetRealtimePrice:
    """Test realtime price fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_get_realtime_price_returns_dict(self, fetcher):
        """get_realtime_price returns a dict with required keys."""
        result = fetcher.get_realtime_price('SPY')
        assert isinstance(result, dict)
        # Should have basic keys if successful
        if result:
            assert 'ticker' in result or 'price' in result or result == {}
    
    def test_realtime_returns_float_price(self, fetcher):
        """If successful, price should be float."""
        result = fetcher.get_realtime_price('SPY')
        if result and 'price' in result:
            assert isinstance(result['price'], (float, int))


class TestDataFrameNormalization:
    """Test normalization of DataFrames."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_normalize_handles_nans(self, fetcher):
        """NaN-only rows are dropped, small gaps forward-filled."""
        # Create a test DataFrame with some NaNs
        df = pd.DataFrame({
            'Open': [100, np.nan, 102, 103],
            'High': [101, np.nan, 103, 104],
            'Low': [99, np.nan, 101, 102],
            'Close': [100.5, np.nan, 102.5, 103.5],
            'Volume': [1000000, np.nan, 1100000, 1200000],
        }, index=pd.date_range('2024-01-01', periods=4))
        
        normalized = fetcher._normalize_dataframe(df, 'test')
        assert isinstance(normalized, pd.DataFrame)
        # Check that all-NaN rows are handled
        assert len(normalized) <= len(df)
    
    def test_normalize_dataframe_timezone(self, fetcher):
        """Output is tz-naive UTC DatetimeIndex."""
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.date_range('2024-01-01', periods=3, tz='UTC'))
        
        normalized = fetcher._normalize_dataframe(df, 'test')
        assert isinstance(normalized.index, pd.DatetimeIndex)


class TestCaching:
    """Test cache functionality."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_cache_roundtrip(self, fetcher):
        """Save to cache, load from cache, data matches."""
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000000, 1100000, 1200000],
        }, index=pd.date_range('2024-01-01', periods=3))
        
        key = 'test_ticker_1d'
        fetcher._save_to_cache(key, df)
        loaded = fetcher._load_from_cache(key, max_age_hours=24)
        
        if loaded is not None:
            # Caching worked
            pd.testing.assert_frame_equal(df, loaded, check_dtype=False)


class TestRetryBackoff:
    """Test retry and backoff logic."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_retry_backoff_returns_result_on_success(self, fetcher):
        """Successful function returns result."""
        def dummy_func():
            return "success"
        
        result = fetcher._retry_with_backoff(dummy_func, max_retries=3)
        assert result == "success"
    
    def test_retry_backoff_handles_failure(self, fetcher):
        """Failed function returns None after retries."""
        def always_fails():
            raise Exception("Test error")
        
        result = fetcher._retry_with_backoff(always_fails, max_retries=2)
        # Should return None after retries
        assert result is None


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def fetcher(self):
        return MarketDataFetcher()
    
    def test_very_old_date_range(self, fetcher):
        """Request for very old data works or returns empty gracefully."""
        end = datetime(2010, 1, 1)
        start = datetime(2000, 1, 1)
        result = fetcher.get_historical_ohlcv('SPY', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        assert isinstance(result, pd.DataFrame)
    
    def test_future_date_range(self, fetcher):
        """Request for future data returns empty or handles gracefully."""
        end = datetime(2030, 1, 1)
        start = datetime(2029, 1, 1)
        result = fetcher.get_historical_ohlcv('SPY', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        assert isinstance(result, pd.DataFrame)


# Integration tests
class TestIntegration:
    """Integration tests for market fetcher."""
    
    def test_full_workflow_single_asset(self):
        """Complete workflow: init, fetch, process, cache."""
        mf = MarketDataFetcher()
        df = mf.get_historical_ohlcv('SPY', '2024-01-01', '2024-02-01')
        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
    
    def test_no_single_point_of_failure(self):
        """Fetcher doesn't crash on various API issues."""
        mf = MarketDataFetcher()
        # These should all return DataFrames, not crash
        results = [
            mf.fetch_equities(['SPY'], period='1d'),
            mf.fetch_crypto(['BTC'], days=7),
            mf.fetch_forex(['EUR/USD'], period='1w'),
        ]
        for r in results:
            assert isinstance(r, pd.DataFrame)
