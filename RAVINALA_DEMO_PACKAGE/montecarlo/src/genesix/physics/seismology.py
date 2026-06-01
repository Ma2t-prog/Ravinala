"""
Financial seismology — markets crash like earthquakes.

Two empirical laws from geophysics apply directly to financial markets:

1. Gutenberg-Richter law: log₁₀(N(>m)) = a - b×m
   The frequency of events of magnitude m follows a power law.
   In markets: the probability of a return of magnitude |r| scales as |r|^(-α).
   α ≈ 3 for equities ("inverse cubic law" — Gopikrishnan et al., 1999).

2. Omori law: aftershock rate n(t) = K / (c + t)^p
   After a mainshock, aftershocks decay as a power law in time.
   In markets: after a crash, volatility decays as (t - t_crash)^{-p}.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, curve_fit
from scipy.stats import kstest
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GutenbergRichter:
    """Power law analysis of market return magnitudes."""
    
    def fit_power_law(self, returns: np.ndarray, x_min: Optional[float] = None) -> dict:
        """
        Fit power law to the tail of the return distribution via MLE.
        
        Args:
            returns: absolute returns or raw returns
            x_min: minimum threshold for power law regime (auto-detect if None)
        
        Returns:
            {
                'alpha': float,
                'x_min': float,
                'n_tail': int,
                'ks_statistic': float,
                'ks_pvalue': float,
                'log_likelihood': float,
                'tail_risk_assessment': {...},
                'interpretation': str,
            }
        """
        abs_returns = np.abs(returns[~np.isnan(returns) & ~np.isinf(returns)])
        
        if len(abs_returns) < 10:
            return self._empty_fit()
        
        # Find optimal x_min if not provided
        if x_min is None:
            x_min = self._find_optimal_xmin(abs_returns)
        
        # Filter to tail
        tail_data = abs_returns[abs_returns >= x_min]
        n_tail = len(tail_data)
        
        if n_tail < 5:
            return {'alpha': np.nan, 'x_min': x_min, 'n_tail': 0, 
                    'ks_statistic': np.nan, 'ks_pvalue': 0, 'log_likelihood': np.nan,
                    'tail_risk_assessment': {}, 'interpretation': 'Insufficient tail data'}
        
        # MLE: α = 1 + n / Σ ln(r_i / x_min)
        alpha = 1.0 + n_tail / np.sum(np.log(tail_data / x_min))
        
        # Log-likelihood
        log_likelihood = -n_tail * np.log(alpha) - (alpha + 1) * np.sum(np.log(tail_data / x_min))
        
        # KS test: compare empirical vs theoretical CDF
        theoretical_cdf = 1 - (x_min / tail_data) ** (alpha - 1)
        empirical_cdf = np.arange(1, len(tail_data) + 1) / len(tail_data)
        ks_stat, ks_pval = kstest(empirical_cdf, theoretical_cdf)
        
        # Tail risk assessment
        current_percentile = np.percentile(abs_returns, 25) if len(abs_returns) > 0 else 0
        tail_risk = 'normal' if 2.5 < alpha < 4 else ('fat_tails' if alpha < 2.5 else 'thin_tails')
        
        interpretation = f"Tail exponent α = {alpha:.2f}. "
        if alpha < 1.5:
            interpretation += "EXTREME FAT TAILS — tail risk is EXTREME."
        elif 1.5 <= alpha < 2.5:
            interpretation += "Very fat tails — tail risk is ELEVATED."
        elif 2.5 <= alpha < 3.5:
            interpretation += "Typical for equities — tail risk is NORMAL."
        else:
            interpretation += "Thin tails — tail risk is LOW."
        
        return {
            'alpha': float(alpha),
            'x_min': float(x_min),
            'n_tail': int(n_tail),
            'ks_statistic': float(ks_stat),
            'ks_pvalue': float(ks_pval),
            'log_likelihood': float(log_likelihood),
            'tail_risk_assessment': {
                'current_alpha': float(alpha),
                'regime': tail_risk,
            },
            'interpretation': interpretation,
        }
    
    def rolling_alpha(self, returns: np.ndarray, window: int = 252) -> pd.Series:
        """Rolling tail exponent over time."""
        alphas = []
        for i in range(window, len(returns)):
            window_returns = returns[i-window:i]
            result = self.fit_power_law(window_returns)
            alphas.append(result['alpha'])
        
        return pd.Series(alphas, index=range(window, len(returns)))
    
    def compare_tails_vs_gaussian(self, returns: np.ndarray) -> dict:
        """Quantify how much fatter the tails are vs Gaussian."""
        abs_returns = np.abs(returns[~np.isnan(returns) & ~np.isinf(returns)])
        sigma = np.std(abs_returns)
        
        if sigma == 0:
            return {}
        
        thresholds = [1, 2, 3, 4, 5]
        results = {
            'thresholds': thresholds,
            'gaussian_expected_pct': [],
            'observed_pct': [],
            'ratio': [],
        }
        
        from scipy.stats import norm
        for t in thresholds:
            # Gaussian tail probability
            gaussian_prob = 2 * (1 - norm.cdf(t))
            
            # Observed
            observed_count = np.sum(abs_returns > t * sigma)
            observed_prob = observed_count / len(abs_returns)
            
            results['gaussian_expected_pct'].append(gaussian_prob * 100)
            results['observed_pct'].append(observed_prob * 100)
            
            if gaussian_prob > 0:
                results['ratio'].append(observed_prob / gaussian_prob)
            else:
                results['ratio'].append(np.inf)
        
        return results
    
    def _find_optimal_xmin(self, data: np.ndarray) -> float:
        """Find x_min that minimizes KS statistic."""
        sorted_data = np.sort(data[data > 0])
        if len(sorted_data) < 10:
            return np.percentile(sorted_data, 5)
        
        # Search over percentiles
        best_ks = np.inf
        best_xmin = sorted_data[0]
        
        for percentile in range(5, 30, 5):
            xmin = np.percentile(sorted_data, percentile)
            tail = sorted_data[sorted_data >= xmin]
            
            if len(tail) < 5:
                continue
            
            alpha = 1 + len(tail) / np.sum(np.log(tail / xmin))
            if alpha <= 0 or alpha > 5:
                continue
            
            # KS distance
            theoretical_cdf = 1 - (xmin / tail) ** (alpha - 1)
            empirical_cdf = np.arange(1, len(tail) + 1) / len(tail)
            ks_stat = np.max(np.abs(empirical_cdf - theoretical_cdf))
            
            if ks_stat < best_ks:
                best_ks = ks_stat
                best_xmin = xmin
        
        return float(best_xmin)
    
    def _empty_fit(self) -> dict:
        return {
            'alpha': np.nan,
            'x_min': np.nan,
            'n_tail': 0,
            'ks_statistic': np.nan,
            'ks_pvalue': 0,
            'log_likelihood': np.nan,
            'tail_risk_assessment': {},
            'interpretation': 'Unable to fit',
        }


class OmoriAftershock:
    """Omori law for post-crash volatility decay."""
    
    def detect_mainshock(self, returns: np.ndarray, threshold_sigma: float = 4.0) -> list[dict]:
        """Identify extreme moves (mainshocks)."""
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if len(returns_clean) < 2:
            return []
        
        mean_return = np.mean(returns_clean)
        std_return = np.std(returns_clean)
        
        if std_return == 0:
            return []
        
        shocks = []
        for i, r in enumerate(returns_clean):
            magnitude = (r - mean_return) / std_return
            if np.abs(magnitude) >= threshold_sigma:
                shocks.append({
                    'date_index': i,
                    'return': float(r),
                    'magnitude_sigma': float(magnitude),
                    'type': 'crash' if r < mean_return else 'rally',
                })
        
        return shocks
    
    def fit_omori(self, returns: np.ndarray, shock_index: int,
                   max_aftershock_window: int = 60) -> dict:
        """Fit Omori law to post-shock volatility decay."""
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if shock_index >= len(returns_clean) - 10:
            return self._empty_omori_fit()
        
        # Compute rolling volatility after shock
        window = 5
        post_shock_returns = returns_clean[shock_index:min(shock_index + max_aftershock_window, len(returns_clean))]
        
        vol_series = []
        for i in range(window, len(post_shock_returns)):
            window_vol = np.std(post_shock_returns[i-window:i])
            vol_series.append(window_vol)
        
        if len(vol_series) < 5:
            return self._empty_omori_fit()
        
        # Background volatility (pre-shock)
        pre_shock_vol = np.std(returns_clean[max(0, shock_index-60):shock_index])
        
        # Fit: σ(t) = A / (c + t)^p
        t_values = np.arange(1, len(vol_series) + 1, dtype=float)
        vol_array = np.array(vol_series)
        
        try:
            # Initial guess
            p0 = [vol_array[0], 1, 0.6]
            
            def omori_func(t, A, c, p):
                return A / (c + t) ** p
            
            popt, _ = curve_fit(omori_func, t_values, vol_array, p0=p0, 
                               bounds=([0.001, 0.001, 0.1], [1.0, 100, 2.0]))
            
            A, c, p = popt
            
            # Fit quality
            fitted_vol = omori_func(t_values, A, c, p)
            ss_res = np.sum((vol_array - fitted_vol) ** 2)
            ss_tot = np.sum((vol_array - np.mean(vol_array)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Forecast
            def days_to_level(target_excess, A, c, p, bg_vol):
                """Solve for t when excess vol drops to target."""
                target = bg_vol + target_excess
                # A / (c + t)^p = target → t = (A/target)^(1/p) - c
                try:
                    t_val = (A / target) ** (1/p) - c
                    return max(1, int(t_val))
                except:
                    return np.inf
            
            current_excess = vol_array[-1] - pre_shock_vol if pre_shock_vol > 0 else vol_array[-1]
            days_50pct = days_to_level(current_excess * 0.5, A, c, p, pre_shock_vol)
            days_90pct = days_to_level(current_excess * 0.1, A, c, p, pre_shock_vol)
            days_normal = days_to_level(current_excess * 0.1, A, c, p, pre_shock_vol)
            
            return {
                'A': float(A),
                'c': float(c),
                'p': float(p),
                'sigma_background': float(pre_shock_vol),
                'fit_r2': float(r2),
                'forecast': {
                    'current_excess_vol': float(current_excess),
                    'days_to_50pct_decay': int(days_50pct),
                    'days_to_90pct_decay': int(days_90pct),
                    'days_to_normal': int(days_normal),
                    'vol_forecast_next_5d': float(omori_func(5, A, c, p)),
                    'vol_forecast_next_20d': float(omori_func(20, A, c, p)),
                },
                'historical_comparison': f"p={p:.2f} (typical range 0.5-1.0)",
            }
        
        except Exception as e:
            logger.debug(f"Omori fit failed: {e}")
            return self._empty_omori_fit()
    
    def aftershock_forecast(self, returns: np.ndarray) -> dict:
        """Forecast aftershock timeline if active."""
        shocks = self.detect_mainshock(returns)
        
        if not shocks:
            return {
                'active_aftershock': False,
                'mainshock_date': None,
                'mainshock_magnitude': None,
                'days_since_shock': None,
                'current_phase': 'normal',
                'forecast': None,
                'recommendation': 'No recent mainshock detected.',
            }
        
        # Take the most recent shock
        last_shock = shocks[-1]
        days_since = len(returns) - last_shock['date_index']
        
        if days_since > 60:
            return {
                'active_aftershock': False,
                'mainshock_date': None,
                'mainshock_magnitude': last_shock['magnitude_sigma'],
                'days_since_shock': days_since,
                'current_phase': 'normal',
                'forecast': None,
                'recommendation': 'Previous shock was 2+ months ago. No active aftershock.',
            }
        
        # Fit Omori to this shock
        fit = self.fit_omori(returns, last_shock['date_index'])
        
        if 'forecast' not in fit or fit['fit_r2'] < 0.3:
            current_phase = 'acute' if days_since < 5 else 'decay'
        else:
            days_to_normal = fit['forecast']['days_to_normal']
            if days_since < days_to_normal * 0.3:
                current_phase = 'acute'
            elif days_since < days_to_normal * 0.7:
                current_phase = 'decay'
            else:
                current_phase = 'recovery'
        
        return {
            'active_aftershock': True,
            'mainshock_date': f'Index {last_shock["date_index"]}',
            'mainshock_magnitude': float(last_shock['magnitude_sigma']),
            'days_since_shock': days_since,
            'current_phase': current_phase,
            'forecast': fit.get('forecast'),
            'recommendation': self._phase_recommendation(current_phase, fit.get('forecast')),
        }
    
    def bath_law(self, mainshock_magnitude: float) -> dict:
        """Bath's law: largest aftershock is ~1.2 magnitudes smaller."""
        expected_aftershock = mainshock_magnitude - 1.2
        prob_exceeds = 1 - np.exp(-1.0)  # Omori integral over infinity
        
        return {
            'mainshock_magnitude_sigma': float(mainshock_magnitude),
            'expected_largest_aftershock_sigma': float(expected_aftershock),
            'expected_largest_aftershock_pct': float(expected_aftershock / mainshock_magnitude * 100),
            'probability_aftershock_exceeds_mainshock': float(prob_exceeds),
        }
    
    def _empty_omori_fit(self) -> dict:
        return {
            'A': np.nan,
            'c': np.nan,
            'p': np.nan,
            'sigma_background': np.nan,
            'fit_r2': 0,
            'forecast': None,
            'historical_comparison': '',
        }
    
    def _phase_recommendation(self, phase: str, forecast: Optional[dict]) -> str:
        """Return recommendation based on phase."""
        if phase == 'acute':
            return "ACUTE PHASE: Reduce position sizes. High uncertainty. Aftershock vol expected for weeks."
        elif phase == 'decay':
            days = forecast['days_to_normal'] if forecast else '?'
            return f"DECAY PHASE: Vol declining on schedule. Expected return to normal in ~{days} days."
        else:
            return "RECOVERY PHASE: Near normal. Monitor for delayed aftershocks."


