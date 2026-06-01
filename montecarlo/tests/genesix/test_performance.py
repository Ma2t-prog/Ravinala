"""Performance benchmarks to ensure operations complete in acceptable time."""

import time
import pytest
import numpy as np
from datetime import datetime


@pytest.mark.slow
class TestPerformance:
    """Performance benchmarks — operations should complete within time limits."""
    
    def test_feature_matrix_build_speed(self):
        """Feature matrix build should complete in <60 seconds (first time)."""
        from genesix.data.feature_store import FeatureStore
        
        fs = FeatureStore()
        
        start = time.time()
        matrix = fs.build_feature_matrix('SPY', lookback='6mo')
        elapsed = time.time() - start
        
        print(f"Feature matrix build: {elapsed:.2f}s")
        assert elapsed < 60, f"Feature matrix took {elapsed:.1f}s (limit: 60s)"
        assert len(matrix) > 50
    
    def test_var_computation_speed(self):
        """VaR computations should complete in <5 seconds."""
        from genesix.risk.risk_engine import GenesiXRiskEngine
        
        engine = GenesiXRiskEngine(n_simulations=5000)
        returns = np.random.normal(0.0005, 0.015, 504)
        
        start = time.time()
        _ = engine.var_historical(returns, confidence=0.95, horizon=1)
        _ = engine.var_parametric(returns, confidence=0.95, horizon=1)
        _ = engine.var_cornish_fisher(returns, confidence=0.95, horizon=1)
        _ = engine.var_monte_carlo(returns, confidence=0.95, horizon=1, investment=1000)
        elapsed = time.time() - start
        
        print(f"All VaR methods: {elapsed:.2f}s")
        assert elapsed < 5, f"VaR methods took {elapsed:.1f}s (limit: 5s)"
    
    def test_monte_carlo_speed(self):
        """Monte Carlo simulation should complete in <10 seconds."""
        from genesix.risk.risk_engine import GenesiXRiskEngine
        
        engine = GenesiXRiskEngine(n_simulations=10000)
        returns = np.random.normal(0.0005, 0.015, 252)
        
        start = time.time()
        _ = engine.simulate_return_scenarios(returns, horizon=5, investment=1000, n_scenarios=5)
        elapsed = time.time() - start
        
        print(f"Monte Carlo 10k sims: {elapsed:.2f}s")
        assert elapsed < 10, f"Monte Carlo took {elapsed:.1f}s (limit: 10s)"
    
    def test_portfolio_analytics_speed(self):
        """Portfolio analytics should complete in <15 seconds."""
        from genesix.risk.portfolio import PortfolioRiskAnalyzer
        
        analyzer = PortfolioRiskAnalyzer()
        weights = {'SPY': 0.5, 'TLT': 0.3, 'GC=F': 0.2}
        
        start = time.time()
        _ = analyzer.portfolio_analytics(weights, portfolio_value=10000, horizon=5)
        elapsed = time.time() - start
        
        print(f"Portfolio analytics: {elapsed:.2f}s")
        assert elapsed < 15, f"Portfolio analytics took {elapsed:.1f}s (limit: 15s)"
    
    def test_ml_training_speed(self):
        """ML ensemble training should complete in <120 seconds."""
        from genesix.ml.prediction_engine import GenesiXPredictor
        
        predictor = GenesiXPredictor(models=['random_forest'])  # Fastest model
        
        start = time.time()
        _ = predictor.train_ensemble('SPY', horizon=5)
        elapsed = time.time() - start
        
        print(f"ML training (RF only): {elapsed:.2f}s")
        assert elapsed < 120, f"ML training took {elapsed:.1f}s (limit: 120s)"
    
    def test_ml_prediction_speed(self):
        """Prediction (after training) should complete in <5 seconds."""
        from genesix.ml.prediction_engine import GenesiXPredictor
        
        predictor = GenesiXPredictor(models=['random_forest'])
        _ = predictor.train_ensemble('SPY', horizon=5)
        
        start = time.time()
        _ = predictor.ensemble_predict('SPY', horizon=5, investment=1000)
        elapsed = time.time() - start
        
        print(f"ML prediction: {elapsed:.2f}s")
        assert elapsed < 5, f"Prediction took {elapsed:.1f}s (limit: 5s)"
    
    def test_anomaly_detection_speed(self):
        """Anomaly detection should complete in <5 seconds."""
        from genesix.ml.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector()
        
        start = time.time()
        _ = detector.composite_alert_level()
        elapsed = time.time() - start
        
        print(f"Anomaly detection: {elapsed:.2f}s")
        assert elapsed < 5, f"Anomaly detection took {elapsed:.1f}s (limit: 5s)"
    
    def test_pdf_generation_speed(self):
        """PDF generation should complete in <10 seconds."""
        from genesix.export.pdf_report import GenesiXReport
        
        results = {
            'prediction': {
                'expected_return_pct': 1.0,
                'worst_case_pct': -3.0,
                'best_case_pct': 5.0,
                'probability_positive': 0.60,
            },
            'risk_metrics': {
                'var_95': 0.02,
                'cvar_95': 0.03,
                'volatility_annualized': 0.15,
                'sharpe_ratio': 0.7,
                'max_drawdown': 0.10,
                'diversification_ratio': 1.1,
            },
            'scenarios': [
                {'name': 'Base', 'probability': 0.6, 'return_pct': 1.0, 'final_value': 1010},
            ],
            'alert_level': {'level': 'green'},
        }
        
        report = GenesiXReport("Test")
        
        start = time.time()
        _ = report.generate(results, {'SPY': 1.0}, 1000)
        elapsed = time.time() - start
        
        print(f"PDF generation: {elapsed:.2f}s")
        assert elapsed < 10, f"PDF generation took {elapsed:.1f}s (limit: 10s)"
    
    def test_excel_generation_speed(self):
        """Excel generation should complete in <5 seconds."""
        from genesix.export.excel_export import export_to_excel
        
        results = {
            'prediction': {
                'expected_return_pct': 1.0,
                'worst_case_pct': -3.0,
                'best_case_pct': 5.0,
                'probability_positive': 0.60,
            },
            'risk_metrics': {
                'var_95': 0.02,
                'cvar_95': 0.03,
                'volatility_annualized': 0.15,
                'sharpe_ratio': 0.7,
                'max_drawdown': 0.10,
                'diversification_ratio': 1.1,
            },
            'scenarios': [
                {'name': 'Base', 'probability': 0.6, 'return_pct': 1.0, 'final_value': 1010},
            ],
        }
        
        start = time.time()
        _ = export_to_excel(results, {'SPY': 1.0}, 1000)
        elapsed = time.time() - start
        
        print(f"Excel generation: {elapsed:.2f}s")
        assert elapsed < 5, f"Excel generation took {elapsed:.1f}s (limit: 5s)"
    
    def test_concurrent_feature_builds(self):
        """Building features for multiple assets concurrently."""
        from genesix.data.feature_store import FeatureStore
        import concurrent.futures
        
        fs = FeatureStore()
        tickers = ['SPY', 'TLT', 'GC=F']
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(fs.build_feature_matrix, ticker, '6mo')
                for ticker in tickers
            ]
            results = [f.result() for f in futures]
        elapsed = time.time() - start
        
        print(f"Concurrent feature builds (3 assets): {elapsed:.2f}s")
        assert elapsed < 120, f"Concurrent builds took {elapsed:.1f}s (limit: 120s)"
        assert len(results) == 3


