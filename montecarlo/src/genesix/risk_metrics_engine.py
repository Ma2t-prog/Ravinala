"""
GenesiX Risk Metrics Engine — v2.1
Professional risk analytics: VaR, CVaR, drawdown, Sharpe, Sortino, Calmar, stress tests
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yfinance as yf
import logging

from genesix.utils.quant_conventions import (
    ANNUALIZATION_FACTOR_VOL,
    RISK_FREE_RATE,
    TRADING_DAYS,
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RiskMetrics:
    """Portfolio/instrument risk metrics."""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    cvar_95: float  # Conditional VaR (95% confidence)
    cvar_99: float  # Conditional VaR (99% confidence)
    max_drawdown: float  # Maximum historical drawdown
    sharpe_ratio: float  # Return per unit volatility
    sortino_ratio: float  # Return per unit downside volatility
    calmar_ratio: float  # Return per unit max drawdown
    volatility: float  # Annualized volatility
    skewness: float  # Distribution skewness
    kurtosis: float  # Distribution kurtosis
    correlation_with_market: float  # Beta-like correlation


@dataclass
class StressTestScenario:
    """Stress test scenario definition and results."""
    name: str
    description: str
    shock_vector: Dict[str, float]  # ticker -> % change


@dataclass  
class StressTestResult:
    """Results of stress test on portfolio."""
    scenario_name: str
    portfolio_value_change: float  # % change in portfolio
    instrument_impacts: Dict[str, float]  # ticker -> % change
    worst_hit: Tuple[str, float]  # (ticker, % change)
    best_performer: Tuple[str, float]  # (ticker, % change)


# ============================================================================
# RISK METRICS CALCULATOR
# ============================================================================

class RiskMetricsEngine:
    """Calculate professional risk metrics for portfolios and instruments."""
    
    def __init__(self, ticker: str = None, price_series: pd.Series = None, lookback_period: str = "2y"):
        """
        Initialize with either ticker or price series.
        
        Args:
            ticker: Stock ticker to analyze
            price_series: Pre-loaded price series
            lookback_period: Period for historical analysis
        """
        self.ticker = ticker
        self.price_series = price_series
        self.lookback_period = lookback_period
        self.returns = None
        self.cum_returns = None
        
        if price_series is not None:
            self._calculate_returns_from_series()
        elif ticker:
            self._fetch_and_process_data()
    
    def _fetch_and_process_data(self) -> bool:
        """Fetch price data and calculate returns."""
        try:
            data = yf.download(self.ticker, period=self.lookback_period, progress=False)
            self.price_series = data['Close']
            self._calculate_returns_from_series()
            logger.info(f"Fetched {len(self.price_series)} data points for {self.ticker}")
            return True
        except Exception as e:
            logger.error(f"Failed to fetch data for {self.ticker}: {e}")
            return False
    
    def _calculate_returns_from_series(self) -> None:
        """Calculate log returns from price series."""
        if self.price_series is None:
            return
        
        # Daily returns
        self.returns = np.log(self.price_series / self.price_series.shift(1)).dropna()
        
        # Cumulative returns (for drawdown calculation)
        self.cum_returns = (1 + self.returns).cumprod()
    
    def calculate_var(self, confidence: float = 0.95, method: str = "historical") -> float:
        """
        Calculate Value at Risk.
        
        Args:
            confidence: Confidence level (0.95 = 95%)
            method: "historical" or "parametric"
        
        Returns:
            VaR as % daily loss
        """
        if self.returns is None:
            return 0.0
        
        if method == "historical":
            var = np.percentile(self.returns, (1 - confidence) * 100)
        else:  # parametric
            mu = self.returns.mean()
            sigma = self.returns.std()
            from scipy import stats
            z_score = stats.norm.ppf(1 - confidence)
            var = mu + z_score * sigma
        
        return float(var * 100)
    
    def calculate_cvar(self, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        
        Args:
            confidence: Confidence level (0.95 = 95%)
        
        Returns:
            CVaR as % daily loss
        """
        if self.returns is None or len(self.returns) == 0:
            return 0.0
        
        var_pct = self.calculate_var(confidence, method="historical") / 100
        tail_returns = self.returns[self.returns <= var_pct]
        
        if len(tail_returns) > 0:
            cvar = tail_returns.mean()
            return float(cvar) * 100
        else:
            return float(var_pct) * 100
    
    def calculate_max_drawdown(self) -> float:
        """
        Calculate maximum historical drawdown.
        
        Returns:
            Max drawdown as % (e.g., -35.5 for -35.5% drawdown)
        """
        if self.cum_returns is None or len(self.cum_returns) == 0:
            return 0.0
        
        running_max = self.cum_returns.expanding().max()
        drawdown = (self.cum_returns - running_max) / running_max
        max_dd = drawdown.min()
        
        return float(max_dd) * 100
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = RISK_FREE_RATE) -> float:
        """
        Calculate Sharpe Ratio.
        
        Args:
            risk_free_rate: Annual risk-free rate from shared quant conventions.
        
        Returns:
            Sharpe ratio (annualized)
        """
        if self.returns is None or len(self.returns) < 2:
            return 0.0
        
        mean_ret = float(self.returns.mean().item()) if hasattr(self.returns.mean(), 'item') else float(self.returns.mean())
        std_ret = float(self.returns.std().item()) if hasattr(self.returns.std(), 'item') else float(self.returns.std())
        
        annual_return = mean_ret * TRADING_DAYS
        annual_vol = std_ret * ANNUALIZATION_FACTOR_VOL
        excess_returns = annual_return - risk_free_rate
        
        if annual_vol > 0.001:
            sharpe = excess_returns / annual_vol
        else:
            sharpe = 0.0
        
        return float(sharpe)
    
    def calculate_sortino_ratio(self, risk_free_rate: float = RISK_FREE_RATE) -> float:
        """
        Calculate Sortino Ratio (only penalizes downside volatility).
        
        Args:
            risk_free_rate: Annual risk-free rate
        
        Returns:
            Sortino ratio (annualized)
        """
        if self.returns is None or len(self.returns) < 2:
            return 0.0
        
        annual_return = float(self.returns.mean()) * TRADING_DAYS
        excess_returns = annual_return - risk_free_rate
        
        # Downside volatility (only negative returns)
        downside_returns = self.returns[self.returns < 0]
        
        if len(downside_returns) > 0:
            downside_volatility = float(downside_returns.std()) * ANNUALIZATION_FACTOR_VOL
        else:
            downside_volatility = 0.001
        
        if downside_volatility > 0.001:
            sortino = excess_returns / downside_volatility
        else:
            sortino = 0.0
        
        return float(sortino)
    
    def calculate_calmar_ratio(self) -> float:
        """
        Calculate Calmar Ratio (return / max drawdown).
        
        Returns:
            Calmar ratio
        """
        if self.returns is None or len(self.returns) < TRADING_DAYS:
            return 0.0
        
        annual_return = float(self.returns.mean()) * TRADING_DAYS
        max_dd = abs(self.calculate_max_drawdown() / 100)
        
        if max_dd > 0.001:
            calmar = annual_return / max_dd
        else:
            calmar = 0.0
        
        return float(calmar)
    
    def calculate_distribution_stats(self) -> Tuple[float, float]:
        """
        Calculate skewness and excess kurtosis.
        
        Returns:
            (skewness, kurtosis)
        """
        if self.returns is None or len(self.returns) < 3:
            return 0.0, 0.0
        
        from scipy import stats
        import numpy as np
        
        skewness_val = stats.skew(self.returns.values)
        kurtosis_val = stats.kurtosis(self.returns.values)
        
        # Ensure they're scalars
        skewness = float(np.asarray(skewness_val).item())
        kurtosis = float(np.asarray(kurtosis_val).item())
        
        return skewness, kurtosis
    
    def get_all_metrics(self, risk_free_rate: float = RISK_FREE_RATE) -> RiskMetrics:
        """
        Calculate all risk metrics at once.
        
        Returns:
            RiskMetrics object with all metrics populated
        """
        if self.returns is None:
            logger.warning("No data available for metrics calculation")
            return RiskMetrics(
                var_95=0.0, var_99=0.0, cvar_95=0.0, cvar_99=0.0,
                max_drawdown=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
                calmar_ratio=0.0, volatility=0.0, skewness=0.0, kurtosis=0.0,
                correlation_with_market=0.0
            )
        
        skewness, kurtosis = self.calculate_distribution_stats()
        
        return RiskMetrics(
            var_95=self.calculate_var(0.95),
            var_99=self.calculate_var(0.99),
            cvar_95=self.calculate_cvar(0.95),
            cvar_99=self.calculate_cvar(0.99),
            max_drawdown=self.calculate_max_drawdown(),
            sharpe_ratio=self.calculate_sharpe_ratio(risk_free_rate),
            sortino_ratio=self.calculate_sortino_ratio(risk_free_rate),
            calmar_ratio=self.calculate_calmar_ratio(),
            volatility=float(self.returns.std() * ANNUALIZATION_FACTOR_VOL * 100),
            skewness=skewness,
            kurtosis=kurtosis,
            correlation_with_market=0.0  # Placeholder
        )


