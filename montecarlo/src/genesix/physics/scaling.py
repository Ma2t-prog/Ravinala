"""
Scaling laws, stable distributions, and universality.

Markets exhibit universal power laws that are independent of asset,
market, or time period. Understanding these scaling laws reveals what
is possible and what is not.

Key concepts:
- Hurst exponent: how persistent is volatility
- Stable distributions: when variance is infinite
- Universality: all markets follow same scaling rules
"""

import numpy as np
import pandas as pd
import logging
from scipy.optimize import minimize
from scipy.stats import kstest

logger = logging.getLogger(__name__)


class ScalingAnalyzer:
    """Power laws and scaling analysis."""
    
    def volatility_scaling(self, returns: np.ndarray,
                          intervals: list[int] = [1, 5, 10, 21, 63, 126, 252]) -> dict:
        """
        Test whether volatility scales as σ(Δt) = σ₁ × Δt^H.
        
        For GBM: H = 0.5 (√T rule).
        For real markets: H ≠ 0.5 (longer-term risk differs from Square-root rule).
        """
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if len(returns_clean) < intervals[-1]:
            return self._empty_vol_scaling()
        
        realized_vol = []
        sqrt_t_predicted = []
        
        for interval in intervals:
            if len(returns_clean) < interval:
                continue
            
            # Trim to multiple of interval to allow reshape
            n_trim = (len(returns_clean) // interval) * interval
            interval_returns = returns_clean[:n_trim].reshape(-1, interval).sum(axis=1)
            vol = np.std(interval_returns)
            realized_vol.append(vol)
            
            # √T prediction (GBM)
            vol_1d = np.std(returns_clean)
            predicted = vol_1d * np.sqrt(interval)
            sqrt_t_predicted.append(predicted)
        
        if len(realized_vol) < 2:
            return self._empty_vol_scaling()
        
        # Fit: log(σ) = log(σ₁) + H × log(Δt)
        log_intervals = np.log(intervals[:len(realized_vol)])
        log_vols = np.log(realized_vol)
        
        # Linear regression
        coeffs = np.polyfit(log_intervals, log_vols, 1)
        H = coeffs[0]  # Slope
        
        sqrt_t_diffs = True
        if abs(H - 0.5) < 0.05:
            sqrt_t_diffs = False
        
        var_adjustment = (H / 0.5) if H > 0 else 1.0
        
        interpretation = f"Volatility scaling exponent H = {H:.2f}. "
        if H > 0.55:
            interpretation += "H > 0.5: long-term risk is HIGHER than √T suggests. Variance clustering."
        elif H < 0.45:
            interpretation += "H < 0.5: long-term risk is LOWER than √T suggests. Mean reversion."
        else:
            interpretation += "H ≈ 0.5: Standard √T rule applies."
        
        return {
            'intervals': intervals[:len(realized_vol)],
            'realized_vol': realized_vol,
            'sqrt_t_predicted': sqrt_t_predicted[:len(realized_vol)],
            'actual_scaling_exponent': float(H),
            'deviates_from_sqrt_t': sqrt_t_diffs,
            'var_scaling_adjustment': float(var_adjustment),
            'interpretation': interpretation,
        }
    
    def stable_distribution_fit(self, returns: np.ndarray) -> dict:
        """
        Fit Lévy stable distribution to returns.
        
        Parameters:
        α (stability): 0 < α ≤ 2. α = 2 is Gaussian. α < 2 → fat tails.
        β (skewness): -1 ≤ β ≤ 1.
        γ (scale): > 0.
        δ (location): mean shift.
        """
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if len(returns_clean) < 10:
            return self._empty_stable_fit()
        
        # Simple parametric approach: estimate α from tail index
        # α ≈ number of finite moments
        
        # Method: log-log regression on tail CDF
        sorted_returns = np.sort(np.abs(returns_clean))[::-1]
        
        # Skip extreme outliers
        n = len(sorted_returns)
        tail_size = max(int(n * 0.05), 10)
        tail_returns = sorted_returns[:tail_size]
        
        # Fit power law to tail: P(X > x) ∝ x^(-α)
        if len(tail_returns) < 3:
            return self._empty_stable_fit()
        
        log_x = np.log(tail_returns)
        log_p = np.log(np.arange(1, len(tail_returns) + 1) / n)
        
        # Fit: log(P) = -α × log(x) + const
        alpha = -np.polyfit(log_x, log_p, 1)[0]
        alpha = max(0.5, min(alpha, 4.0))  # Clamp to reasonable range
        
        # Estimate other parameters
        gamma = np.std(returns_clean)
        delta = np.mean(returns_clean)
        
        # Skewness estimation
        skewness = float(pd.Series(returns_clean).skew())
        beta = (skewness / 2) if np.isfinite(skewness) else 0
        beta = np.clip(beta, -1, 1)
        
        is_gaussian = alpha > 1.95
        has_finite_variance = alpha >= 1.99
        
        tail_description = ""
        if alpha < 1.5:
            tail_description = "EXTREME FAT TAILS — tail risk is extreme."
        elif alpha < 2.0:
            tail_description = "Fat tails — tail risk is elevated."
        elif alpha >= 2.0:
            tail_description = "Gaussian or thin tails."
        
        interpretation = (
            f"Stable α = {alpha:.2f}. "
            f"{'Gaussian' if is_gaussian else 'Non-Gaussian'} distribution. "
            f"{'Finite variance.' if has_finite_variance else 'INFINITE VARIANCE — use quantile-based risk measures (VaR, CVaR) not variance-based ones.'} "
            f"{tail_description}"
        )
        
        return {
            'alpha': float(alpha),
            'beta': float(beta),
            'gamma': float(gamma),
            'delta': float(delta),
            'is_gaussian': is_gaussian,
            'has_finite_variance': has_finite_variance,
            'tail_description': tail_description,
            'interpretation': interpretation,
        }
    
    def hurst_exponent(self, returns: np.ndarray) -> dict:
        """
        Estimate Hurst exponent via rescaled range analysis.
        
        H = 0.5: random walk (GBM)
        H > 0.5: persistent (trending, volatility clustering)
        H < 0.5: mean reverting
        """
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if len(returns_clean) < 50:
            return {'hurst': 0.5, 'interpretation': 'Insufficient data'}
        
        # Simple Hurst via volatility scaling
        # Use volatility_scaling output
        vol_result = self.volatility_scaling(returns_clean)
        H = vol_result.get('actual_scaling_exponent', 0.5)
        
        if H > 0.55:
            interpretation = "H > 0.5: Markets show PERSISTENCE (trending, momentum). Long memory in volatility."
        elif H < 0.45:
            interpretation = "H < 0.5: Markets show MEAN REVERSION. Prices tend to revert to average."
        else:
            interpretation = "H ≈ 0.5: Markets behave like random walk (GBM assumption valid)."
        
        return {
            'hurst': float(H),
            'is_persistent': H > 0.55,
            'is_mean_reverting': H < 0.45,
            'interpretation': interpretation,
        }
    
    def universality_test(self, returns_dict: dict[str, np.ndarray]) -> dict:
        """Test if multiple assets share same scaling exponents (universality class)."""
        assets = list(returns_dict.keys())
        
        tail_exponents = {}
        hurst_exponents = {}
        stable_alphas = {}
        
        for asset, returns in returns_dict.items():
            # Tail exponent (from Gutenberg-Richter)
            from genesix.physics.seismology import GutenbergRichter
            gr = GutenbergRichter()
            gr_result = gr.fit_power_law(returns)
            tail_exponents[asset] = gr_result['alpha']
            
            # Hurst exponent
            hurst_result = self.hurst_exponent(returns)
            hurst_exponents[asset] = hurst_result['hurst']
            
            # Stable α
            stable_result = self.stable_distribution_fit(returns)
            stable_alphas[asset] = stable_result['alpha']
        
        # Check if they're in the same universality class (within 20%)
        tail_values = [v for v in tail_exponents.values() if not np.isnan(v)]
        hurst_values = [v for v in hurst_exponents.values() if not np.isnan(v)]
        stable_values = [v for v in stable_alphas.values() if not np.isnan(v)]
        
        same_tail_class = False
        same_hurst_class = False
        
        if tail_values:
            tail_cv = np.std(tail_values) / (np.mean(tail_values) + 1e-10)
            same_tail_class = tail_cv < 0.2
        
        if hurst_values:
            hurst_cv = np.std(hurst_values) / (np.mean(hurst_values) + 1e-10)
            same_hurst_class = hurst_cv < 0.2
        
        same_universality_class = same_tail_class and same_hurst_class
        
        interpretation = ""
        if same_universality_class:
            interpretation = f"Assets {assets} share the same universality class (same scaling laws). Same dynamics."
        else:
            interpretation = f"Assets {assets} belong to DIFFERENT universality classes. Different tail behavior and/or persistence."
        
        return {
            'assets': assets,
            'tail_exponents': tail_exponents,
            'hurst_exponents': hurst_exponents,
            'stable_alphas': stable_alphas,
            'same_universality_class': same_universality_class,
            'interpretation': interpretation,
        }
    
    def _empty_vol_scaling(self) -> dict:
        return {
            'intervals': [],
            'realized_vol': [],
            'sqrt_t_predicted': [],
            'actual_scaling_exponent': 0.5,
            'deviates_from_sqrt_t': False,
            'var_scaling_adjustment': 1.0,
            'interpretation': 'Insufficient data',
        }
    
    def _empty_stable_fit(self) -> dict:
        return {
            'alpha': 2.0,
            'beta': 0,
            'gamma': 1.0,
            'delta': 0,
            'is_gaussian': True,
            'has_finite_variance': True,
            'tail_description': '',
            'interpretation': 'Insufficient data',
        }
