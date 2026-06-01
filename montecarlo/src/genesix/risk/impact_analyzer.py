"""
Impact analyzer — causal impact analysis for macro events.

Models how market events propagate through asset classes.
"""

import logging
from typing import Union

import pandas as pd
import numpy as np
from scipy import stats

from ..utils.config import Config
from ..data.market_fetcher import MarketDataFetcher

logger = logging.getLogger(__name__)

# Event impact chains (from spec)
EVENT_IMPACT_CHAINS = {
    'fed_rate_hike_25bps': {
        'description': 'Federal Reserve raises rates by 25 basis points',
        'direct': {'SPY': -0.008, 'QQQ': -0.012, 'TLT': -0.015, 'BTC-USD': -0.02},
        'indirect': {'XLU': -0.01, 'XLF': +0.005, 'XLRE': -0.012},
        'confidence': 0.72,
    },
    'oil_price_spike_10pct': {
        'description': 'Oil prices surge 10%',
        'direct': {'XLE': +0.06, 'CL=F': +0.10, 'XLY': -0.02, 'SPY': -0.01},
        'indirect': {'JETS': -0.04, 'XLP': -0.005},
        'confidence': 0.68,
    },
    'unemployment_rise_50bps': {
        'description': 'Unemployment rate rises by 0.5 percentage points',
        'direct': {'SPY': -0.025, 'XLY': -0.04, 'TLT': +0.02},
        'indirect': {'XLF': -0.03, 'HYG': -0.02},
        'confidence': 0.65,
    },
    'cpi_surprise_up_50bps': {
        'description': 'CPI comes in 0.5% above expectations',
        'direct': {'SPY': -0.015, 'QQQ': -0.02, 'TLT': -0.025},
        'indirect': {'XLRE': -0.02, 'XLU': -0.015},
        'confidence': 0.70,
    },
    'recession_start': {
        'description': 'Official recession declared',
        'direct': {'SPY': -0.15, 'QQQ': -0.18, 'HYG': -0.08, 'TLT': +0.10},
        'indirect': {'XLF': -0.20, 'XLY': -0.18},
        'confidence': 0.60,
    },
}


class ImpactAnalyzer:
    """
    Causal impact analysis — models how events propagate through markets.
    """
    
    def __init__(self):
        """Initialize impact analyzer."""
        self.market = MarketDataFetcher()
        logger.info("ImpactAnalyzer initialized")
    
    def macro_sensitivity_matrix(
        self,
        assets: list[str],
        lookback_days: int = 504,
    ) -> pd.DataFrame:
        """
        For each asset, regress daily returns on macro factor changes.
        
        Returns DataFrame with asset betas to macro factors.
        """
        # Placeholder implementation
        # In production, would use actual regression on macro data
        
        factors = ['10Y_yield', 'DXY', 'VIX', 'Oil', 'Gold', 'CPI', 'Unemp']
        
        # Synthetic data for now
        matrix_data = {}
        for asset in assets:
            betas = {f: np.random.uniform(-0.5, 0.5) for f in factors}
            matrix_data[asset] = betas
        
        return pd.DataFrame(matrix_data).T
    
    def event_impact_chain(
        self,
        event_type: str,
        magnitude: float = 1.0,
    ) -> dict:
        """
        Model the cascade of impacts from a macro event.
        
        Args:
            event_type: one of EVENT_IMPACT_CHAINS keys
            magnitude: multiplier (1.0 = standard, 2.0 = double)
        
        Returns: impact chain dict with direct/indirect effects
        """
        if event_type not in EVENT_IMPACT_CHAINS:
            available = list(EVENT_IMPACT_CHAINS.keys())
            raise ValueError(f"Unknown event: {event_type}. Available: {available}")
        
        chain = EVENT_IMPACT_CHAINS[event_type]
        
        return {
            'event': event_type,
            'description': chain['description'],
            'magnitude': magnitude,
            'direct_impact': {k: v * magnitude for k, v in chain['direct'].items()},
            'indirect_impact': {k: v * magnitude for k, v in chain['indirect'].items()},
            'confidence': chain['confidence'],
            'total_affected_assets': len(chain['direct']) + len(chain['indirect']),
        }
    
    def company_exposure(self, ticker: str) -> dict:
        """
        Company-level exposure profile via yfinance.
        
        Returns dict with company info and risk factors.
        """
        try:
            import yfinance as yf
            company = yf.Ticker(ticker)
            info = company.info or {}
        except:
            info = {}
        
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        beta = info.get('beta', np.nan)
        market_cap = info.get('marketCap', np.nan)
        
        risk_factors = []
        if beta and beta > 1.5:
            risk_factors.append('high_beta')
        if market_cap and market_cap < 2e9:
            risk_factors.append('small_cap')
        
        return {
            'ticker': ticker,
            'sector': sector,
            'industry': industry,
            'beta': float(beta) if not np.isnan(beta) else np.nan,
            'market_cap': float(market_cap) if not np.isnan(market_cap) else np.nan,
            'risk_factors': risk_factors,
        }
    
    def portfolio_exposure_report(
        self,
        portfolio_weights: dict[str, float],
    ) -> dict:
        """
        Aggregate exposure report for a portfolio.
        """
        sector_allocation = {}
        
        for asset, weight in portfolio_weights.items():
            try:
                exposure = self.company_exposure(asset)
                sector = exposure.get('sector', 'Other')
                sector_allocation[sector] = sector_allocation.get(sector, 0) + weight
            except:
                pass
        
        # HHI (Herfindahl-Hirschman Index)
        hhi = sum(w**2 for w in portfolio_weights.values())
        
        # Diversification score (0-100)
        diversification_score = max(0, 100 - (hhi * 100 * 10))
        
        return {
            'sector_allocation': sector_allocation,
            'asset_class_allocation': {'equity': sum(portfolio_weights.values())},
            'concentration_hhi': float(hhi),
            'diversification_score': min(100, float(diversification_score)),
            'top_risk_factors': [],
        }
