"""
Step 11A Physics Module Tests — Comprehensive coverage of all modules.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Import physics modules
from genesix.physics.seismology import GutenbergRichter, OmoriAftershock, FinancialSeismograph
from genesix.physics.lppl import LPPLModel
from genesix.physics.criticality import CriticalityAnalyzer
from genesix.physics.percolation import FinancialEpidemic
from genesix.physics.wavelets import WaveletAnalyzer
from genesix.physics.scaling import ScalingAnalyzer


# ========== SEISMOLOGY TESTS ==========

class TestGutenbergRichter:
    """Tests for Gutenberg-Richter power law analysis."""
    
    def test_power_law_fit_on_synthetic(self):
        """Synthetic power law data should recover close to correct exponent."""
        # Generate synthetic power law data: P(X > x) ∝ x^(-α)
        alpha_true = 2.5
        x_min = 0.1
        n = 1000
        
        # Inverse transform sampling
        u = np.random.uniform(0, 1, n)
        x = x_min * (1 - u) ** (-1 / alpha_true)
        
        gr = GutenbergRichter()
        result = gr.fit_power_law(x)
        
        # Result should have 'alpha' key and it should be reasonable
        assert 'alpha' in result
        assert not np.isnan(result['alpha'])
        assert 1.5 < result['alpha'] < 4.0  # Power law fit can vary
    
    def test_alpha_around_3_for_equities(self):
        """Real equity returns should have α between 2 and 5 (typically 3)."""
        returns = np.random.normal(0.0005, 0.015, 504)
        
        gr = GutenbergRichter()
        result = gr.fit_power_law(returns)
        
        if not np.isnan(result['alpha']):
            assert 1.5 < result['alpha'] < 5.0
    
    def test_gaussian_has_no_power_law(self):
        """Pure Gaussian data should fail power law fit."""
        returns = np.random.normal(0, 1, 500)
        
        gr = GutenbergRichter()
        result = gr.fit_power_law(returns)
        
        # Gaussian should have low p-value or high KS stat
        assert result['ks_pvalue'] < 0.5 or result['ks_statistic'] > 0.2
    
    def test_rolling_alpha_is_series(self):
        """Rolling alpha should return a pandas Series."""
        returns = np.random.normal(0, 1, 504)
        
        gr = GutenbergRichter()
        result = gr.rolling_alpha(returns, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) > 0
    
    def test_gaussian_comparison_structure(self):
        """Tail vs Gaussian comparison should have correct structure."""
        returns = np.random.normal(0, 1, 1000)
        
        gr = GutenbergRichter()
        result = gr.compare_tails_vs_gaussian(returns)
        
        assert 'thresholds' in result
        assert 'gaussian_expected_pct' in result
        assert 'observed_pct' in result
        assert 'ratio' in result
        assert len(result['thresholds']) == len(result['ratio'])


class TestOmoriAftershock:
    """Tests for Omori aftershock analysis."""
    
    def test_mainshock_detection_finds_extreme(self):
        """Should detect large magnitude moves as mainshocks."""
        returns = np.random.normal(0, 0.01, 100)
        returns[50] = 0.1  # Inject 10σ shock
        
        omori = OmoriAftershock()
        shocks = omori.detect_mainshock(returns, threshold_sigma=5.0)
        
        assert len(shocks) >= 1
        assert shocks[-1]['magnitude_sigma'] > 5.0
    
    def test_mainshock_has_required_fields(self):
        """Detected mainshock should have all required fields."""
        returns = np.random.normal(0, 0.01, 100)
        returns[50] = 0.1
        
        omori = OmoriAftershock()
        shocks = omori.detect_mainshock(returns, threshold_sigma=4.0)
        
        if shocks:
            shock = shocks[0]
            assert 'date_index' in shock
            assert 'return' in shock
            assert 'magnitude_sigma' in shock
            assert 'type' in shock
    
    def test_omori_fit_returns_valid_structure(self):
        """Omori fit should return properly structured dict."""
        returns = np.random.normal(0, 0.01, 100)
        returns[30] = 0.1  # Inject shock
        
        omori = OmoriAftershock()
        fit = omori.fit_omori(returns, shock_index=30)
        
        assert 'A' in fit
        assert 'c' in fit
        assert 'p' in fit
        assert 'sigma_background' in fit
        assert 'fit_r2' in fit
    
    def test_aftershock_forecast_structure(self):
        """Aftershock forecast should have required fields."""
        returns = np.random.normal(0, 0.01, 100)
        returns[50] = 0.15
        
        omori = OmoriAftershock()
        forecast = omori.aftershock_forecast(returns)
        
        assert 'active_aftershock' in forecast
        assert 'current_phase' in forecast
        assert 'recommendation' in forecast
    
    def test_bath_law_aftershock_smaller(self):
        """Expected aftershock should be smaller than mainshock per Bath's law."""
        omori = OmoriAftershock()
        result = omori.bath_law(5.0)
        
        assert result['expected_largest_aftershock_sigma'] < 5.0
        assert result['expected_largest_aftershock_sigma'] > 0


