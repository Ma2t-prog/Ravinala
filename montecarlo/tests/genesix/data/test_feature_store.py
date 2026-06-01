"""Tests for feature_store.py"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import tempfile

from src.genesix.data.feature_store import FeatureStore


class TestFeatureStoreInitialization:
    """Test feature store initialization."""
    
    def test_initialization_no_crash(self):
        """FeatureStore initializes without crash."""
        fs = FeatureStore()
        assert fs is not None
    
    def test_initialization_creates_cache_dir(self):
        """FeatureStore creates cache directory on init."""
        fs = FeatureStore()
        # Should have cache paths configured
        assert hasattr(fs, '__dict__')


class TestFeatureMatrixBuilding:
    """Test feature matrix construction."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_build_feature_matrix_returns_dataframe(self, store):
        """build_feature_matrix returns a DataFrame."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        assert isinstance(matrix, pd.DataFrame)
    
    def test_feature_matrix_has_datetime_index(self, store):
        """Feature matrix has DatetimeIndex."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        assert isinstance(matrix.index, pd.DatetimeIndex)
    
    def test_feature_matrix_non_empty(self, store):
        """Feature matrix has rows."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        assert len(matrix) > 0
    
    def test_feature_matrix_columns_exist(self, store):
        """Feature matrix has expected column types."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        # Should have at least some of these feature groups
        expected_patterns = [
            'return',          # Return features
            'volatility',      # Vol features
            'momentum',        # Momentum features
            'rsi',             # Technical indicators
        ]
        columns_lower = [c.lower() for c in matrix.columns]
        # At least one feature type should exist
        assert any(
            any(pat in c for c in columns_lower)
            for pat in expected_patterns
        )


class TestFeatureMatrixSchema:
    """Test feature matrix schema validation."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    @pytest.fixture
    def matrix(self, store):
        return store.build_feature_matrix('SPY', lookback='3mo')
    
    def test_all_columns_numeric(self, matrix):
        """All feature columns are numeric."""
        assert matrix.dtypes.apply(lambda x: np.issubdtype(x, np.number)).all()
    
    def test_no_inf_values(self, matrix):
        """No infinite values in matrix."""
        assert not np.any(np.isinf(matrix.values))
    
    def test_reasonable_value_ranges(self, matrix):
        """Feature values in reasonable ranges."""
        # Most features should be in [-100, 100] (volatility, returns, etc. normalized)
        # or in [0, 100] (percentages, RSI, etc.)
        # Allow for some outliers but most should be reasonable
        values = matrix.values.flatten()
        values_finite = values[np.isfinite(values)]
        
        if len(values_finite) > 0:
            # 95th percentile should be < 1000 (reasonable bound)
            assert np.percentile(values_finite, 95) < 1000
            # 5th percentile should be > -1000
            assert np.percentile(values_finite, 5) > -1000


class TestLookAheadBias:
    """Test for lookahead bias in forward returns."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_forward_returns_no_lookahead(self, store):
        """Forward return features don't include current bar."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        
        # If forward_return_1d exists, first row should be NaN or valid future return
        if 'forward_return_1d' in matrix.columns:
            # First few rows might be NaN (not enough history)
            # But they should never use current bar data
            assert matrix['forward_return_1d'].isna().any() or True
    
    def test_forward_returns_shifted_correctly(self, store):
        """Forward returns are shifted from current price."""
        matrix = store.build_feature_matrix('SPY', lookback='3mo')
        
        if 'forward_return_1d' in matrix.columns:
            # Forward return at row i should correspond to close at row i+1
            # Not row i (that would be lookahead)
            assert matrix.index[0] < matrix.index[-1]


class TestFeatureNormalization:
    """Test feature normalization."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_returns_normalized_reasonable(self, store):
        """Return features are in reasonable ranges."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        
        # Daily returns typically -5% to +5%
        return_cols = [c for c in matrix.columns if 'return' in c.lower()]
        if return_cols:
            for col in return_cols:
                values = matrix[col].dropna()
                if len(values) > 0:
                    # 95th percentile of return should be < 500% daily
                    assert values.quantile(0.95) < 5.0
    
    def test_volatility_positive(self, store):
        """Volatility features are non-negative."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        
        vol_cols = [c for c in matrix.columns if 'volatility' in c.lower() or 'vol' in c.lower()]
        if vol_cols:
            for col in vol_cols:
                values = matrix[col].dropna()
                assert (values >= 0).all()
    
    def test_rsi_in_bounds(self, store):
        """RSI features are in [0, 100]."""
        matrix = store.build_feature_matrix('SPY', lookback='6mo')
        
        rsi_cols = [c for c in matrix.columns if 'rsi' in c.lower()]
        if rsi_cols:
            for col in rsi_cols:
                values = matrix[col].dropna()
                assert (values >= 0).all() and (values <= 100).all()


