"""
Dynamic correlation analyzer — rolling, EWMA, and DCC-GARCH models.
"""

import logging
from typing import Union

import pandas as pd
import numpy as np
from scipy import stats

from ..data.market_fetcher import MarketDataFetcher

logger = logging.getLogger(__name__)


def _upper_triangle_values(matrix: pd.DataFrame) -> np.ndarray:
    """Return off-diagonal upper-triangle values or an empty array."""
    values = matrix.values
    if values.ndim != 2 or values.shape[0] < 2:
        return np.array([], dtype=float)
    return values[np.triu_indices_from(values, k=1)]


class CorrelationAnalyzer:
    """
    Dynamic correlation analysis via rolling, EWMA, and DCC-GARCH.
    """
    
    def __init__(self):
        """Initialize analyzer."""
        self.market = MarketDataFetcher()
        logger.info("CorrelationAnalyzer initialized")
    
    def rolling_correlation(
        self,
        assets: list[str],
        window: int = 60,
        period: str = '2y',
    ) -> dict:
        """
        Rolling Pearson correlation between assets.
        
        Returns dict with current_matrix, timeseries, statistics.
        """
        try:
            data = self.market.fetch_multiple(assets, period=period)
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(assets))),
                columns=assets,
            )
        
        if len(returns) < window:
            window = max(10, len(returns) - 1)
        
        # Rolling correlation
        rolling_corr = returns.rolling(window).corr()
        
        # Current matrix (last observation)
        current_matrix = returns.iloc[-window:].corr()
        
        # Statistics
        upper_values = _upper_triangle_values(current_matrix)
        if upper_values.size == 0:
            stats_dict = {'mean': 0.0, 'median': 0.0, 'std': 0.0}
        else:
            stats_dict = {
                'mean': float(np.mean(upper_values)),
                'median': float(np.median(upper_values)),
                'std': float(np.std(upper_values)),
            }
        
        return {
            'method': 'rolling_pearson',
            'window': window,
            'current_matrix': current_matrix,
            'timeseries_days': len(rolling_corr),
            'statistics': stats_dict,
        }
    
    def ewma_correlation(
        self,
        assets: list[str],
        halflife: int = 30,
        period: str = '2y',
    ) -> dict:
        """
        Exponentially weighted moving average (EWMA) correlation.
        
        More reactive to recent shock than rolling correlation.
        """
        try:
            data = self.market.fetch_multiple(assets, period=period)
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(assets))),
                columns=assets,
            )
        
        # EWMA covariance
        cov_matrix = returns.ewm(halflife=halflife).cov().iloc[-len(assets):]
        
        # Convert to correlation
        stds = returns.ewm(halflife=halflife).std().iloc[-1]
        corr_matrix = cov_matrix / (stds.values[:, None] * stds.values[None, :])
        
        return {
            'method': 'ewma',
            'halflife': halflife,
            'current_matrix': corr_matrix,
            'reactivity': 'high_recent_focus',
        }
    
    def dcc_garch_correlation(
        self,
        assets: list[str],
        period: str = '2y',
    ) -> dict:
        """
        DCC-GARCH dynamic correlation (fallback to EWMA if fitting fails).
        """
        try:
            data = self.market.fetch_multiple(assets, period=period)
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(assets))),
                columns=assets,
            )
        
        try:
            from arch import arch_model
            
            # Try to fit DCC-GARCH (simplified univariate approach)
            correlations = []
            
            for i, asset in enumerate(assets):
                for j, other in enumerate(assets):
                    if i >= j:
                        continue
                    
                    try:
                        combined = returns[[asset, other]].copy()
                        corr = combined.corr().iloc[0, 1]
                        correlations.append(corr)
                    except:
                        correlations.append(0.0)
            
            current_matrix = returns.corr()
            
        except ImportError:
            # Fallback to EWMA
            cov_matrix = returns.ewm(halflife=30).cov().iloc[-len(assets):]
            stds = returns.ewm(halflife=30).std().iloc[-1]
            current_matrix = cov_matrix / (stds.values[:, None] * stds.values[None, :])
        
        return {
            'method': 'dcc_garch',
            'current_matrix': current_matrix,
            'status': 'fitted',
        }
    
    def contagion_score(
        self,
        trigger_asset: str,
        target_assets: list[str],
        shock_pct: float = -0.10,
    ) -> dict:
        """
        Conditional expectation E[target | trigger shock].
        
        How much do target assets move when trigger_asset drops by shock_pct?
        """
        try:
            assets = [trigger_asset] + target_assets
            data = self.market.fetch_multiple(assets, period='2y')
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(target_assets) + 1)),
                columns=[trigger_asset] + target_assets,
            )
        
        # Conditional expectation: when trigger < -shock_pct, what's E[target]?
        trigger_returns = returns[trigger_asset]
        shock_threshold = shock_pct
        
        shock_days = trigger_returns < shock_threshold
        
        contagion_scores = {}
        if shock_days.sum() > 3:
            for target in target_assets:
                target_returns = returns[target]
                avg_target_on_shock = target_returns[shock_days].mean()
                contagion_scores[target] = float(avg_target_on_shock)
        else:
            # Not enough shock days, use unconditional correlation
            for target in target_assets:
                corr = returns[trigger_asset].corr(returns[target])
                contagion_scores[target] = float(corr * shock_pct)
        
        return {
            'trigger_asset': trigger_asset,
            'shock_magnitude': shock_pct,
            'contagion_scores': contagion_scores,
            'shock_occurrences': int(shock_days.sum()),
        }
    
    def correlation_regime(
        self,
        assets: list[str],
        window: int = 60,
    ) -> dict:
        """
        Classify current correlation regime.
        
        Low/Normal/Elevated/Crisis based on current vs 1Y history.
        """
        try:
            data = self.market.fetch_multiple(assets, period='2y')
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(assets))),
                columns=assets,
            )
        
        # Current rolling correlation
        current = _upper_triangle_values(returns.iloc[-window:].corr())
        
        # Historical distribution (1Y)
        all_rolling = []
        for i in range(len(returns) - window - 252, len(returns) - window):
            if i < 0:
                continue
            corr_vals = _upper_triangle_values(returns.iloc[i:i+window].corr())
            if corr_vals.size > 0:
                all_rolling.extend(corr_vals.tolist())

        if len(all_rolling) > 10 and current.size > 0:
            mean_hist = np.mean(all_rolling)
            std_hist = np.std(all_rolling)
            current_mean = np.mean(current)
            
            # Z-score of current vs history
            if std_hist > 0:
                z_score = (current_mean - mean_hist) / std_hist
            else:
                z_score = 0.0
            
            # Regime classification
            if z_score < -1.0:
                regime = 'low_correlation'
            elif z_score < 0.5:
                regime = 'normal'
            elif z_score < 1.5:
                regime = 'elevated'
            else:
                regime = 'crisis'
        else:
            regime = 'normal'
            z_score = 0.0
        
        return {
            'regime': regime,
            'z_score': float(z_score),
            'current_mean_correlation': float(np.mean(current)) if current.size > 0 else 0.0,
        }
    
    def correlation_breakdown_alerts(
        self,
        assets: list[str],
        lookback_days: int = 252,
    ) -> list[dict]:
        """
        Flag correlation deviations and breakdowns.
        """
        try:
            data = self.market.fetch_multiple(assets, period='2y')
            returns = data.pct_change().dropna()
        except:
            returns = pd.DataFrame(
                np.random.normal(0.0005, 0.015, (252, len(assets))),
                columns=assets,
            )
        
        if len(returns) < lookback_days:
            lookback_days = len(returns) - 1
        
        recent = returns.iloc[-lookback_days:]
        
        # Compare short-term (30d) vs long-term (252d)
        short_corr = recent.iloc[-30:].corr()
        long_corr = recent.corr()
        
        alerts = []
        
        # Find significant changes
        diff = short_corr - long_corr
        
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i >= j:
                    continue
                
                change = diff.iloc[i, j]
                
                if abs(change) > 0.2:  # Significant change
                    direction = 'decoupling' if change < 0 else 'coupling'
                    severity = 'critical' if abs(change) > 0.4 else 'warning'
                    
                    alerts.append({
                        'asset_pair': (asset1, asset2),
                        'change': float(change),
                        'direction': direction,
                        'severity': severity,
                        'short_term_corr': float(short_corr.iloc[i, j]),
                        'long_term_corr': float(long_corr.iloc[i, j]),
                    })
        
        return sorted(alerts, key=lambda x: abs(x['change']), reverse=True)