class FinancialSeismograph:
    """Composite seismological analysis."""
    
    def __init__(self):
        self.gr = GutenbergRichter()
        self.omori = OmoriAftershock()
    
    def full_seismic_report(self, returns: pd.Series) -> dict:
        """Complete seismological analysis."""
        returns_array = returns.values
        
        # Tail exponent
        tail_fit = self.gr.fit_power_law(returns_array)
        
        # Comparison with Gaussian
        gaussian_compare = self.gr.compare_tails_vs_gaussian(returns_array)
        
        # Aftershock status
        aftershock_status = self.omori.aftershock_forecast(returns_array)
        
        # Composite seismic risk score
        alpha = tail_fit['alpha']
        if np.isnan(alpha):
            seismic_score = 25
        else:
            # Lower α = fatter tails = higher risk
            seismic_score = min(100, max(0, 100 * (4.0 - alpha) / 3.0))
        
        if aftershock_status['active_aftershock']:
            seismic_score = min(100, seismic_score + 25)
        
        return {
            'tail_exponent': {
                'current_alpha': tail_fit['alpha'],
                'tail_risk_regime': tail_fit['tail_risk_assessment'].get('regime', 'unknown'),
            },
            'aftershock_status': {
                'active': aftershock_status['active_aftershock'],
                'mainshock': aftershock_status['mainshock_magnitude'],
                'days_since': aftershock_status['days_since_shock'],
                'current_phase': aftershock_status['current_phase'],
            },
            'gaussian_comparison': gaussian_compare,
            'seismic_risk_score': float(seismic_score),
            'interpretation': f"{tail_fit['interpretation']} {aftershock_status['recommendation']}",
        }
