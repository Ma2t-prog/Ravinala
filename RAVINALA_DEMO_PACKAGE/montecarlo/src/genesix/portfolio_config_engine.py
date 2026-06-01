"""
GenesiX Portfolio Configuration Engine — v2.1
Dynamic universe selection, constraint builder, and multi-model optimization
Handles user-selected instruments + risk profile → optimal allocation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.optimize import minimize
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OptimizationModel:
    """Model configuration for portfolio optimization."""
    name: str
    description: str
    method: str  # "mvo", "inverse_vol", "equal_weight", "risk_parity"
    params: Dict


@dataclass
class PortfolioConstraints:
    """Portfolio-level constraints."""
    min_sector_allocation: float = 0.02  # 2% min per sector
    max_sector_allocation: float = 0.40  # 40% max per sector
    min_weight_per_instrument: float = 0.01  # 1% min per instrument
    max_weight_per_instrument: float = 0.15  # 15% max per instrument
    max_leverage: float = 1.0  # No leverage by default
    turnover_limit: Optional[float] = None  # None = no limit


@dataclass
class AllocationResult:
    """Output of portfolio optimization."""
    weights: Dict[str, float]  # ticker -> weight (0-1)
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    model_used: str
    execution_time_ms: float
    warnings: List[str]


# ============================================================================
# PORTFOLIO OPTIMIZER ENGINE
# ============================================================================

class PortfolioOptimizer:
    """Multi-model portfolio optimization engine."""
    
    def __init__(self, instruments: List, lookback_period: str = "2y"):
        """
        Initialize optimizer with instrument universe.
        
        Args:
            instruments: List of Instrument objects from universe_explorer
            lookback_period: Historical data period for covariance matrix
        """
        self.instruments = instruments
        self.tickers = [inst.ticker for inst in instruments]
        self.lookback_period = lookback_period
        self._price_data = None
        self._returns = None
        self._cov_matrix = None
        self._mean_returns = None
        self.warnings = []
        
    def _fetch_price_data(self) -> bool:
        """Fetch historical price data for all instruments."""
        try:
            self._price_data = yf.download(
                self.tickers,
                period=self.lookback_period,
                progress=False
            )['Close']
            
            # Handle single ticker case (returns Series instead of DataFrame)
            if isinstance(self._price_data, pd.Series):
                self._price_data = pd.DataFrame({self.tickers[0]: self._price_data})
            
            # Validate data quality
            min_data_points = len(self._price_data) * 0.7  # 70% data requirement
            valid_tickers = []
            for ticker in self.tickers:
                non_null = self._price_data[ticker].notna().sum()
                if non_null > min_data_points:
                    valid_tickers.append(ticker)
                else:
                    self.warnings.append(f"Insufficient data for {ticker} (only {non_null} points)")
            
            # Filter to valid tickers only
            self._price_data = self._price_data[valid_tickers]
            self.tickers = valid_tickers
            
            if len(self.tickers) < 2:
                logger.error("Insufficient valid instruments for optimization")
                return False
            
            logger.info(f"Fetched price data for {len(self.tickers)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch price data: {e}")
            self.warnings.append(f"Price data fetch failed: {str(e)}")
            return False
    
    def _calculate_statistics(self) -> bool:
        """Calculate returns covariance matrix and expected returns."""
        try:
            self._returns = self._price_data.pct_change().dropna()
            self._mean_returns = self._returns.mean() * 252  # Annualized
            self._cov_matrix = self._returns.cov() * 252  # Annualized
            
            logger.info("Calculated return statistics")
            return True
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return False
    
    def optimize_mvo(
        self,
        target_return: float,
        max_volatility: Optional[float] = None,
        constraints_cfg: Optional[PortfolioConstraints] = None
    ) -> Optional[AllocationResult]:
        """
        Mean-Variance Optimization (Markowitz).
        
        Minimizes portfolio volatility subject to target return constraint.
        """
        import time
        start_time = time.time()
        
        if self._cov_matrix is None:
            if not self._fetch_price_data() or not self._calculate_statistics():
                return None
        
        n = len(self.tickers)
        constraints_cfg = constraints_cfg or PortfolioConstraints()
        
        def portfolio_volatility(w):
            """Objective: minimize portfolio volatility."""
            return float(np.sqrt(w @ self._cov_matrix.values @ w))
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},  # Sum to 1
            {'type': 'ineq', 'fun': lambda w: w @ self._mean_returns.values - (target_return / 100)},  # Target return
        ]
        
        # Add max volatility constraint if specified
        if max_volatility:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: (max_volatility / 100) - np.sqrt(w @ self._cov_matrix.values @ w)
            })
        
        # Bounds: min/max weight per instrument
        bounds = [
            (constraints_cfg.min_weight_per_instrument, constraints_cfg.max_weight_per_instrument)
            for _ in range(n)
        ]
        
        # Initial guess
        w0 = np.ones(n) / n
        
        # Optimize
        result = minimize(
            portfolio_volatility,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'maxiter': 1000}
        )
        
        execution_ms = (time.time() - start_time) * 1000
        
        if result.success and result.x is not None:
            weights = result.x
            weights = weights / weights.sum()  # Normalize
            
            expected_return = float(weights @ self._mean_returns.values) * 100
            expected_vol = float(np.sqrt(weights @ self._cov_matrix.values @ weights)) * 100
            sharpe = expected_return / max(expected_vol, 0.001)
            
            return AllocationResult(
                weights={t: float(w) for t, w in zip(self.tickers, weights)},
                expected_return=expected_return,
                expected_volatility=expected_vol,
                sharpe_ratio=sharpe,
                model_used="Mean-Variance Optimization (Markowitz)",
                execution_time_ms=execution_ms,
                warnings=self.warnings
            )
        else:
            self.warnings.append(f"MVO optimization failed: {result.message}")
            return None
    
    def optimize_inverse_volatility(
        self,
        constraints_cfg: Optional[PortfolioConstraints] = None
    ) -> Optional[AllocationResult]:
        """
        Inverse Volatility weighting (Risk Parity style).
        Higher weight to lower-volatility instruments.
        """
        import time
        start_time = time.time()
        
        if self._cov_matrix is None:
            if not self._fetch_price_data() or not self._calculate_statistics():
                return None
        
        # Volatility of each instrument
        volatilities = np.sqrt(np.diag(self._cov_matrix.values))
        
        # Inverse volatility weights (higher volatility = lower weight)
        inv_vol_weights = 1.0 / volatilities
        weights = inv_vol_weights / inv_vol_weights.sum()
        
        expected_return = float(weights @ self._mean_returns.values) * 100
        expected_vol = float(np.sqrt(weights @ self._cov_matrix.values @ weights)) * 100
        sharpe = expected_return / max(expected_vol, 0.001)
        
        execution_ms = (time.time() - start_time) * 1000
        
        return AllocationResult(
            weights={t: float(w) for t, w in zip(self.tickers, weights)},
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            model_used="Inverse Volatility Weighting",
            execution_time_ms=execution_ms,
            warnings=self.warnings
        )
    
    def optimize_equal_weight(
        self,
        constraints_cfg: Optional[PortfolioConstraints] = None
    ) -> Optional[AllocationResult]:
        """
        Equal weighting (simple 1/N diversification).
        """
        import time
        start_time = time.time()
        
        if self._cov_matrix is None:
            if not self._fetch_price_data() or not self._calculate_statistics():
                return None
        
        n = len(self.tickers)
        weights = np.ones(n) / n
        
        expected_return = float(weights @ self._mean_returns.values) * 100
        expected_vol = float(np.sqrt(weights @ self._cov_matrix.values @ weights)) * 100
        sharpe = expected_return / max(expected_vol, 0.001)
        
        execution_ms = (time.time() - start_time) * 1000
        
        return AllocationResult(
            weights={t: float(w) for t, w in zip(self.tickers, weights)},
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            model_used="Equal Weight (1/N Diversification)",
            execution_time_ms=execution_ms,
            warnings=self.warnings
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_optimization_models() -> Dict[str, OptimizationModel]:
    """Get available optimization models."""
    return {
        "mvo": OptimizationModel(
            name="Mean-Variance Optimization",
            description="Markowitz MVO — minimizes volatility for target return",
            method="mvo",
            params={"target_return", "max_volatility"}
        ),
        "inverse_vol": OptimizationModel(
            name="Inverse Volatility Weighting",
            description="Risk parity style — higher weight to lower-vol instruments",
            method="inverse_vol",
            params={}
        ),
        "equal_weight": OptimizationModel(
            name="Equal Weight (1/N)",
            description="Simple diversification — equal weight across all instruments",
            method="equal_weight",
            params={}
        ),
    }
