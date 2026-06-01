"""End-to-end integration tests for GenesiX.

These tests verify that the full pipeline works:
Data → Features → Risk → ML → Output
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestFullPipeline:
    """Test complete data → prediction pipeline."""
    
    def test_spy_feature_engineering(self):
        """Full pipeline for SPY: fetch → features."""
        from genesix.data.feature_store import FeatureStore
        
        fs = FeatureStore()
        matrix = fs.build_feature_matrix('SPY', lookback='6mo')
        
        assert len(matrix) > 50, "Need at least 50 rows"
        assert matrix.shape[1] > 20, "Need at least 20 features"
        assert not matrix.isnull().all().any(), "Should have valid features"
    
    def test_portfolio_risk_analysis(self):
        """Portfolio-level risk analysis."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        
        analyzer = PortfolioRiskAnalyzer()
        weights = {'SPY': 0.5, 'TLT': 0.5}
        
        analytics = analyzer.portfolio_analytics(weights, portfolio_value=1000, horizon=5)
        
        assert 'risk_metrics' in analytics
        assert 'var' in analytics['risk_metrics']
        assert analytics['risk_metrics']['diversification_ratio'] > 0
    
    def test_ml_prediction_pipeline(self):
        """ML prediction on single asset."""
        from genesix.ml.prediction_engine import GenesiXPredictor
        
        predictor = GenesiXPredictor(models=['random_forest'])
        
        # Train
        train_result = predictor.train_ensemble('SPY', horizon=5)
        assert train_result['ensemble_status'] == 'trained'
        
        # Predict
        prediction = predictor.ensemble_predict('SPY', horizon=5, investment=1000)
        assert 'scenarios' in prediction
        assert prediction['expected_return'] is not None
        assert -1.0 < prediction['expected_return'] < 1.0  # Reasonable range
    
    def test_anomaly_detection(self):
        """Anomaly detection system."""
        from genesix.ml.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector()
        alert = detector.composite_alert_level()
        
        assert alert['level'] in ['green', 'yellow', 'orange', 'red', 'black']
        assert 0 <= alert['score'] <= 100
        assert 'components' in alert
    
    def test_pdf_report_generation(self):
        """PDF report generation."""
        from genesix.export.pdf_report import GenesiXReport
        
        # Minimal results dict
        results = {
            'prediction': {
                'expected_return_pct': 1.5,
                'worst_case_pct': -3.0,
                'best_case_pct': 5.0,
                'probability_positive': 0.65,
            },
            'risk_metrics': {
                'var_95': 0.025,
                'cvar_95': 0.04,
                'volatility_annualized': 0.15,
                'sharpe_ratio': 0.8,
                'max_drawdown': 0.12,
                'diversification_ratio': 1.2,
            },
            'scenarios': [
                {'name': 'Crash', 'probability': 0.05, 'return_pct': -15, 'final_value': 850},
                {'name': 'Base', 'probability': 0.60, 'return_pct': 1.5, 'final_value': 1015},
                {'name': 'Bull', 'probability': 0.35, 'return_pct': 5, 'final_value': 1050},
            ],
            'model_info': {'confidence_score': 0.75},
            'top_concerns': ['VIX elevated', 'Fed uncertainty'],
            'alert_level': {'level': 'yellow'},
            'recommendations': ['Rebalance quarterly'],
        }
        
        report = GenesiXReport("Test Portfolio")
        pdf_bytes = report.generate(results, {'SPY': 0.6, 'TLT': 0.4}, 1000)
        
        assert len(pdf_bytes) > 2000, "PDF should be non-trivial"
        assert pdf_bytes[:4] == b'%PDF', "Should start with PDF magic bytes"
    
    def test_excel_export(self):
        """Excel export."""
        from genesix.export.excel_export import export_to_excel
        
        results = {
            'prediction': {
                'expected_return_pct': 1.0,
                'worst_case_pct': -2.0,
                'best_case_pct': 3.0,
                'probability_positive': 0.62,
            },
            'risk_metrics': {
                'var_95': 0.02,
                'cvar_95': 0.03,
                'volatility_annualized': 0.12,
                'sharpe_ratio': 0.75,
                'max_drawdown': 0.08,
                'diversification_ratio': 1.0,
            },
            'scenarios': [
                {'name': 'Base', 'probability': 0.5, 'return_pct': 1.0, 'final_value': 1010},
            ],
        }
        
        xlsx_bytes = export_to_excel(results, {'SPY': 1.0}, 1000)
        assert len(xlsx_bytes) > 1000
        # Verify it's valid XLSX (ZIP format)
        assert xlsx_bytes[:2] == b'PK'
    
    def test_caching_works(self):
        """Caching system works."""
        from genesix.cache import cached, clear_cache, cache_stats
        
        # Clear cache first
        clear_cache()
        
        # Create simple cached function
        @cached('test')
        def expensive_op(x):
            return pd.DataFrame({'value': range(x)})
        
        # First call (compute)
        result1 = expensive_op(10)
        assert len(result1) == 10
        
        # Second call (cached)
        result2 = expensive_op(10)
        assert len(result2) == 10
        assert result1.equals(result2)
        
        # Check cache stats
        stats = cache_stats()
        assert stats['num_files'] > 0


