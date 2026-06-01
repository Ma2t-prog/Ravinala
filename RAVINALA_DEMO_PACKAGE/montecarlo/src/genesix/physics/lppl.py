"""
Log-Periodic Power Law (LPPL) — predicting when bubbles pop.

Didier Sornette showed that financial bubbles exhibit a mathematical signature:
ln(p(t)) = A + B(tc - t)^m + C(tc - t)^m × cos(ω × ln(tc - t) + φ)

where tc = critical time (crash date), m = power law exponent, ω = log-frequency.

The oscillations accelerate as t → tc (log-periodic acceleration).
This is the same pattern seen before earthquakes and material failure.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, least_squares
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LPPLModel:
    """LPPL bubble detection."""
    
    def fit(self, prices: pd.Series, window_days: int = 252) -> dict:
        """
        Fit LPPL model to price data via two-stage optimization.
        
        Returns:
            {
                'fit_found': bool,
                'parameters': {...},
                'fit_quality': {...},
                'fitted_values': pd.Series,
                'residuals': pd.Series,
            }
        """
        if len(prices) < window_days:
            return self._empty_fit()
        
        prices_windowed = prices.iloc[-window_days:].values
        log_prices = np.log(prices_windowed)
        t_values = np.arange(len(log_prices))
        
        if np.any(np.isnan(log_prices)) or np.any(np.isinf(log_prices)):
            return self._empty_fit()
        
        # Stage 1: Grid search over (tc, m, ω)
        best_r2 = -np.inf
        best_params = None
        
        # Search space
        last_t = len(log_prices) - 1
        tc_candidates = np.arange(last_t + 5, last_t + 121, 5)  # 5-120 days ahead
        m_candidates = np.linspace(0.1, 0.9, 9)
        omega_candidates = np.linspace(4, 15, 12)
        
        for tc in tc_candidates:
            for m in m_candidates:
                for omega in omega_candidates:
                    try:
                        # Stage 2: Solve for A, B, C, φ via linear regression
                        result = self._fit_linear_params(log_prices, t_values, tc, m, omega)
                        
                        if result is None:
                            continue
                        
                        A, B, C, phi, r2 = result
                        
                        # Validation filters
                        if B >= 0:  # B must be negative (bubble = price above fundamental)
                            continue
                        if abs(C) < 0.001:  # Must have oscillations
                            continue
                        if r2 < 0.75:  # Minimum fit quality
                            continue
                        
                        if r2 > best_r2:
                            best_r2 = r2
                            best_params = (tc, m, omega, A, B, C, phi, r2)
                    
                    except Exception:
                        continue
        
        if best_params is None or best_r2 < 0.75:
            return self._empty_fit()
        
        tc, m, omega, A, B, C, phi, r2 = best_params
        
        # Generate fitted values and residuals
        fitted = self._lppl_function(t_values, A, B, C, tc, m, omega, phi)
        residuals = log_prices - fitted
        residual_std = np.std(residuals)
        
        # Estimate parameter stability via bootstrap
        stability = self._bootstrap_stability(log_prices, t_values, tc, m, omega, n_bootstrap=20)
        
        return {
            'fit_found': True,
            'parameters': {
                'tc': float(tc),
                'tc_date': f'~{int(tc)} days ahead',
                'm': float(m),
                'omega': float(omega),
                'A': float(A),
                'B': float(B),
                'C': float(C),
                'phi': float(phi),
            },
            'fit_quality': {
                'r_squared': float(r2),
                'residual_std': float(residual_std),
                'parameter_stability': float(stability),
            },
            'fitted_values': pd.Series(fitted, index=prices.iloc[-window_days:].index),
            'residuals': pd.Series(residuals, index=prices.iloc[-window_days:].index),
        }
    
    def bubble_confidence(self, prices: pd.Series, n_bootstrap: int = 50,
                         n_windows: int = 5) -> dict:
        """
        Estimate confidence of bubble detection via multi-window bootstrap.
        
        Returns:
            {
                'bubble_detected': bool,
                'confidence': float,
                'tc_estimate': str | None,
                'tc_range': (str, str) | None,
                'days_to_critical': int | None,
                'risk_level': 'none'|'low'|'moderate'|'high'|'extreme',
                'interpretation': str,
            }
        """
        window_sizes = [252, 378, 504, 630, 756]  # 1y, 1.5y, 2y, 2.5y, 3y
        
        fits_found = 0
        tc_estimates = []
        confidence_scores = []
        
        for window_size in window_sizes:
            if len(prices) < window_size:
                continue
            
            fit = self.fit(prices, window_days=window_size)
            
            if not fit['fit_found']:
                continue
            
            fits_found += 1
            r2 = fit['fit_quality']['r_squared']
            stability = fit['fit_quality']['parameter_stability']
            
            # Confidence = fit quality × parameter stability
            confidence_score = r2 * stability
            confidence_scores.append(confidence_score)
            tc_estimates.append(fit['parameters']['tc'])
        
        if fits_found == 0:
            return {
                'bubble_detected': False,
                'confidence': 0.0,
                'tc_estimate': None,
                'tc_range': None,
                'days_to_critical': None,
                'risk_level': 'none',
                'interpretation': 'No LPPL pattern detected.',
            }
        
        avg_confidence = np.mean(confidence_scores)
        median_tc = np.median(tc_estimates)
        tc_std = np.std(tc_estimates)
        
        # Map confidence to risk level
        if avg_confidence < 0.3:
            risk_level = 'none'
        elif avg_confidence < 0.5:
            risk_level = 'low'
        elif avg_confidence < 0.65:
            risk_level = 'moderate'
        elif avg_confidence < 0.80:
            risk_level = 'high'
        else:
            risk_level = 'extreme'
        
        tc_lower = int(median_tc - 1.96 * tc_std)
        tc_upper = int(median_tc + 1.96 * tc_std)
        
        interpretation = (
            f"LPPL bubble pattern detected with {avg_confidence*100:.0f}% confidence. "
            f"Critical time: ~{int(median_tc)} ± {int(tc_std)} days. "
            f"Risk level: {risk_level.upper()}. "
            "CAUTION: LPPL has ~30% false positive rate. Use alongside other indicators."
        )
        
        return {
            'bubble_detected': avg_confidence > 0.4,
            'confidence': float(avg_confidence),
            'tc_estimate': f'{int(median_tc)} days',
            'tc_range': (f'{tc_lower} days', f'{tc_upper} days'),
            'days_to_critical': int(median_tc),
            'multi_window_results': [
                {
                    'window_days': int(window_sizes[i]),
                    'fit_found': i < len(confidence_scores),
                    'confidence': float(confidence_scores[i]) if i < len(confidence_scores) else 0,
                }
                for i in range(len(window_sizes))
            ],
            'risk_level': risk_level,
            'interpretation': interpretation,
        }
    
    def scan_universe(self, asset_prices: dict[str, pd.Series], lookback: str = '2y') -> list[dict]:
        """Scan multiple assets for LPPL bubble patterns."""
        results = []
        
        for asset, prices in asset_prices.items():
            try:
                conf = self.bubble_confidence(prices.tail(504))  # 2-year max
                
                if conf['confidence'] > 0.2:
                    results.append({
                        'asset': asset,
                        'confidence': conf['confidence'],
                        'risk_level': conf['risk_level'],
                        'tc_estimate': conf['tc_estimate'],
                        'days_to_critical': conf['days_to_critical'],
                    })
            
            except Exception as e:
                logger.debug(f"LPPL scan failed for {asset}: {e}")
                continue
        
        # Sort by confidence descending
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results
    
    def visualize_fit(self, prices: pd.Series, fit_result: dict) -> dict:
        """Return data for Plotly visualization."""
        if not fit_result.get('fit_found'):
            return {}
        
        return {
            'dates': prices.index.strftime('%Y-%m-%d').tolist(),
            'actual_prices': prices.values.tolist(),
            'fitted_prices': fit_result['fitted_values'].values.tolist() if 'fitted_values' in fit_result else [],
            'tc_date': fit_result['parameters'].get('tc_date'),
        }
    
    def _lppl_function(self, t, A, B, C, tc, m, omega, phi):
        """LPPL model: ln(p) = A + B(tc-t)^m + C(tc-t)^m*cos(ω*ln(tc-t)+φ)"""
        power = np.maximum(tc - t, 0.001) ** m
        log_term = np.log(np.maximum(tc - t, 0.001))
        
        return A + B * power + C * power * np.cos(omega * log_term + phi)
    
    def _fit_linear_params(self, log_prices, t_values, tc, m, omega):
        """Linear regression to find A, B, C, φ given (tc, m, ω)."""
        power = np.maximum(tc - t_values, 0.001) ** m
        log_term = np.log(np.maximum(tc - t_values, 0.001))
        
        cos_term = np.cos(omega * log_term)
        sin_term = np.sin(omega * log_term)
        
        # Design matrix: [1, power, power*cos, power*sin]
        X = np.column_stack([np.ones_like(t_values), power, power * cos_term, power * sin_term])
        
        try:
            # Linear least squares
            params, residuals, rank, _ = np.linalg.lstsq(X, log_prices, rcond=None)
            
            A, B, C_cos, C_sin = params
            
            # Convert back
            C = np.sqrt(C_cos**2 + C_sin**2)
            phi = np.arctan2(C_sin, C_cos)
            
            # R-squared
            predicted = X @ params
            ss_res = np.sum((log_prices - predicted) ** 2)
            ss_tot = np.sum((log_prices - np.mean(log_prices)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            return A, B, C, phi, r2
        
        except Exception:
            return None
    
    def _bootstrap_stability(self, log_prices, t_values, tc, m, omega, n_bootstrap=20):
        """Estimate parameter stability via bootstrap."""
        stabilities = []
        
        for _ in range(n_bootstrap):
            # Resample with replacement
            indices = np.random.choice(len(log_prices), len(log_prices), replace=True)
            resampled_prices = log_prices[indices]
            
            result = self._fit_linear_params(resampled_prices, t_values, tc, m, omega)
            
            if result is not None:
                A, B, C, phi, r2 = result
                if r2 > 0.7:
                    stabilities.append(r2)
        
        return np.mean(stabilities) if stabilities else 0.5
    
    def _empty_fit(self) -> dict:
        return {
            'fit_found': False,
            'parameters': {},
            'fit_quality': {},
            'fitted_values': pd.Series(),
            'residuals': pd.Series(),
        }