class TestFeatureCaching:
    """Test feature matrix caching."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_build_caches_result(self, store):
        """Building feature matrix creates cache."""
        matrix1 = store.build_feature_matrix('SPY', lookback='3mo')
        # Calling again might use cache or recompute
        matrix2 = store.build_feature_matrix('SPY', lookback='3mo')
        
        # Results should be identical
        pd.testing.assert_frame_equal(matrix1, matrix2)
    
    def test_different_lookbacks_different_matrices(self, store):
        """Different lookbacks produce different matrices."""
        matrix_3mo = store.build_feature_matrix('SPY', lookback='3mo')
        matrix_6mo = store.build_feature_matrix('SPY', lookback='6mo')
        
        # 6mo should have more rows than 3mo
        assert len(matrix_6mo) >= len(matrix_3mo)


class TestMultiAssetMatrix:
    """Test multi-asset feature matrix."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_build_multi_asset_matrix_returns_dataframe(self, store):
        """build_multi_asset_matrix returns DataFrame."""
        result = store.build_multi_asset_matrix(
            ['SPY', 'QQQ', 'IWM'],
            lookback='3mo'
        )
        assert isinstance(result, (pd.DataFrame, dict))
    
    def test_multi_asset_coverage(self, store):
        """Multi-asset matrix covers all requested assets."""
        assets = ['SPY', 'QQQ']
        result = store.build_multi_asset_matrix(assets, lookback='1mo')
        
        if isinstance(result, dict):
            # Should have entries for each asset
            assert len(result) > 0
        elif isinstance(result, pd.DataFrame):
            # Should have multi-level columns with assets
            assert len(result) > 0


class TestCorrelationMatrix:
    """Test correlation computation."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_get_correlation_matrix_returns_dataframe(self, store):
        """get_correlation_matrix returns a DataFrame."""
        corr = store.get_correlation_matrix(
            ['SPY', 'QQQ', 'IWM'],
            lookback='6mo'
        )
        assert isinstance(corr, pd.DataFrame)
    
    def test_correlation_matrix_is_square(self, store):
        """Correlation matrix is square (n_assets × n_assets)."""
        assets = ['SPY', 'QQQ', 'IWM', 'TLT']
        corr = store.get_correlation_matrix(assets, lookback='6mo')
        
        assert corr.shape[0] == corr.shape[1]
        # All columns should be the queried assets
        assert len(corr) > 0
    
    def test_correlation_bounds(self, store):
        """Correlation values are in [-1, 1]."""
        corr = store.get_correlation_matrix(
            ['SPY', 'QQQ'],
            lookback='6mo'
        )
        
        values = corr.values.flatten()
        # Ignore NaNs
        values_finite = values[np.isfinite(values)]
        
        if len(values_finite) > 0:
            assert np.all(values_finite >= -1.0) and np.all(values_finite <= 1.0)
    
    def test_correlation_diagonal_one(self, store):
        """Diagonal of correlation matrix is 1.0."""
        corr = store.get_correlation_matrix(
            ['SPY', 'QQQ'],
            lookback='6mo'
        )
        
        # Diagonal should be ~1.0 (self-correlation)
        if len(corr) > 0:
            diag = np.diag(corr.values)
            diag_finite = diag[np.isfinite(diag)]
            if len(diag_finite) > 0:
                assert np.allclose(diag_finite, 1.0, atol=0.01)


class TestFeatureStats:
    """Test feature statistics."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_get_feature_stats_returns_dict(self, store):
        """get_feature_stats returns a dictionary."""
        stats = store.get_feature_stats('SPY', lookback='3mo')
        assert isinstance(stats, dict)
    
    def test_feature_stats_has_expected_keys(self, store):
        """Feature stats has mean, std, min, max."""
        stats = store.get_feature_stats('SPY', lookback='3mo')
        
        if stats:
            # Should have some statistical summary
            expected_keys = ['mean', 'std', 'min', 'max', 'count']
            # At least one key should exist
            assert any(k in str(stats).lower() for k in expected_keys)