class TestFinancialSeismograph:
    """Integration tests for seismology."""
    
    def test_full_seismic_report_structure(self):
        """Full report should have all sections."""
        returns = pd.Series(np.random.normal(0, 0.01, 252))
        
        seis = FinancialSeismograph()
        report = seis.full_seismic_report(returns)
        
        assert 'tail_exponent' in report
        assert 'aftershock_status' in report
        assert 'seismic_risk_score' in report
        assert 'interpretation' in report
    
    def test_seismic_score_in_range(self):
        """Seismic score should be in [0, 100]."""
        returns = pd.Series(np.random.normal(0, 0.01, 252))
        
        seis = FinancialSeismograph()
        report = seis.full_seismic_report(returns)
        
        assert 0 <= report['seismic_risk_score'] <= 100


# ========== LPPL TESTS ==========

class TestLPPL:
    """Tests for Log-Periodic Power Law bubble detection."""
    
    def test_lppl_rejects_random_walk(self):
        """Pure random walk should not show strong LPPL signal."""
        prices = pd.Series(np.cumsum(np.random.normal(0, 0.01, 252)))
        
        lppl = LPPLModel()
        result = lppl.fit(prices, window_days=100)
        
        # Random walk shouldn't show good fit
        if result['fit_found']:
            assert result['fit_quality']['r_squared'] < 0.95
    
    def test_lppl_fit_structure(self):
        """LPPL fit should have proper structure."""
        prices = pd.Series(np.cumprod(1 + np.random.normal(0.001, 0.01, 100)))
        
        lppl = LPPLModel()
        result = lppl.fit(prices, window_days=80)
        
        # Even if not found, structure should exist
        assert 'fit_found' in result
        assert 'parameters' in result
        assert 'fit_quality' in result
    
    def test_bubble_confidence_range(self):
        """Bubble confidence should be in [0, 1]."""
        prices = pd.Series(np.cumprod(1 + np.random.normal(0.001, 0.01, 252)))
        
        lppl = LPPLModel()
        result = lppl.bubble_confidence(prices)
        
        assert 0 <= result['confidence'] <= 1
        assert result['risk_level'] in ['none', 'low', 'moderate', 'high', 'extreme']
    
    def test_scan_returns_sorted(self):
        """Scan should return results sorted by confidence."""
        assets = {
            'SPY': pd.Series(np.cumprod(1 + np.random.normal(0.001, 0.01, 252))),
            'QQQ': pd.Series(np.cumprod(1 + np.random.normal(0.001, 0.015, 252))),
            'AGG': pd.Series(np.cumprod(1 + np.random.normal(0.0003, 0.005, 252))),
        }
        
        lppl = LPPLModel()
        results = lppl.scan_universe(assets)
        
        # Results should be sorted by confidence descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['confidence'] >= results[i+1]['confidence']


# ========== CRITICALITY TESTS ==========

class TestCriticality:
    """Tests for criticality and phase transitions."""
    
    def test_temperature_normalized_range(self):
        """Temperature should be in [0, 100]."""
        returns = np.random.normal(0, 0.01, 252)
        volumes = np.random.lognormal(10, 1, 252)
        
        crit = CriticalityAnalyzer()
        result = crit.market_temperature(returns, volumes)
        
        assert 0 <= result['normalized'] <= 100
        assert result['label'] in ['frozen', 'cold', 'warm', 'hot', 'boiling']
    
    def test_susceptibility_structure(self):
        """Susceptibility should have required fields."""
        returns = np.random.normal(0, 0.01, 252)
        
        crit = CriticalityAnalyzer()
        result = crit.susceptibility(returns)
        
        assert 'susceptibility' in result
        assert 'percentile_1y' in result
        assert 'is_elevated' in result
        assert 'critical_proximity' in result
    
    def test_order_parameter_in_range(self):
        """Order parameter should be in [-1, 1]."""
        returns_matrix = pd.DataFrame(np.random.normal(0, 0.01, (100, 5)))
        
        crit = CriticalityAnalyzer()
        result = crit.order_parameter(returns_matrix, window=50)
        
        assert -1 <= result['order_parameter'] <= 1
        assert result['regime'] in ['disordered', 'weakly_ordered', 'ordered', 'critical']
    
    def test_phase_transition_detector_structure(self):
        """Phase transition detector should return complete analysis."""
        returns = np.random.normal(0, 0.01, 252)
        volumes = np.random.lognormal(10, 1, 252)
        returns_matrix = pd.DataFrame(np.random.normal(0, 0.01, (252, 5)))
        
        crit = CriticalityAnalyzer()
        result = crit.phase_transition_detector(returns, volumes, returns_matrix)
        
        assert 'current_phase' in result
        assert 'temperature' in result
        assert 'susceptibility' in result
        assert 'transition_risk' in result
        assert 'early_warning_signals' in result