class TestEdgeCases:
    """Test edge cases and failure modes."""
    
    def test_single_day_data(self):
        """Handle case where only 1 day of data is available."""
        from genesix.risk.risk_engine import GenesiXRiskEngine
        
        engine = GenesiXRiskEngine()
        result = engine.var_historical(np.array([0.01]), confidence=0.95, horizon=1)
        # Should return 0 or NaN, not crash
        assert result >= 0 or np.isnan(result)
    
    def test_all_zero_returns(self):
        """Handle constant price (zero returns)."""
        from genesix.risk.risk_engine import GenesiXRiskEngine
        
        engine = GenesiXRiskEngine()
        result = engine.var_historical(np.zeros(100), confidence=0.95, horizon=1)
        assert result == 0.0 or np.isnan(result)
    
    def test_nan_filled_returns(self):
        """Handle series with many NaNs."""
        from genesix.risk.risk_engine import GenesiXRiskEngine
        
        engine = GenesiXRiskEngine()
        returns = np.array([0.01, np.nan, -0.02, np.nan, 0.005] * 20)
        # Should handle NaNs gracefully
        result = engine.var_historical(returns, confidence=0.95, horizon=1)
        assert isinstance(result, float)
    
    def test_portfolio_single_asset(self):
        """Single-asset portfolio (diversification_ratio should be ~1)."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        
        analyzer = PortfolioRiskAnalyzer()
        result = analyzer.portfolio_analytics({'SPY': 1.0}, 1000, 5)
        
        # Single asset → diversification ratio ≈ 1
        assert 0.9 < result['risk_metrics'].get('diversification_ratio', 0) < 1.2
    
    def test_extreme_weights(self):
        """Portfolio with one asset at 99%."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        
        analyzer = PortfolioRiskAnalyzer()
        weights = {'SPY': 0.99, 'TLT': 0.01}
        
        result = analyzer.portfolio_analytics(weights, 1000, 5)
        assert 'var' in result['risk_metrics']
    
    def test_empty_portfolio(self):
        """Empty portfolio should raise error."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        from genesix.exceptions import PortfolioError
        
        analyzer = PortfolioRiskAnalyzer()
        
        with pytest.raises((PortfolioError, ValueError)):
            analyzer.portfolio_analytics({}, 1000, 5)
    
    def test_weights_not_summing_to_one(self):
        """Weights that don't sum to 1 may be normalized or raise error."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        
        analyzer = PortfolioRiskAnalyzer()
        weights = {'SPY': 0.5, 'TLT': 0.3}  # Sum = 0.8
        
        # Should either normalize or raise error
        try:
            result = analyzer.portfolio_analytics(weights, 1000, 5)
            # If it works, result should be valid
            assert 'var' in result['risk_metrics']
        except (ValueError, ValueError):
            # If it raises, that's also acceptable
            pass


class TestErrorHandling:
    """Test error handling and resilience."""
    
    def test_graceful_degradation_no_api_keys(self):
        """System works with zero API keys."""
        import os
        
        # Temporarily mock missing API keys
        keys = ['FRED_API_KEY', 'ALPHA_VANTAGE_KEY', 'NEWS_API_KEY']
        saved = {}
        for key in keys:
            saved[key] = os.environ.pop(key, None)
        
        try:
            from genesix.data.feature_store import FeatureStore
            fs = FeatureStore()
            # Should still work with yfinance
            matrix = fs.build_feature_matrix('SPY', lookback='3mo')
            assert len(matrix) > 30
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value
    
    def test_invalid_ticker_handling(self):
        """System handles invalid tickers gracefully."""
        from genesix.data.market_fetcher import MarketDataFetcher
        
        fetcher = MarketDataFetcher()
        
        # Invalid ticker
        with pytest.raises(Exception):  # DataFetchError or other
            fetcher.fetch_equities(['XYZXYZ12345INVALID'], period='1mo')
    
    def test_cache_corruption_recovery(self):
        """System recovers from corrupted cache files."""
        from genesix.cache import cached, clear_cache
        
        # Clear cache
        clear_cache()
        
        # Create and cache data
        @cached('test')
        def test_op(x):
            return pd.DataFrame({'col': [x] * 5})
        
        result1 = test_op(42)
        assert len(result1) == 5
        
        # Corrupt cache (write invalid parquet)
        from pathlib import Path
        cache_dir = Path('data/cache/test')
        if cache_dir.exists():
            parquet_files = list(cache_dir.glob('*.parquet'))
            if parquet_files:
                parquet_files[0].write_bytes(b'corrupted')
                
                # Function should recompute instead of crashing
                result2 = test_op(42)
                assert len(result2) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