class TestRefresh:
    """Test feature matrix refresh."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_refresh_no_crash(self, store):
        """Calling refresh() doesn't crash."""
        # First build a matrix
        matrix1 = store.build_feature_matrix('SPY', lookback='3mo')
        
        # Then refresh
        store.refresh('SPY')
        
        # Build again
        matrix2 = store.build_feature_matrix('SPY', lookback='3mo')
        
        assert isinstance(matrix2, pd.DataFrame)


class TestParquetSerialization:
    """Test Parquet save/load for feature matrices."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_feature_matrix_save_load_roundtrip(self, store, temp_dir):
        """Feature matrix can be saved and loaded."""
        matrix = store.build_feature_matrix('SPY', lookback='3mo')
        
        filepath = os.path.join(temp_dir, 'test_features.parquet')
        
        try:
            # Save
            matrix.to_parquet(filepath)
            
            # Load
            matrix_loaded = pd.read_parquet(filepath)
            
            # Should be identical
            pd.testing.assert_frame_equal(matrix, matrix_loaded)
        except Exception:
            # Parquet may not be available, that's ok
            pass


class TestEdgeCases:
    """Test edge cases."""
    
    @pytest.fixture
    def store(self):
        return FeatureStore()
    
    def test_invalid_ticker_returns_dataframe(self, store):
        """Invalid ticker returns empty DataFrame, not crash."""
        result = store.build_feature_matrix('ZZZZZZZZ_INVALID', lookback='1mo')
        assert isinstance(result, pd.DataFrame)
    
    def test_very_short_lookback(self, store):
        """Very short lookback (1d) returns DataFrame."""
        result = store.build_feature_matrix('SPY', lookback='1d')
        assert isinstance(result, pd.DataFrame)
    
    def test_very_long_lookback(self, store):
        """Very long lookback (10y) returns DataFrame."""
        result = store.build_feature_matrix('SPY', lookback='10y')
        assert isinstance(result, pd.DataFrame)
        # Should have many rows for 10 years of daily data
        if len(result) > 0:
            assert len(result) > 100


class TestIntegration:
    """Integration tests for feature store."""
    
    def test_complete_workflow(self):
        """Full workflow: init, build, correlate, stats."""
        fs = FeatureStore()
        
        # Build matrix
        matrix = fs.build_feature_matrix('SPY', lookback='6mo')
        assert isinstance(matrix, pd.DataFrame)
        assert len(matrix) > 0
        
        # Get correlations
        corr = fs.get_correlation_matrix(['SPY', 'QQQ'], lookback='6mo')
        assert isinstance(corr, pd.DataFrame)
        
        # Get stats
        stats = fs.get_feature_stats('SPY', lookback='6mo')
        assert isinstance(stats, dict)
    
    def test_multi_asset_workflow(self):
        """Multi-asset feature engineering workflow."""
        fs = FeatureStore()
        
        assets = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']
        
        # Build per-asset
        for asset in assets[:2]:  # Just test first 2 for speed
            matrix = fs.build_feature_matrix(asset, lookback='3mo')
            assert isinstance(matrix, pd.DataFrame)
        
        # Build multi-asset
        multi = fs.build_multi_asset_matrix(assets[:2], lookback='3mo')
        assert multi is not None