# ============================================================================
# PRE-DEFINED STRESS SCENARIOS
# ============================================================================

def get_stress_scenarios() -> Dict[str, StressTestScenario]:
    """Get pre-defined stress test scenarios."""
    return {
        "global_financial_crisis": StressTestScenario(
            name="2008 Global Financial Crisis",
            description="Equities -50%, Credit spreads +300bps, Volatility 3x",
            shock_vector={
                "equities": -0.50,
                "bonds": +0.10,
                "commodities": -0.40,
                "volatility": 3.0,
            }
        ),
        "pandemic": StressTestScenario(
            name="COVID-19 Pandemic Shock",
            description="Equities -35%, Volatility 2.5x, Flight to safety",
            shock_vector={
                "equities": -0.35,
                "government_bonds": -0.05,
                "corporate_bonds": -0.20,
                "commodities": -0.30,
                "volatility": 2.5,
            }
        ),
        "rate_shock": StressTestScenario(
            name="Interest Rate Shock (+200bps)",
            description="Yields rise 200bps, equities decline, volatility rises",
            shock_vector={
                "equities": -0.15,
                "bonds": -0.12,
                "commodities": +0.05,
                "volatility": 1.5,
            }
        ),
        "oil_shock": StressTestScenario(
            name="Oil Price Spike (+50%)",
            description="Energy prices surge, reflationary scenario",
            shock_vector={
                "energy": +0.50,
                "equities": -0.10,
                "currencies": -0.05,
                "inflation_expectations": +0.15,
            }
        ),
        "credit_crisis": StressTestScenario(
            name="Credit Market Seizure",
            description="Credit spreads blow out, liquidity dries up",
            shock_vector={
                "corporate_bonds": -0.25,
                "bank_stocks": -0.30,
                "equities": -0.20,
                "credit_spreads": +2.0,
            }
        ),
        "geopolitical": StressTestScenario(
            name="Geopolitical Escalation",
            description="Safe haven flows, commodities spike",
            shock_vector={
                "equities": -0.15,
                "government_bonds": +0.05,
                "commodities": +0.25,
                "gold": +0.30,
                "volatility": 2.0,
            }
        ),
    }


# ============================================================================
# CORRELATION & COVARIANCE ANALYSIS
# ============================================================================

def calculate_correlation_matrix(
    instruments: List,
    lookback_period: str = "2y"
) -> Tuple[pd.DataFrame, bool]:
    """
    Calculate correlation matrix for list of instruments.
    
    Args:
        instruments: List of Instrument objects or tickers
        lookback_period: Historical period
    
    Returns:
        (correlation_dataframe, success_bool)
    """
    try:
        tickers = [inst.ticker if hasattr(inst, 'ticker') else inst for inst in instruments]
        
        data = yf.download(tickers, period=lookback_period, progress=False)['Close']
        
        if isinstance(data, pd.Series):
            data = pd.DataFrame(data)
        
        returns = data.pct_change().dropna()
        corr_matrix = returns.corr()
        
        return corr_matrix, True
        
    except Exception as e:
        logger.error(f"Failed to calculate correlation matrix: {e}")
        return pd.DataFrame(), False
