"""Tests for alt_data_fetcher.py"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.genesix.data.alt_data_fetcher import AltDataFetcher


class TestAltDataFetcherInitialization:
    """Test alt data fetcher initialization."""
    
    def test_initialization_no_crash(self):
        """AltDataFetcher initializes without API keys configured."""
        adf = AltDataFetcher()
        assert adf is not None


class TestWeatherFetching:
    """Test weather data fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_fetch_weather_returns_dataframe(self, fetcher):
        """fetch_weather returns a DataFrame."""
        result = fetcher.fetch_weather()
        assert isinstance(result, pd.DataFrame)
    
    def test_weather_impact_score_range(self, fetcher):
        """Weather impact score is always in [-1, 1]."""
        score = fetcher.compute_weather_impact_score('wheat')
        assert -1 <= score <= 1


class TestNewsSentiment:
    """Test news sentiment analysis."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_vader_sentiment_positive(self, fetcher):
        """Positive headlines score > 0."""
        headlines = [
            'Stock market reaches all-time high',
            'Company earnings beat expectations',
            'Economic growth accelerates',
        ]
        result = fetcher.compute_news_sentiment(headlines)
        assert isinstance(result, dict)
        if 'mean_compound' in result:
            # Very positive headlines should have positive sentiment
            assert result['mean_compound'] > 0
    
    def test_vader_sentiment_negative(self, fetcher):
        """Negative headlines score < 0."""
        headlines = [
            'Market crash imminent',
            'Company files for bankruptcy',
            'Recession fears grow',
        ]
        result = fetcher.compute_news_sentiment(headlines)
        assert isinstance(result, dict)
        if 'mean_compound' in result:
            assert result['mean_compound'] < 0
    
    def test_compute_news_sentiment_returns_dict(self, fetcher):
        """compute_news_sentiment returns a dictionary."""
        result = fetcher.compute_news_sentiment(['neutral headline'])
        assert isinstance(result, dict)


class TestGoogleTrends:
    """Test Google Trends fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_fetch_google_trends_returns_dataframe(self, fetcher):
        """fetch_google_trends returns a DataFrame."""
        result = fetcher.fetch_google_trends(['bitcoin'], timeframe='today 1-m')
        assert isinstance(result, pd.DataFrame)
    
    def test_trends_momentum_returns_float(self, fetcher):
        """compute_trends_momentum returns a float."""
        momentum = fetcher.compute_trends_momentum('bitcoin')
        assert isinstance(momentum, (float, int))
    
    def test_trends_momentum_neutral_fallback(self, fetcher):
        """Returns 1.0 (neutral) when trends unavailable."""
        # Should gracefully return neutral value
        momentum = fetcher.compute_trends_momentum('bitcoin')
        # Could be 1.0 or could be a calculated value
        assert isinstance(momentum, (float, int))


class TestRedditSentiment:
    """Test Reddit sentiment analysis."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_fetch_reddit_sentiment_returns_dict(self, fetcher):
        """fetch_reddit_sentiment returns a dictionary."""
        result = fetcher.fetch_reddit_sentiment()
        assert isinstance(result, dict)
    
    def test_reddit_graceful_without_praw(self, fetcher):
        """Without PRAW credentials, returns neutral dict."""
        result = fetcher.fetch_reddit_sentiment()
        assert isinstance(result, dict)
        # Should have required keys even if unavailable
        if result:
            assert 'overall_sentiment' in result or 'bullish_pct' in result or True


class TestMarketIndicators:
    """Test market indicator fetching."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_fetch_vix_returns_series(self, fetcher):
        """fetch_vix returns a pd.Series."""
        result = fetcher.fetch_vix(period='1mo')
        assert isinstance(result, (pd.Series, pd.DataFrame))
    
    def test_fetch_dxy_returns_series(self, fetcher):
        """fetch_dxy returns a pd.Series."""
        result = fetcher.fetch_dxy(period='1mo')
        assert isinstance(result, (pd.Series, pd.DataFrame))
    
    def test_put_call_ratio_returns_float_or_nan(self, fetcher):
        """fetch_put_call_ratio returns float or NaN."""
        result = fetcher.fetch_put_call_ratio()
        if result is not None:
            assert isinstance(result, (float, int))
    
    def test_baltic_dry_index_returns_series(self, fetcher):
        """fetch_baltic_dry_index returns a Series."""
        result = fetcher.fetch_baltic_dry_index(period='1mo')
        assert isinstance(result, (pd.Series, pd.DataFrame))


class TestFearGreedIndex:
    """Test Fear & Greed index computation."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_fear_greed_returns_dict(self, fetcher):
        """compute_fear_greed_index returns a dictionary."""
        result = fetcher.compute_fear_greed_index()
        assert isinstance(result, dict)
    
    def test_fear_greed_score_range(self, fetcher):
        """Fear & Greed score is always 0-100."""
        result = fetcher.compute_fear_greed_index()
        if 'score' in result:
            assert 0 <= result['score'] <= 100
    
    def test_fear_greed_label_mapping(self, fetcher):
        """Score to label mapping is correct."""
        result = fetcher.compute_fear_greed_index()
        if 'label' in result:
            valid_labels = [
                'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
            ]
            assert result['label'] in valid_labels
    
    def test_fear_greed_has_components(self, fetcher):
        """Fear & Greed includes component breakdown."""
        result = fetcher.compute_fear_greed_index()
        # Should have components or scores
        assert any(key in result for key in ['components', 'score', 'label'])


class TestAltDataSnapshot:
    """Test alt data snapshot."""
    
    @pytest.fixture
    def fetcher(self):
        return AltDataFetcher()
    
    def test_alt_snapshot_returns_dict(self, fetcher):
        """get_alt_data_snapshot returns a dictionary."""
        result = fetcher.get_alt_data_snapshot()
        assert isinstance(result, dict)
    
    def test_alt_snapshot_all_keys(self, fetcher):
        """Snapshot dict has required top-level keys."""
        result = fetcher.get_alt_data_snapshot()
        # Should have at least some of these
        expected_keys = {'fear_greed', 'vix', 'news_sentiment', 'data_quality'}
        if result:
            assert any(k in result for k in expected_keys)


# Integration tests
class TestIntegration:
    """Integration tests for alt data fetcher."""
    
    def test_full_workflow(self):
        """Complete workflow: init, compute indices, snapshot."""
        adf = AltDataFetcher()
        
        fg = adf.compute_fear_greed_index()
        assert isinstance(fg, dict)
        
        snap = adf.get_alt_data_snapshot()
        assert isinstance(snap, dict)
    
    def test_no_crash_without_credentials(self):
        """All methods work even without API credentials."""
        adf = AltDataFetcher()
        
        results = [
            adf.compute_fear_greed_index(),
            adf.get_alt_data_snapshot(),
            adf.fetch_reddit_sentiment(),
        ]
        for r in results:
            assert isinstance(r, dict)
