"""
Risk Analytics Engine

Calculates risk metrics for individual assets and portfolios:
- Value at Risk (VaR) - historical and parametric methods
- Conditional VaR (CVaR / Expected Shortfall)
- Volatility (daily and annualized)
- Portfolio risk aggregation

Usage:
    from analytics.risk import RiskEngine
    
    risk = RiskEngine(confidence_level=0.95)
    risk.add_price("AAPL", 150.25)
    
    var = risk.calculate_var_historical("AAPL", position_value=1_000_000)
    cvar = risk.calculate_cvar("AAPL", position_value=1_000_000)
    vol = risk.calculate_volatility("AAPL")
    
    print(f"VaR (95%): ${abs(var):,.2f}")
    print(f"CVaR (95%): ${abs(cvar):,.2f}")
    print(f"Volatility: {vol:.2f}%")
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
import logging
import sys
from typing import Dict, List, Optional, Tuple
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_quant_conventions():
    """Load shared quant conventions without importing heavy genesix package init."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "genesix"
        / "utils"
        / "quant_conventions.py"
    )
    spec = spec_from_file_location("src_shared_quant_conventions", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load quant conventions from {module_path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_QC = _load_quant_conventions()
RISK_FREE_RATE = _QC.RISK_FREE_RATE
TRADING_DAYS = _QC.TRADING_DAYS
ANNUALIZATION_FACTOR_RETURN = _QC.ANNUALIZATION_FACTOR_RETURN
ANNUALIZATION_FACTOR_VOL = _QC.ANNUALIZATION_FACTOR_VOL

class RiskEngine:
    """
    Calculates value at risk, CVaR, volatility, and portfolio risk metrics.
    """
    
    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize risk engine.
        
        Args:
            confidence_level: Confidence level for VaR (0.95 = 95% confidence)
        """
        self.confidence = confidence_level
        self.price_history: Dict[str, List[float]] = {}
        logger.info(f"Risk engine initialized (confidence: {confidence_level*100}%)")
    
    def add_price(self, symbol: str, price: float) -> None:
        """Add price point for a symbol."""
        symbol = symbol.upper()
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
    
    def calculate_var_historical(self, symbol: str, position_value: float) -> float:
        """
        Calculate Value at Risk using historical simulation (non-parametric).
        
        Interpretation: There is a (1-confidence) probability that the position
        will lose more than the returned amount over one period.
        
        Example: VaR = -2.5% means 95% chance that daily loss won't exceed 2.5%
        
        Args:
            symbol: Asset symbol
            position_value: Total position value in dollars
        
        Returns:
            Dollar loss amount (negative value indicates loss)
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            logger.warning(f"Not enough data for {symbol}")
            return 0.0
        
        # Calculate percentage returns
        returns = np.diff(prices) / prices[:-1]
        
        # Historical percentile (worst case at (1-confidence) percentile)
        var_percentile = (1 - self.confidence) * 100
        var = np.percentile(returns, var_percentile)
        
        # Convert to dollar amount
        dollar_var = position_value * var
        
        logger.debug(f"{symbol} VaR (hist): {var*100:.2f}% = ${dollar_var:,.0f}")
        
        return dollar_var
    
    def calculate_var_parametric(self, symbol: str, position_value: float) -> float:
        """
        Calculate Value at Risk assuming normal distribution (parametric).
        
        Pros: Fast, works with less data
        Cons: Assumes normal distribution (often wrong for financial data)
        
        Args:
            symbol: Asset symbol
            position_value: Total position value in dollars
        
        Returns:
            Dollar loss amount (negative value)
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            return 0.0
        
        # Returns
        returns = np.diff(prices) / prices[:-1]
        
        # Fit to normal distribution
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Z-score at confidence level
        z_score = norm.ppf(1 - self.confidence)
        
        # VaR calculation
        var = mean_return + z_score * std_return
        dollar_var = position_value * var
        
        logger.debug(f"{symbol} VaR (param): {var*100:.2f}% = ${dollar_var:,.0f}")
        
        return dollar_var
    
    def calculate_cvar(self, symbol: str, position_value: float) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        
        CVaR is the average loss given that loss exceeds VaR.
        More conservative than VaR (used by some regulators).
        
        Args:
            symbol: Asset symbol
            position_value: Position value
        
        Returns:
            Dollar loss (more severe than VaR)
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            return 0.0
        
        returns = np.diff(prices) / prices[:-1]
        
        # VaR threshold
        var = np.percentile(returns, (1 - self.confidence) * 100)
        
        # Average of returns beyond VaR threshold
        tail_losses = returns[returns <= var]
        
        if len(tail_losses) > 0:
            cvar = np.mean(tail_losses)
        else:
            cvar = var  # Fallback if no tail data
        
        dollar_cvar = position_value * cvar
        
        logger.debug(f"{symbol} CVaR: {cvar*100:.2f}% = ${dollar_cvar:,.0f}")
        
        return dollar_cvar
    
    def calculate_volatility(self, symbol: str, annualize: bool = True) -> float:
        """
        Calculate volatility (standard deviation of returns).
        
        Args:
            symbol: Asset symbol
            annualize: If True, annualize with shared quant convention
        
        Returns:
            Volatility as percentage (e.g., 0.25 = 25%)
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            return 0.0
        
        returns = np.diff(prices) / prices[:-1]
        
        daily_vol = np.std(returns)
        
        if annualize:
            annual_vol = daily_vol * ANNUALIZATION_FACTOR_VOL
        else:
            annual_vol = daily_vol
        
        logger.debug(f"{symbol} volatility: {annual_vol*100:.2f}% (annualized)")
        
        return annual_vol
    
    def calculate_sharpe_ratio(self, symbol: str, risk_free_rate: float = RISK_FREE_RATE) -> float:
        """
        Calculate Sharpe Ratio (return per unit of risk).
        
        Sharpe = (annual_return - risk_free_rate) / volatility
        Higher is better (>1 is good, >2 is very good)
        
        Args:
            symbol: Asset symbol
            risk_free_rate: Annual risk-free rate (shared convention by default)
        
        Returns:
            Sharpe ratio
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            return 0.0
        
        returns = np.diff(prices) / prices[:-1]
        
        # Annualized metrics
        annual_return = np.mean(returns) * ANNUALIZATION_FACTOR_RETURN
        volatility = self.calculate_volatility(symbol, annualize=True)
        
        if volatility == 0:
            return 0.0
        
        sharpe = (annual_return - risk_free_rate) / volatility
        
        logger.debug(f"{symbol} Sharpe: {sharpe:.2f}")
        
        return sharpe
    
    def calculate_max_drawdown(self, symbol: str) -> Tuple[float, int, int]:
        """
        Calculate maximum drawdown (largest peak-to-trough decline).
        
        Returns:
            (max_drawdown_pct, from_index, to_index)
        """
        symbol = symbol.upper()
        prices = np.array(self.price_history.get(symbol, []))
        
        if len(prices) < 2:
            return 0.0, 0, 0
        
        # Running maximum
        running_max = np.maximum.accumulate(prices)
        
        # Drawdown
        drawdown = (prices - running_max) / running_max
        
        # Find max
        max_dd = np.min(drawdown)
        max_dd_idx = np.argmin(drawdown)
        max_idx = np.argmax(prices[:max_dd_idx])
        
        logger.debug(f"{symbol} max drawdown: {max_dd*100:.2f}%")
        
        return max_dd, max_idx, max_dd_idx
    
    def calculate_portfolio_var(
        self,
        positions: Dict[str, float],
        correlation_matrix: pd.DataFrame,
        method: str = "historical"
    ) -> float:
        """
        Calculate Value at Risk for a multi-asset portfolio.
        
        Args:
            positions: {"AAPL": 100000, "MSFT": 50000, ...}
            correlation_matrix: pd.DataFrame of correlations
            method: "historical" or "parametric"
        
        Returns:
            Portfolio VaR (dollar amount)
        """
        symbols = list(positions.keys())
        values = np.array(list(positions.values()))
        total_value = sum(values)
        
        if total_value == 0:
            return 0.0
        
        # Calculate individual volatilities
        vols = np.array([self.calculate_volatility(sym) for sym in symbols])
        
        # Get correlation submatrix
        try:
            corr_subset = correlation_matrix.loc[symbols, symbols].values
        except (KeyError, AttributeError):
            # If no correlation matrix, assume independent
            corr_subset = np.eye(len(symbols))
        
        # Covariance matrix
        cov_matrix = np.outer(vols, vols) * corr_subset
        
        # Portfolio weights
        weights = values / total_value
        
        # Portfolio volatility
        port_vol = np.sqrt(weights @ cov_matrix @ weights.T)
        
        # VaR
        z_score = norm.ppf(1 - self.confidence)
        port_var = z_score * port_vol * total_value
        
        logger.debug(f"Portfolio VaR: {port_var/total_value*100:.2f}% = ${port_var:,.0f}")
        
        return port_var
    
    def reset(self) -> None:
        """Clear all price history"""
        self.price_history.clear()
        logger.info("Risk engine reset")

# ================================
# EXAMPLE USAGE
# ================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    risk = RiskEngine(confidence_level=0.95)
    
    # Simulate prices
    import random
    random.seed(42)
    
    base_price = 150.0
    for i in range(TRADING_DAYS):
        price = base_price * (1 + random.gauss(0.0005, 0.02))
        risk.add_price("AAPL", price)
        base_price = price
    
    # Calculate risk metrics
    position = 1_000_000  # $1M position
    
    var_hist = risk.calculate_var_historical("AAPL", position)
    var_param = risk.calculate_var_parametric("AAPL", position)
    cvar = risk.calculate_cvar("AAPL", position)
    vol = risk.calculate_volatility("AAPL")
    sharpe = risk.calculate_sharpe_ratio("AAPL")
    max_dd, _, _ = risk.calculate_max_drawdown("AAPL")
    
    print(f"\n=== AAPL Risk Metrics ===")
    print(f"VaR (Historical):  ${abs(var_hist):>12,.0f}  ({var_hist/position*100:>6.2f}%)")
    print(f"VaR (Parametric):  ${abs(var_param):>12,.0f}  ({var_param/position*100:>6.2f}%)")
    print(f"CVaR (Expected S): ${abs(cvar):>12,.0f}  ({cvar/position*100:>6.2f}%)")
    print(f"Volatility:        {vol*100:>12.2f}%")
    print(f"Sharpe Ratio:      {sharpe:>12.2f}")
    print(f"Max Drawdown:      {max_dd*100:>12.2f}%")