@pytest.mark.slow
class TestMemoryUsage:
    """Basic memory efficiency checks."""
    
    def test_feature_matrix_memory(self):
        """Feature matrix shouldn't consume excessive memory."""
        from genesix.data.feature_store import FeatureStore
        import sys
        
        fs = FeatureStore()
        matrix = fs.build_feature_matrix('SPY', lookback='1y')
        
        memory_mb = sys.getsizeof(matrix) / 1024 / 1024
        print(f"Feature matrix memory: {memory_mb:.2f} MB")
        
        # Should be reasonable — 1y of SPY ~ 250 rows, 50+ features
        assert memory_mb < 50, f"Feature matrix using {memory_mb:.1f} MB (limit: 50 MB)"
    
    def test_ml_model_memory(self):
        """Trained ML model shouldn't be excessively large."""
        from genesix.ml.prediction_engine import GenesiXPredictor
        import sys
        
        predictor = GenesiXPredictor(models=['random_forest'])
        predictor.train_ensemble('SPY', horizon=5)
        
        memory_mb = sys.getsizeof(predictor) / 1024 / 1024
        print(f"Predictor object memory: {memory_mb:.2f} MB")
        
        # Model object may be large but not obscene
        assert memory_mb < 200, f"Predictor using {memory_mb:.1f} MB (limit: 200 MB)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'slow'])
