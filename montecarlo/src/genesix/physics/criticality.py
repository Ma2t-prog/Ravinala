"""
Self-Organized Criticality (SOC) and market phase transitions.

Markets naturally evolve toward a critical state where small perturbations
can trigger cascades of all sizes. GenesiX measures: how close is the
market to the critical point?

Phase states:
- LIQUID: normal market, moderate vol, price discovery works
- GAS: euphoria, high vol, herding, momentum dominates
- SOLID: frozen, no liquidity, everyone wants to sell
- CRITICAL: boundary between phases — maximum susceptibility
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CriticalityAnalyzer:
    """Market phase transitions and criticality analysis."""
    
    def market_temperature(self, returns: np.ndarray, volumes: np.ndarray,
                          lookback_days: int = 504) -> dict:
        """
        "Market temperature" — composite measure of market agitation.
        
        T = σ_realized × (V / V_avg) × (1 + |skewness|)
        
        Normalized to 0-100 scale based on 2-year history.
        """
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        volumes_clean = volumes[~np.isnan(volumes) & ~np.isinf(volumes)]
        
        if len(returns_clean) < 5 or len(volumes_clean) < 5:
            return self._empty_temperature()
        
        # Components
        vol_realized = np.std(returns_clean[-min(20, len(returns_clean)):])
        vol_avg = np.std(returns_clean[-lookback_days:]) if len(returns_clean) >= lookback_days else vol_realized
        
        vol_volume = np.mean(volumes_clean[-min(20, len(volumes_clean)):]) / (np.mean(volumes_clean[-lookback_days:]) + 1e-10)
        
        skewness = np.mean(returns_clean[-min(20, len(returns_clean)):] ** 3) / (np.std(returns_clean[-min(20, len(returns_clean)):]) ** 3 + 1e-10)
        
        # Raw temperature
        T = vol_realized * vol_volume * (1 + abs(skewness) / 10)
        
        # Normalize to historical percentile
        historical_temps = []
        for i in range(lookback_days, len(returns_clean), 20):
            window_vol = np.std(returns_clean[i-lookback_days:i])
            hist_temps = window_vol if window_vol > 0 else 0.01
            historical_temps.append(hist_temps)
        
        if historical_temps:
            percentile = np.mean([T >= ht for ht in historical_temps]) * 100
        else:
            percentile = 50
        
        # Map to label
        if percentile < 20:
            label = 'frozen'
            phase = 'solid'
        elif percentile < 40:
            label = 'cold'
            phase = 'liquid'
        elif percentile < 60:
            label = 'warm'
            phase = 'liquid'
        elif percentile < 80:
            label = 'hot'
            phase = 'gas'
        else:
            label = 'boiling'
            phase = 'gas'
        
        trend = 'heating' if vol_realized > vol_avg else ('cooling' if vol_realized < vol_avg * 0.9 else 'stable')
        
        return {
            'temperature': float(T),
            'normalized': float(np.clip(percentile, 0, 100)),
            'label': label,
            'components': {
                'volatility_contribution': float(vol_realized),
                'volume_contribution': float(vol_volume),
                'skew_contribution': float(abs(skewness) / 10),
            },
            'trend': trend,
            'phase': phase,
            'near_transition': abs(percentile - 40) < 10 or abs(percentile - 80) < 10,
            'interpretation': self._temperature_interpretation(label, percentile),
        }
    
    def susceptibility(self, returns: np.ndarray, window: int = 60) -> dict:
        """
        Market susceptibility — how sensitive is the market to perturbations?
        
        χ = Var(returns) / Var(|returns|)
        
        High susceptibility → system near critical point → small shocks cause big moves.
        """
        returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
        
        if len(returns_clean) < window:
            return self._empty_susceptibility()
        
        window_returns = returns_clean[-window:]
        var_returns = np.var(window_returns)
        var_abs_returns = np.var(np.abs(window_returns))
        
        if var_abs_returns < 1e-10:
            chi = 0
        else:
            chi = var_returns / var_abs_returns
        
        # Percentile over 1-year history
        if len(returns_clean) >= 252:
            historical_chi = []
            for i in range(window, len(returns_clean), 20):
                hist_var_ret = np.var(returns_clean[i-window:i])
                hist_var_abs = np.var(np.abs(returns_clean[i-window:i]))
                if hist_var_abs > 1e-10:
                    historical_chi.append(hist_var_ret / hist_var_abs)
            
            percentile = 0 if not historical_chi else np.mean([chi >= hc for hc in historical_chi]) * 100
        else:
            percentile = 50
        
        is_elevated = percentile > 80
        critical_proximity = min(1.0, max(0.0, (percentile - 50) / 50))
        
        return {
            'susceptibility': float(chi),
            'percentile_1y': float(percentile),
            'is_elevated': is_elevated,
            'critical_proximity': float(critical_proximity),
            'interpretation': self._susceptibility_interpretation(percentile),
        }
    
    def order_parameter(self, returns_matrix: pd.DataFrame, window: int = 60) -> dict:
        """
        Order parameter — measures market "herding" (correlation).
        
        M = mean of off-diagonal elements of rolling correlation matrix.
        
        M ≈ 0: disorder (healthy diversification)
        M → 1: perfect order (herding, DANGER)
        """
        if len(returns_matrix) < window:
            return self._empty_order_parameter()
        
        # Rolling correlation
        rolling_corr = returns_matrix.iloc[-window:].corr()
        
        # Off-diagonal elements
        off_diag = rolling_corr.values[np.triu_indices_from(rolling_corr.values, k=1)]
        M = np.mean(off_diag)
        
        # Regime
        if M < 0.3:
            regime = 'disordered'
        elif M < 0.5:
            regime = 'weakly_ordered'
        elif M < 0.7:
            regime = 'ordered'
        else:
            regime = 'critical'
        
        # Rate of change (if we have history)
        if len(returns_matrix) >= window + 60:
            prev_corr = returns_matrix.iloc[-(window+60):-60].corr()
            prev_off_diag = prev_corr.values[np.triu_indices_from(prev_corr.values, k=1)]
            prev_M = np.mean(prev_off_diag)
            rate_of_change = M - prev_M
        else:
            rate_of_change = 0
        
        rolling_series = pd.Series(index=returns_matrix.index[-window:], data=M)
        
        return {
            'order_parameter': float(M),
            'rolling_series': rolling_series,
            'regime': regime,
            'rate_of_change': float(rate_of_change),
            'interpretation': self._order_parameter_interpretation(regime, rate_of_change),
        }
    
    def phase_transition_detector(self, returns: np.ndarray, 
                                    volumes: np.ndarray,
                                    returns_matrix: Optional[pd.DataFrame] = None) -> dict:
        """
        Composite phase transition analysis.
        
        Returns probability of imminent phase transition.
        """
        temp = self.market_temperature(returns, volumes)
        susc = self.susceptibility(returns)
        order = self.order_parameter(returns_matrix) if returns_matrix is not None else self._empty_order_parameter()
        
        # Count early warning signals triggered
        warnings = []
        
        if susc['is_elevated']:
            warnings.append({'signal': 'susceptibility_divergence', 'value': susc['susceptibility'], 'threshold': 3.0, 'triggered': True})
        
        if order.get('regime') in ['ordered', 'critical']:
            warnings.append({'signal': 'order_parameter_surge', 'value': order.get('order_parameter', 0), 'threshold': 0.5, 'triggered': True})
        
        if temp['near_transition']:
            warnings.append({'signal': 'temperature_boundary', 'value': temp['normalized'], 'threshold': 50, 'triggered': True})
        
        if order.get('rate_of_change', 0) > 0.05:
            warnings.append({'signal': 'ordering_acceleration', 'value': order.get('rate_of_change', 0), 'threshold': 0.05, 'triggered': True})
        
        # Overall transition risk
        n_warnings = len(warnings)
        transition_risk = min(1.0, n_warnings / 3.0)
        
        # Likely transition type
        transition_type = None
        if temp['phase'] == 'gas' and susc['critical_proximity'] > 0.5:
            transition_type = 'gas_to_solid'  # Bubble burst
        elif temp['phase'] == 'liquid' and order.get('regime') == 'critical':
            transition_type = 'liquid_to_gas'   # Bubble forming
        elif temp['phase'] == 'solid' and susc['susceptibility'] > 2.0:
            transition_type = 'solid_to_liquid'  # Thaw/recovery
        
        recommendation = self._transition_recommendation(transition_type, transition_risk, n_warnings)
        
        return {
            'current_phase': temp['phase'],
            'temperature': temp,
            'susceptibility': susc,
            'order_parameter': order,
            'transition_risk': float(transition_risk),
            'transition_type': transition_type,
            'early_warning_signals': warnings,
            'recommendation': recommendation,
            'confidence': float(min(1.0, n_warnings / 2.0)),
        }
    
    def _temperature_interpretation(self, label: str, percentile: float) -> str:
        """Generate interpretation text."""
        templates = {
            'frozen': f"Market is {label} ({percentile:.0f}th percentile). LIQUIDITY TRAP risk.",
            'cold': f"Market is {label} ({percentile:.0f}th percentile). Calm conditions.",
            'warm': f"Market is {label} ({percentile:.0f}th percentile). Normal trading.",
            'hot': f"Market is {label} ({percentile:.0f}th percentile). Elevated activity.",
            'boiling': f"Market is {label} ({percentile:.0f}th percentile). EXTREME activity.",
        }
        return templates.get(label, f"Market temperature: {percentile:.0f}%")
    
    def _susceptibility_interpretation(self, percentile: float) -> str:
        """Generate susceptibility interpretation."""
        if percentile > 80:
            return "Susceptibility is ELEVATED. System is near critical point. Small shocks can trigger large moves."
        elif percentile > 60:
            return "Susceptibility is elevated. Increasing sensitivity to perturbations."
        else:
            return "Susceptibility is normal to low. System response to shocks is moderate."
    
    def _order_parameter_interpretation(self, regime: str, rate: float) -> str:
        """Generate order parameter interpretation."""
        base = f"Market is in {regime} regime. "
        if regime == 'critical':
            base += "EXTREME HERDING — all assets moving together. Crash conditions."
        elif regime == 'ordered':
            base += "Significant herding present. Diversification benefits reduced."
        elif regime == 'weakly_ordered':
            base += "Some herding detected. Maintain caution."
        else:
            base += "Healthy diversification. Assets moving independently."
        
        if rate > 0.05:
            base += " ORDERING ACCELERATING."
        
        return base
    
    def _transition_recommendation(self, trans_type: Optional[str], risk: float, n_warn: int) -> str:
        """Generate recommendation based on phase transition risk."""
        if trans_type == 'gas_to_solid':
            return f"HIGH CRASH RISK ({risk*100:.0f}% probability). Reduce exposure, hedge, or go defensive."
        elif trans_type == 'liquid_to_gas':
            return f"BUBBLE FORMATION RISK ({risk*100:.0f}% probability). Monitor for momentum exhaustion."
        elif trans_type == 'solid_to_liquid':
            return f"RECOVERY SIGNAL ({risk*100:.0f}% probability). Consider gradual re-entry."
        elif n_warn >= 3:
            return f"Multiple warning signals ({n_warn} triggered). System is STRESSED. Exercise caution."
        elif n_warn >= 2:
            return f"Transition risk elevated ({risk*100:.0f}%). Monitor developing conditions."
        else:
            return "No imminent phase transition detected. Continue normal operations."
    
    def _empty_temperature(self) -> dict:
        return {
            'temperature': 0, 'normalized': 50, 'label': 'warm', 'phase': 'liquid',
            'components': {'volatility_contribution': 0, 'volume_contribution': 0, 'skew_contribution': 0},
            'trend': 'stable', 'near_transition': False, 'interpretation': ''
        }
    
    def _empty_susceptibility(self) -> dict:
        return {'susceptibility': 0, 'percentile_1y': 50, 'is_elevated': False, 'critical_proximity': 0, 'interpretation': ''}
    
    def _empty_order_parameter(self) -> dict:
        return {'order_parameter': 0, 'rolling_series': pd.Series(), 'regime': 'disordered', 'rate_of_change': 0, 'interpretation': ''}