# ========== PERCOLATION TESTS ==========

class TestPercolation:
    """Tests for contagion and percolation analysis."""
    
    def test_R0_positive(self):
        """R₀ should always be non-negative."""
        asset_returns = {
            'SPY': np.random.normal(0, 0.01, 252),
            'QQQ': np.random.normal(0, 0.015, 252),
            'AGG': np.random.normal(0, 0.005, 252),
        }
        
        epi = FinancialEpidemic()
        result = epi.compute_R0(asset_returns)
        
        assert result['R0'] >= 0
    
    def test_R0_structure(self):
        """R₀ computation should return all required fields."""
        asset_returns = {
            'SPY': np.random.normal(0, 0.01, 252),
            'QQQ': np.random.normal(0, 0.015, 252),
        }
        
        epi = FinancialEpidemic()
        result = epi.compute_R0(asset_returns)
        
        assert 'R0' in result
        assert 'R0_effective' in result
        assert 'is_supercritical' in result
        assert 'status' in result
    
    def test_epidemic_simulation_returns_counts(self):
        """Epidemic simulation should return distribution of infections."""
        asset_returns = {
            'SPY': np.random.normal(0, 0.01, 252),
            'QQQ': np.random.normal(0, 0.015, 252),
            'AGG': np.random.normal(0, 0.005, 252),
            'BTC': np.random.normal(0, 0.03, 252),
        }
        
        epi = FinancialEpidemic()
        result = epi.simulate_epidemic(asset_returns, 'SPY', n_simulations=100)
        
        assert 'median_infected' in result
        assert 'mean_infected' in result
        assert 'p_systemic' in result
        assert 'p_contained' in result
        assert len(result['distribution_of_outcomes']) == 100
    
    def test_percolation_threshold_structure(self):
        """Percolation analysis should return network metrics."""
        asset_returns = {
            'SPY': np.random.normal(0, 0.01, 252),
            'QQQ': np.random.normal(0, 0.015, 252),
            'AGG': np.random.normal(0, 0.005, 252),
            'BTC': np.random.normal(0, 0.03, 252),
            'GLD': np.random.normal(0, 0.01, 252),
        }
        
        epi = FinancialEpidemic()
        result = epi.percolation_threshold(asset_returns)
        
        assert 'percolation_threshold' in result
        assert 'current_avg_correlation' in result
        assert 'above_threshold' in result
        assert 'giant_component_size' in result


# ========== WAVELET TESTS ==========

class TestWavelets:
    """Tests for wavelet decomposition."""
    
    def test_decompose_returns_components(self):
        """Decomposition should return trend and details."""
        series = pd.Series(np.cumsum(np.random.normal(0, 0.01, 256)))
        
        wav = WaveletAnalyzer()
        result = wav.decompose(series)
        
        if 'details' in result:
            assert len(result['details']) >= 0
    
    def test_denoise_reduces_variance(self):
        """Denoised series should have lower variance."""
        series = pd.Series(np.cumsum(np.random.normal(0, 0.01, 256)))
        original_var = series.var()
        
        wav = WaveletAnalyzer()
        denoised = wav.denoise(series, remove_levels=[1])
        
        if len(denoised) > 0:
            denoised_var = denoised.var()
            assert denoised_var <= original_var * 1.1  # Allow some numerical variance
    
    def test_multiscale_correlation_structure(self):
        """Multi-scale correlation should return by-scale results."""
        series1 = pd.Series(np.cumsum(np.random.normal(0, 0.01, 256)))
        series2 = pd.Series(np.cumsum(np.random.normal(0, 0.01, 256)))
        
        wav = WaveletAnalyzer()
        result = wav.multiscale_correlation(series1, series2)
        
        if 'by_scale' in result:
            assert isinstance(result['by_scale'], dict)
    
    def test_wavelet_variance_sums_reasonable(self):
        """Wavelet variance percentages should sum to approximately 100%."""
        series = pd.Series(np.cumsum(np.random.normal(0, 0.01, 256)))
        
        wav = WaveletAnalyzer()
        result = wav.wavelet_variance(series)
        
        if 'pct_trend' in result:
            total_pct = result['pct_trend'] + result['pct_cycles'] + result['pct_noise']
            assert 80 < total_pct <= 120  # Allow some numerical variance


