"""
Correlation Matrix Engine

Calculates correlations between assets using Pearson and Spearman methods.
Useful for understanding asset relationships in a portfolio.

Usage:
    from analytics.correlation import CorrelationEngine
    
    corr = CorrelationEngine(lookback_period=252)  # 1 year
    corr.add_price("AAPL", 150.25)
    corr.add_price("MSFT", 345.60)
    
    matrix = corr.calculate_matrix()
    print(matrix)  # DataFrame with correlations
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CorrelationEngine:
    """
    Calculates correlations between multiple assets.
    
    Methods:
    - Pearson: Linear correlation
    - Spearman: Rank-based (non-linear) correlation
    """
    
    def __init__(self, lookback_periods: int = 252):
        """
        Initialize correlation engine.
        
        Args:
            lookback_periods: Number of periods to use for calculation (default: 252 = 1 year)
        """
        self.lookback = lookback_periods
        self.price_history: Dict[str, List[float]] = {}
        logger.info(f"Correlation engine initialized (lookback: {lookback_periods} periods)")
    
    def add_price(self, symbol: str, price: float) -> None:
        """
        Add a price point for a symbol.
        
        Args:
            symbol: Asset symbol (e.g., "AAPL")
            price: Current price
        """
        symbol = symbol.upper()
        
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        
        # Keep only lookback periods
        if len(self.price_history[symbol]) > self.lookback:
            self.price_history[symbol].pop(0)
    
    def calculate_matrix(self, method: str = "pearson") -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix.
        
        Args:
            method: "pearson" (default) or "spearman"
        
        Returns:
            pandas DataFrame with correlation coefficients
        """
        if len(self.price_history) < 2:
            logger.warning(f"Need at least 2 assets, have {len(self.price_history)}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(self.price_history)
        
        # Calculate percentage returns
        returns = df.pct_change().dropna()
        
        if len(returns) < 2:
            logger.warning("Not enough data points for correlation")
            return None
        
        # Calculate correlation matrix
        if method.lower() == "pearson":
            corr_matrix = returns.corr(method="pearson")
        elif method.lower() == "spearman":
            corr_matrix = returns.corr(method="spearman")
        else:
            raise ValueError(f"Unknown method: {method}")
        
        logger.debug(f"Calculated {method} correlation matrix ({len(corr_matrix)}x{len(corr_matrix)})")
        
        return corr_matrix
    
    def get_corr_pair(self, symbol1: str, symbol2: str) -> Optional[float]:
        """
        Get correlation between two symbols.
        
        Args:
            symbol1: First asset (e.g., "AAPL")
            symbol2: Second asset (e.g., "MSFT")
        
        Returns:
            Correlation coefficient (-1 to 1), or None if calculation fails
        """
        corr_matrix = self.calculate_matrix()
        
        if corr_matrix is None:
            return None
        
        symbol1 = symbol1.upper()
        symbol2 = symbol2.upper()
        
        try:
            return corr_matrix.loc[symbol1, symbol2]
        except KeyError:
            logger.warning(f"Symbols not found: {symbol1}, {symbol2}")
            return None
    
    def get_highly_correlated(self, symbol: str, threshold: float = 0.7) -> List[tuple]:
        """
        Find assets highly correlated with a given symbol.
        
        Args:
            symbol: Reference asset
            threshold: Minimum correlation (0-1, default 0.7 = 70%)
        
        Returns:
            List of (symbol, correlation) tuples, sorted by correlation
        """
        corr_matrix = self.calculate_matrix()
        
        if corr_matrix is None:
            return []
        
        symbol = symbol.upper()
        
        try:
            correlations = corr_matrix[symbol]
            # Filter by threshold, exclude self-correlation
            high_corr = [
                (sym, corr) for sym, corr in correlations.items()
                if abs(corr) >= threshold and sym != symbol
            ]
            # Sort by absolute correlation
            high_corr.sort(key=lambda x: abs(x[1]), reverse=True)
            
            logger.debug(f"Found {len(high_corr)} assets corr with {symbol} > {threshold}")
            
            return high_corr
        except KeyError:
            logger.warning(f"Symbol not found: {symbol}")
            return []
    
    def get_uncorrelated(self, symbol: str, threshold: float = 0.3) -> List[tuple]:
        """
        Find assets with low correlation (good for diversification).
        
        Args:
            symbol: Reference asset
            threshold: Maximum correlation (default 0.3 = 30%)
        
        Returns:
            List of (symbol, correlation) tuples
        """
        corr_matrix = self.calculate_matrix()
        
        if corr_matrix is None:
            return []
        
        symbol = symbol.upper()
        
        try:
            correlations = corr_matrix[symbol]
            # Make all absolute values lower than threshold
            uncorr = [
                (sym, corr) for sym, corr in correlations.items()
                if abs(corr) <= threshold and sym != symbol
            ]
            # Sort by lowest correlation
            uncorr.sort(key=lambda x: abs(x[1]))
            
            return uncorr
        except KeyError:
            return []
    
    def reset(self) -> None:
        """Clear all price history"""
        self.price_history.clear()
        logger.info("Correlation engine reset")

# ================================
# EXAMPLE USAGE
# ================================

if __name__ == "__main__":
    # Test the engine
    logging.basicConfig(level=logging.DEBUG)
    
    engine = CorrelationEngine(lookback_periods=100)
    
    # Simulate price data
    import random
    random.seed(42)
    
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    base_prices = {"AAPL": 150, "MSFT": 345, "GOOGL": 120, "AMZN": 155}
    
    for _ in range(100):
        for sym in symbols:
            price = base_prices[sym] * (1 + random.gauss(0, 0.02))
            engine.add_price(sym, price)
            base_prices[sym] = price
    
    # Calculate and print correlation matrix
    print("\n=== Pearson Correlation Matrix ===")
    print(engine.calculate_matrix("pearson"))
    
    print("\n=== Spearman Correlation Matrix ===")
    print(engine.calculate_matrix("spearman"))
    
    print("\n=== Highly Correlated with AAPL (>0.5) ===")
    print(engine.get_highly_correlated("AAPL", threshold=0.5))
    
    print("\n=== Uncorrelated with AAPL (<0.3) ===")
    print(engine.get_uncorrelated("AAPL", threshold=0.3))
