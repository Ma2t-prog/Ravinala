"""
Multi-Criteria Asset Screener Engine.

Scans the asset universe and filters/ranks by multiple criteria:
- Valuation (PE, dividend yield)
- Momentum (1M, 3M, 6M, 12M returns)
- Risk (volatility, beta, max drawdown)
- Sentiment (news sentiment, trend)
- Technical (above/below moving averages)

Prebuilt screens:
- "Undervalued + Momentum": low valuation + positive momentum
- "Safe Haven": low beta + low vol
- "High Conviction": strong signals across multiple factors
- "Income": high dividend + low volatility
- "Momentum": highest momentum scores
- "Contrarian": beaten down with improving sentiment
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AssetScreener:
    """Multi-criteria asset screening engine."""
    
    def __init__(self):
        """Initialize screener with data sources."""
        try:
            from genesix.data.feature_store import FeatureStore
            self.feature_store = FeatureStore()
            self.has_data_source = True
        except Exception as e:
            logger.warning(f"FeatureStore unavailable: {e}. Running in demo mode.")
            self.has_data_source = False
    
    def screen(self, 
               universe: list[str] | None = None,
               filters: list[dict] | None = None,
               sort_by: str = 'composite_score',
               limit: int = 20) -> pd.DataFrame:
        """
        Run a screen on the asset universe.
        
        Args:
            universe: List of tickers. None = predefined universe
            filters: List of filter dicts with 'field', 'op', 'value'
            sort_by: Column to sort results by
            limit: Max results to return
        
        Returns:
            DataFrame with screening results
        """
        if universe is None:
            # Default universe: major ETFs and indices
            universe = [
                'SPY', 'QQQ', 'IWM', 'EFA', 'EEM',  # equities
                'TLT', 'BND', 'HYG',                # bonds
                'GLD', 'USO', 'DBC',                # commodities
                'FXE', 'FXY',                       # FX
                'GBTC', 'ETHE',                     # crypto
            ]
        
        # Build data for universe
        results = []
        for ticker in universe:
            try:
                data = self._get_asset_metrics(ticker)
                results.append(data)
            except Exception as e:
                logger.debug(f"Failed to screen {ticker}: {e}")
                continue
        
        df = pd.DataFrame(results)
        
        # Apply filters
        if filters:
            for filt in filters:
                field = filt.get('field')
                op = filt.get('op')
                value = filt.get('value')
                
                if op == '<':
                    df = df[df[field] < value]
                elif op == '>':
                    df = df[df[field] > value]
                elif op == '==':
                    df = df[df[field] == value]
                elif op == 'between':
                    df = df[(df[field] >= value[0]) & (df[field] <= value[1])]
        
        # Sort and limit
        df = df.sort_values(sort_by, ascending=False)
        df = df.head(limit)
        
        # Add signal column (machine learning recommendation)
        df['signal'] = df['composite_score'].apply(self._get_signal)
        
        return df
    
    def prebuilt_screen(self, screen_name: str) -> pd.DataFrame:
        """Run a prebuilt screen by name."""
        screens = {
            'undervalued_momentum': [
                {'field': 'pe_ratio', 'op': '<', 'value': 20},
                {'field': 'momentum_6m', 'op': '>', 'value': 0},
            ],
            'safe_haven': [
                {'field': 'beta', 'op': '<', 'value': 0.8},
                {'field': 'volatility_annual', 'op': '<', 'value': 0.20},
            ],
            'high_conviction': [
                {'field': 'momentum_6m', 'op': '>', 'value': 0.05},
                {'field': 'news_sentiment', 'op': '>', 'value': 0},
                {'field': 'rsi_14', 'op': 'between', 'value': [40, 70]},
            ],
            'income_generator': [
                {'field': 'dividend_yield', 'op': '>', 'value': 0.02},
                {'field': 'volatility_annual', 'op': '<', 'value': 0.18},
            ],
            'momentum': [
                {'field': 'momentum_6m', 'op': '>', 'value': 0.10},
            ],
            'contrarian': [
                {'field': 'momentum_1m', 'op': '<', 'value': -0.10},
                {'field': 'news_sentiment', 'op': '>', 'value': 0},
            ],
        }
        
        filters = screens.get(screen_name, [])
        return self.screen(filters=filters, limit=25)
    
    def rank_assets(self, universe: list[str], 
                    factors: list[str],
                    weights: dict[str, float] | None = None) -> pd.DataFrame:
        """
        Multi-factor ranking system.
        
        Each factor ranked 1-N, then composite score = weighted average rank percentile.
        """
        if weights is None:
            weights = {f: 1.0/len(factors) for f in factors}
        
        df = self.screen(universe=universe, limit=len(universe))
        
        # Rank each factor
        for factor in factors:
            percentile_rank = df[factor].rank(pct=True)
            df[f'{factor}_percentile'] = percentile_rank
        
        # Composite score = weighted average of percentiles
        percentile_cols = [f'{f}_percentile' for f in factors]
        df['composite_score'] = sum(
            df[f'{f}_percentile'] * weights[f] for f in factors
        ) / sum(weights.values())
        
        return df.sort_values('composite_score', ascending=False)
    
    def compare_assets(self, tickers: list[str]) -> pd.DataFrame:
        """Side-by-side comparison of 2-5 assets."""
        data = []
        for ticker in tickers:
            metrics = self._get_asset_metrics(ticker)
            data.append(metrics)
        
        df = pd.DataFrame(data).T
        return df
    
    def _get_asset_metrics(self, ticker: str) -> dict:
        """Fetch or compute metrics for an asset."""
        try:
            import yfinance as yf
            
            # Fetch historical data
            hist = yf.download(ticker, period='1y', progress=False)
            
            if hist.empty:
                raise ValueError(f"No data for {ticker}")
            
            # Calculate metrics
            returns = hist['Close'].pct_change()
            momentum_1m = (hist['Close'].iloc[-21] / hist['Close'].iloc[-22] - 1) * 100 if len(hist) > 21 else 0
            momentum_6m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-126] - 1) * 100 if len(hist) > 126 else 0
            
            volatility = returns.std() * np.sqrt(252)  # annualized
            sharpe = returns.mean() * 252 / volatility if volatility > 0 else 0
            
            # RSI calculation
            delta = returns.dropna()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_14 = 100 - (100 / (1 + rs))
            
            price = hist['Close'].iloc[-1]
            change_1d = (price / hist['Close'].iloc[-2] - 1) * 100 if len(hist) > 1 else 0
            change_1m = momentum_1m
            change_6m = momentum_6m
            
            return {
                'ticker': ticker,
                'price': price,
                'change_1d': change_1d,
                'change_1m': change_1m,
                'change_6m': change_6m,
                'change_12m': (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100,
                'volatility_annual': volatility * 100,
                'beta': 1.0,  # would need benchmark correlation
                'sharpe': sharpe,
                'pe_ratio': 15.0,  # placeholder
                'dividend_yield': 0.02,  # placeholder
                'rsi_14': rsi_14.iloc[-1] if not rsi_14.empty else 50,
                'news_sentiment': 0.0,  # would need sentiment API
                'momentum_1m': momentum_1m,
                'momentum_6m': momentum_6m,
                'composite_score': sharpe * 10 + momentum_6m * 0.5,  # simple composite
            }
        except Exception as e:
            logger.debug(f"Error calculating metrics for {ticker}: {e}")
            raise
    
    def _get_signal(self, score: float) -> str:
        """Convert composite score to signal."""
        if score >= 0.7:
            return 'strong_buy'
        elif score >= 0.4:
            return 'buy'
        elif score >= 0.25:
            return 'neutral'
        elif score >= 0.1:
            return 'sell'
        else:
            return 'strong_sell'