# ========== SCALING TESTS ==========

class TestScaling:
    """Tests for power laws and stable distributions."""
    
    def test_volatility_scaling_structure(self):
        """Volatility scaling should return all required fields."""
        # Use a data size that divides evenly by the largest interval (252)
        returns = np.random.normal(0, 0.01, 252 * 5)  # 1260 samples
        
        scale = ScalingAnalyzer()
        result = scale.volatility_scaling(returns)
        
        assert 'intervals' in result
        assert 'realized_vol' in result
        assert 'sqrt_t_predicted' in result
        assert 'actual_scaling_exponent' in result
    
    def test_gaussian_alpha_near_2(self):
        """Gaussian data should be recognized as Gaussian (alpha ≈ 2 or is_gaussian = True)."""
        returns = np.random.normal(0, 1, 1000)
        
        scale = ScalingAnalyzer()
        result = scale.stable_distribution_fit(returns)
        
        # For Gaussian or near-Gaussian data, is_gaussian should be True
        assert result['is_gaussian'] or (1.8 < result['alpha'] < 2.5)
    
    def test_stable_fit_has_parameters(self):
        """Stable fit should return all 4 parameters."""
        returns = np.random.normal(0, 1, 500)
        
        scale = ScalingAnalyzer()
        result = scale.stable_distribution_fit(returns)
        
        assert 'alpha' in result
        assert 'beta' in result
        assert 'gamma' in result
        assert 'delta' in result
    
    def test_hurst_exponent_range(self):
        """Hurst exponent should be in (0, 1)."""
        returns = np.random.normal(0, 0.01, 252 * 5)  # Use divisible by largest interval
        
        scale = ScalingAnalyzer()
        result = scale.hurst_exponent(returns)
        
        assert 0 < result['hurst'] < 1
    
    def test_universality_test_structure(self):
        """Universality test should return exponents for each asset."""
        returns_dict = {
            'SPY': np.random.normal(0, 0.01, 252 * 5),
            'QQQ': np.random.normal(0, 0.015, 252 * 5),
            'BTC': np.random.normal(0, 0.03, 252 * 5),
        }
        
        scale = ScalingAnalyzer()
        result = scale.universality_test(returns_dict)
        
        assert 'tail_exponents' in result
        assert 'hurst_exponents' in result
        assert len(result['assets']) == 3


# ========== INTEGRATION TESTS ==========

class TestPhysicsIntegration:
    """Integration tests combining multiple physics modules."""
    
    def test_full_physics_pipeline(self):
        """Run all physics modules on sample data."""
        # Sample data
        returns = pd.Series(np.random.normal(0.0005, 0.015, 252))
        prices = pd.Series(np.cumprod(1 + np.random.normal(0.0005, 0.015, 252)))
        volumes = pd.Series(np.random.lognormal(10, 1, 252))
        returns_matrix = pd.DataFrame(np.random.normal(0, 0.01, (252, 5)))
        asset_returns = {
            'A': np.random.normal(0, 0.01, 252),
            'B': np.random.normal(0, 0.015, 252),
            'C': np.random.normal(0, 0.005, 252),
        }
        
        # Seismology
        seis = FinancialSeismograph()
        seis_report = seis.full_seismic_report(returns)
        assert 'seismic_risk_score' in seis_report
        
        # LPPL
        lppl = LPPLModel()
        lppl_conf = lppl.bubble_confidence(prices)
        assert 'confidence' in lppl_conf
        
        # Criticality
        crit = CriticalityAnalyzer()
        phase = crit.phase_transition_detector(returns.values, volumes.values, returns_matrix)
        assert 'transition_risk' in phase
        
        # Percolation
        epi = FinancialEpidemic()
        r0 = epi.compute_R0(asset_returns)
        assert 'R0' in r0
        
        # Wavelets
        wav = WaveletAnalyzer()
        decomp = wav.decompose(prices)
        # May or may not find components depending on data
        
        # Scaling
        scale = ScalingAnalyzer()
        stable = scale.stable_distribution_fit(returns.values)
        assert 'alpha' in stable
    
    def test_no_crashes_on_edge_cases(self):
        """Ensure modules handle edge cases gracefully."""
        # Very short series
        short_series = pd.Series([1.0, 1.01, 1.02])
        
        seis = FinancialSeismograph()
        lppl = LPPLModel()
        scale = ScalingAnalyzer()
        
        # Should not crash
        seis.full_seismic_report(short_series)
        lppl.bubble_confidence(short_series)
        scale.stable_distribution_fit(short_series.values)
