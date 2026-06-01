"""
GenesiX Backtesting Engine — v2.1
Historical portfolio simulation, performance attribution, risk analysis
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
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
class BacktestConfig:
    """Configuration for backtest run."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100_000
    rebalance_frequency: str = "monthly"  # "daily", "weekly", "monthly", "quarterly"
    benchmark_ticker: str = "SPY"  # Benchmark for comparison
    transaction_cost_bps: float = 10  # 10 basis points per trade


@dataclass
class BacktestResult:
    """Results from backtest run."""
    portfolio_value: pd.Series  # Daily NAV
    daily_returns: pd.Series  # Daily return %
    cumulative_returns: pd.Series  # Cumulative return from start
    
    # Performance metrics
    total_return: float  # %
    annual_return: float  # %
    annual_volatility: float  # %
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float  # %
    calmar_ratio: float
    
    # Benchmark comparison
    benchmark_returns: pd.Series
    benchmark_value: pd.Series
    excess_returns: pd.Series  # Outperformance
    beta: float
    alpha: float  # Annualized
    tracking_error: float  # %
    information_ratio: float
    
    # Attribution
    instrument_pnl: Dict[str, float]  # ticker -> P&L
    instrument_returns: Dict[str, float]  # ticker -> return %
    
    # Risks
    var_95: float  # %
    cvar_95: float  # %
    max_daily_loss: float  # %
    days_negative: int
    win_loss_ratio: float


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time."""
    date: datetime
    nav: float
    positions: Dict[str, float]  # ticker -> quantity
    weights: Dict[str, float]  # ticker -> % allocation
    cash: float


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class BacktestingEngine:
    """
    Historical portfolio backtester with rebalancing, benchmarking, attribution.
    """
    
    def __init__(self, 
                 tickers: List[str],
                 weights: Dict[str, float],
                 config: BacktestConfig):
        """
        Initialize backtester.
        
        Args:
            tickers: List of asset tickers
            weights: Target allocation (ticker -> weight 0-1)
            config: BacktestConfig object
        """
        self.tickers = tickers
        self.target_weights = weights
        self.config = config
        self.price_data = None
        self.benchmark_data = None
        
        # Validate inputs
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
    
    def _fetch_data(self) -> bool:
        """Fetch price data for all tickers and benchmark."""
        try:
            # Fetch portfolio tickers
            self.price_data = yf.download(
                self.tickers,
                start=self.config.start_date,
                end=self.config.end_date,
                progress=False
            )['Close']
            
            # Handle single ticker case
            if isinstance(self.price_data, pd.Series):
                self.price_data = pd.DataFrame({self.tickers[0]: self.price_data})
            
            # Fetch benchmark
            self.benchmark_data = yf.download(
                self.config.benchmark_ticker,
                start=self.config.start_date,
                end=self.config.end_date,
                progress=False
            )['Close']
            
            logger.info(f"Fetched data from {self.config.start_date.date()} to {self.config.end_date.date()}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return False
    
    def _rebalance_dates(self) -> List[datetime]:
        """Generate rebalancing dates based on frequency."""
        start = self.config.start_date
        end = self.config.end_date
        dates = [start]
        current = start
        
        if self.config.rebalance_frequency == "daily":
            freq = timedelta(days=1)
        elif self.config.rebalance_frequency == "weekly":
            freq = timedelta(weeks=1)
        elif self.config.rebalance_frequency == "monthly":
            freq = timedelta(days=30)
        else:  # quarterly
            freq = timedelta(days=91)
        
        while current < end:
            current += freq
            if current <= end:
                dates.append(current)
        
        return dates
    
    def run(self) -> Optional[BacktestResult]:
        """
        Run backtest simulation.
        
        Returns:
            BacktestResult object with full performance metrics
        """
        if not self._fetch_data():
            return None
        
        trading_days = self.price_data.index
        num_days = len(trading_days)
        
        # Initialize portfolio tracking
        portfolio_values = np.zeros(num_days)
        positions = {}  # ticker -> quantity over time
        cash_balance = self.config.initial_capital
        
        # Initialize positions based on target weights
        for ticker, weight in self.target_weights.items():
            if ticker in self.price_data.columns or (len(self.tickers) == 1 and ticker == self.tickers[0]):
                allocation = self.config.initial_capital * weight
                price = self.price_data[ticker].iloc[0]
                positions[ticker] = allocation / price
        
        # Simulate day-by-day
        for day_idx in range(num_days):
            current_date = trading_days[day_idx]
            
            # Calculate current portfolio value
            day_value = cash_balance
            for ticker, qty in positions.items():
                try:
                    price = self.price_data[ticker].iloc[day_idx]
                    day_value += qty * price
                except:
                    pass
            
            portfolio_values[day_idx] = day_value
            
            # Rebalance if needed
            if current_date in self._rebalance_dates():
                self._rebalance(positions, cash_balance, day_idx)
        
        # Calculate returns
        portfolio_series = pd.Series(portfolio_values, index=trading_days)
        daily_returns = portfolio_series.pct_change().dropna()
        cumulative_returns = (1 + daily_returns).cumprod() - 1
        
        # Calculate benchmark
        benchmark_returns = self.benchmark_data.pct_change().dropna()
        benchmark_cum = (1 + benchmark_returns).cumprod()
        benchmark_value = self.config.initial_capital * benchmark_cum
        
        # Align indices
        common_idx = portfolio_series.index.intersection(benchmark_value.index)
        
        # Performance metrics
        annual_return = self._calculate_annual_return(daily_returns)
        annual_vol = daily_returns.std() * ANNUALIZATION_FACTOR_VOL
        sharpe = self._calculate_sharpe(daily_returns)
        sortino = self._calculate_sortino(daily_returns)
        max_dd = self._calculate_max_drawdown(portfolio_series)
        calmar = annual_return / max(abs(max_dd / 100), 0.001)
        
        # Benchmark comparison
        bench_annual_return = self._calculate_annual_return(benchmark_returns)
        # Align indices for comparison
        if len(daily_returns.index) > len(benchmark_returns.index):
            common_dates = daily_returns.index.intersection(benchmark_returns.index)
            daily_ret_aligned = daily_returns.loc[common_dates].values.flatten()
            bench_ret_aligned = benchmark_returns.loc[common_dates].values.flatten()
        else:
            daily_ret_aligned = daily_returns.values.flatten()
            bench_ret_aligned = benchmark_returns.values.flatten()[:len(daily_ret_aligned)]
        
        excess_returns_arr = daily_ret_aligned - bench_ret_aligned
        beta = self._calculate_beta(daily_returns, benchmark_returns)
        alpha_val = float(
            annual_return
            - (
                RISK_FREE_RATE
                + beta * (bench_annual_return - RISK_FREE_RATE)
            )
        )
        
        # Convert to scalars
        tracking_error_val = float(
            np.std(excess_returns_arr) * ANNUALIZATION_FACTOR_VOL * 100
        )
        info_ratio = float((annual_return - bench_annual_return) / max(tracking_error_val / 100, 0.001))
        
        # Risk metrics
        var_95 = np.percentile(daily_returns, 5)
        cvar_95 = daily_returns[daily_returns <= var_95].mean()
        max_daily_loss = daily_returns.min()
        days_neg = (daily_returns < 0).sum()
        days_pos = (daily_returns > 0).sum()
        win_loss = days_pos / max(days_neg, 1)
        
        # Attribution (simplified)
        instrument_pnl = {}
        instrument_returns = {}
        for ticker in self.tickers:
            if ticker in self.price_data.columns:
                ticker_returns = self.price_data[ticker].pct_change().dropna()
                instrument_returns[ticker] = (
                    ticker_returns.mean() * TRADING_DAYS * 100
                )
                allocation = self.target_weights.get(ticker, 0)
                instrument_pnl[ticker] = allocation * annual_return
        
        return BacktestResult(
            portfolio_value=portfolio_series,
            daily_returns=daily_returns * 100,  # Convert to %
            cumulative_returns=cumulative_returns * 100,
            total_return=((portfolio_values[-1] / self.config.initial_capital) - 1) * 100,
            annual_return=annual_return * 100,
            annual_volatility=annual_vol * 100,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd * 100,
            calmar_ratio=calmar,
            benchmark_returns=benchmark_returns * 100,
            benchmark_value=benchmark_value,
            excess_returns=pd.Series(excess_returns_arr * 100),
            beta=beta,
            alpha=alpha_val * 100,
            tracking_error=tracking_error_val,
            information_ratio=info_ratio,
            instrument_pnl=instrument_pnl,
            instrument_returns=instrument_returns,
            var_95=var_95 * 100,
            cvar_95=cvar_95 * 100,
            max_daily_loss=max_daily_loss * 100,
            days_negative=days_neg,
            win_loss_ratio=win_loss,
        )
    
    def _rebalance(self, positions: Dict, cash: float, day_idx: int) -> None:
        """Rebalance portfolio to target weights."""
        # Simplified rebalance (in production, would calculate transaction costs)
        total_value = cash
        for ticker, qty in positions.items():
            total_value += qty * self.price_data[ticker].iloc[day_idx]
        
        for ticker, target_weight in self.target_weights.items():
            target_value = total_value * target_weight
            current_value = positions.get(ticker, 0) * self.price_data[ticker].iloc[day_idx]
            
            # Adjust position (with transaction costs)
            cost = abs(target_value - current_value) * (self.config.transaction_cost_bps / 10000)
            # Position update deferred for simplicity
    
    @staticmethod
    def _calculate_annual_return(daily_returns: pd.Series) -> float:
        """Calculate annualized return."""
        return (
            (1 + daily_returns).prod()
            ** (TRADING_DAYS / len(daily_returns))
            - 1
        )
    
    @staticmethod
    def _calculate_sharpe(
        daily_returns: pd.Series, risk_free_rate: float | None = None
    ) -> float:
        """Calculate Sharpe ratio."""
        rf = RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
        annual_return = BacktestingEngine._calculate_annual_return(daily_returns)
        annual_vol = daily_returns.std() * ANNUALIZATION_FACTOR_VOL
        return (annual_return - rf) / max(annual_vol, 0.001)
    
    @staticmethod
    def _calculate_sortino(
        daily_returns: pd.Series, risk_free_rate: float | None = None
    ) -> float:
        """Calculate Sortino ratio."""
        rf = RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
        annual_return = BacktestingEngine._calculate_annual_return(daily_returns)
        downside = daily_returns[daily_returns < 0]
        downside_vol = (
            downside.std() * ANNUALIZATION_FACTOR_VOL if len(downside) > 0 else 0.001
        )
        return (annual_return - rf) / max(downside_vol, 0.001)
    
    @staticmethod
    def _calculate_max_drawdown(series: pd.Series) -> float:
        """Calculate maximum drawdown."""
        running_max = series.expanding().max()
        drawdown = (series - running_max) / running_max
        return drawdown.min()
    
    @staticmethod
    def _calculate_beta(returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate beta vs market returns."""
        common_idx = returns.index.intersection(market_returns.index)
        returns_aligned = returns.loc[common_idx].values.reshape(-1)
        market_aligned = market_returns.loc[common_idx].values.reshape(-1)
        
        if len(returns_aligned) < 2:
            return 1.0
        
        # Calculate covariance and variance
        cov_val = np.cov(returns_aligned, market_aligned)[0, 1]
        market_variance = np.var(market_aligned, ddof=1)
        
        if market_variance == 0:
            return 1.0
        
        return cov_val / market_variance


# ============================================================================
# HELPERS
# ============================================================================

def create_backtest_config(
    start_date: str = "2020-01-01",
    end_date: str = None,
    initial_capital: float = 100_000
) -> BacktestConfig:
    """Create backtest config from string dates."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    
    return BacktestConfig(
        start_date=start,
        end_date=end,
        initial_capital=initial_capital
    )
