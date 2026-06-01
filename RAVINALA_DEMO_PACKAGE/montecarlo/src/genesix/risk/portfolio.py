"""
Portfolio risk analyzer — VaR decomposition, efficient frontier, risk parity.
"""

import logging
from datetime import datetime, timedelta
from typing import Union

import pandas as pd
import numpy as np
from scipy import stats, optimize

from .risk_engine import GenesiXRiskEngine
from .correlation import CorrelationAnalyzer
from ..data.market_fetcher import MarketDataFetcher
from ..utils.quant_conventions import RISK_FREE_RATE, ANNUALIZATION_FACTOR_RETURN

logger = logging.getLogger(__name__)


class PortfolioRiskAnalyzer:
    """
    Comprehensive portfolio risk analytics.
    
    Integrates risk engine with correlation analysis for decomposition.
    """
    
    def __init__(self):
        """Initialize portfolio analyzer."""
        self.engine = GenesiXRiskEngine()
        self.correlations = CorrelationAnalyzer()
        self.market = MarketDataFetcher()
        logger.info("PortfolioRiskAnalyzer initialized")

    def _fetch_returns_for_weights(
        self,
        weights: dict[str, float],
        lookback_days: int = 252,
    ) -> pd.DataFrame:
        """Fetch close-based return series for the supplied portfolio weights."""
        if not weights:
            raise ValueError("Portfolio weights cannot be empty")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        returns = pd.DataFrame()

        for ticker in weights:
            ohlcv = self.market.get_historical_ohlcv(ticker, start_date, end_date)
            if len(ohlcv) == 0 or 'close' not in ohlcv.columns:
                continue
            returns[ticker] = ohlcv['close'].pct_change()

        returns = returns.dropna(how='all')
        if returns.empty:
            raise ValueError("Unable to build portfolio returns from market data")
        return returns
    
    def portfolio_var(
        self,
        returns: pd.DataFrame,
        weights: dict[str, float],
        confidence: float = 0.95,
        horizon: int = 1,
        method: str = 'historical',
    ) -> dict:
        """
        Portfolio VaR with diversification benefit calculation.
        
        Args:
            returns: DataFrame of asset returns (each column is an asset)
            weights: dict mapping asset name to weight (must sum to ~1.0)
            confidence: confidence level (0.90-0.99)
            horizon: days
            method: 'historical', 'parametric', 'cornish_fisher', 'monte_carlo'
        
        Returns: dict with portfolio_var, diversification_benefit, sum_marginal_vars
        """
        # Normalize weights
        total_weight = sum(weights.values())
        if abs(total_weight) < 0.01:
            return {'error': 'weights sum to zero'}
        
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # Portfolio returns
        asset_cols = [col for col in returns.columns if col in weights]
        if not asset_cols:
            return {'error': 'no matching assets in returns'}
        
        asset_returns = returns[asset_cols]
        portfolio_returns = (asset_returns * pd.Series(
            [weights[col] for col in asset_cols], index=asset_cols
        )).sum(axis=1)
        
        # VaR on portfolio returns
        portfolio_var = self.engine.var_historical(portfolio_returns, confidence, horizon)
        
        # Sum of marginal VARs (unhedged case)
        marginal_vars = []
        for asset in asset_cols:
            if asset in returns.columns:
                asset_var = self.engine.var_historical(
                    returns[asset], confidence, horizon
                )
                marginal_vars.append(weights[asset] * asset_var)
        
        sum_marginal = sum(marginal_vars) if marginal_vars else portfolio_var
        
        # Diversification benefit
        div_benefit = sum_marginal - portfolio_var
        
        return {
            'portfolio_var': float(portfolio_var),
            'sum_marginal_vars': float(sum_marginal),
            'diversification_benefit': float(div_benefit),
            'diversification_ratio': float(sum_marginal / portfolio_var) if portfolio_var > 0 else 1.0,
        }
    
    def marginal_var(
        self,
        returns: pd.DataFrame,
        weights: dict[str, float],
        confidence: float = 0.95,
        epsilon: float = 0.001,
    ) -> dict:
        """
        Marginal VaR per position (sensitivity to weight increase).
        
        dVaR/dw_i via epsilon bump method.
        """
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        marginal_vars = {}
        
        for asset in weights.keys():
            # Bump weight by epsilon
            bumped_weights = weights.copy()
            bumped_weights[asset] = bumped_weights.get(asset, 0) + epsilon
            
            # Normalize
            total = sum(bumped_weights.values())
            bumped_weights = {k: v / total for k, v in bumped_weights.items()}
            
            # VaR at bumped state
            var_bumped = self.portfolio_var(returns, bumped_weights, confidence)
            var_base = self.portfolio_var(returns, weights, confidence)
            
            var_b = var_bumped.get('portfolio_var', 0)
            var_a = var_base.get('portfolio_var', 0)
            
            # Derivative
            if epsilon > 0:
                marginal = (var_b - var_a) / epsilon
            else:
                marginal = 0.0
            
            marginal_vars[asset] = float(marginal)
        
        return marginal_vars
    
    def component_var(
        self,
        returns: pd.DataFrame,
        weights: dict[str, float],
        confidence: float = 0.95,
    ) -> dict:
        """
        Component VaR — contribution of each asset to total portfolio VaR.
        
        Returns: dict mapping asset to its VaR contribution
        """
        asset_cols = [col for col in returns.columns if col in weights]
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        portfolio_returns = (returns[asset_cols] * pd.Series(
            [weights[col] for col in asset_cols], index=asset_cols
        )).sum(axis=1)
        
        portfolio_var = self.engine.var_historical(portfolio_returns, confidence, 1)
        
        # Component as weight × correlation × asset_var
        components = {}
        for asset in asset_cols:
            asset_var = self.engine.var_historical(returns[asset], confidence, 1)
            correlation = returns[asset].corr(portfolio_returns)
            
            # Component VaR = weight × correlation × (asset_vol / portfolio_vol)
            component = weights[asset] * correlation * asset_var
            components[asset] = float(component)
        
        return components
    
    def risk_parity_weights(
        self,
        returns: pd.DataFrame,
        lookback_days: int | None = None,
    ) -> dict[str, float]:
        """
        Equal-risk allocation — each asset contributes equally to portfolio risk.
        
        Solved via scipy.optimize.minimize.
        """
        if lookback_days:
            returns = returns.iloc[-lookback_days:]
        
        assets = returns.columns.tolist()
        
        # Target: equal risk contribution
        cov_matrix = returns.cov()
        
        def objective_rp(weights):
            """Minimize squared differences in risk contributions."""
            portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
            marginal_vol = cov_matrix @ weights / portfolio_vol
            risk_contrib = weights * marginal_vol  # Risk contribution vector
            
            # Target is equal contributions (1/N each)
            target = portfolio_vol / len(assets)
            
            return np.sum((risk_contrib - target) ** 2)
        
        # Constraints: sum to 1, all positive
        constraints = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
        )
        bounds = tuple((0.01, 0.99) for _ in assets)
        
        # Initial guess: equal weights
        x0 = np.array([1 / len(assets)] * len(assets))
        
        try:
            result = optimize.minimize(
                objective_rp,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            
            if result.success:
                weights_array = result.x
            else:
                weights_array = x0
        except:
            weights_array = x0
        
        # Return as dict
        return {asset: float(w) for asset, w in zip(assets, weights_array)}
    
    def efficient_frontier(
        self,
        returns: pd.DataFrame,
        n_points: int = 50,
        risk_free_rate: float = RISK_FREE_RATE,
    ) -> dict:
        """
        Mean-variance efficient frontier, max Sharpe, minimum variance.
        
        Returns: dict with portfolios, optimal_weights, frontier_data
        """
        assets = returns.columns.tolist()
        mean_returns = returns.mean() * ANNUALIZATION_FACTOR_RETURN
        cov_matrix = returns.cov() * ANNUALIZATION_FACTOR_RETURN
        
        def portfolio_metrics(weights):
            """Return (annual_return, annual_volatility)."""
            ret = weights @ mean_returns
            vol = np.sqrt(weights @ cov_matrix @ weights)
            return ret, vol
        
        def negative_sharpe(weights):
            """Negative Sharpe ratio (for minimization)."""
            ret, vol = portfolio_metrics(weights)
            sharpe = (ret - risk_free_rate) / (vol + 1e-8)
            return -sharpe
        
        def portfolio_volatility(weights):
            """Portfolio volatility."""
            return np.sqrt(weights @ cov_matrix @ weights)
        
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1},)
        bounds = tuple((0.0, 1.0) for _ in assets)
        x0 = np.array([1 / len(assets)] * len(assets))
        
        # Min variance portfolio
        try:
            result_minvar = optimize.minimize(
                portfolio_volatility,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            min_var_weights = result_minvar.x
            min_var_ret, min_var_vol = portfolio_metrics(min_var_weights)
        except:
            min_var_weights = x0
            min_var_ret, min_var_vol = portfolio_metrics(x0)
        
        # Max Sharpe portfolio
        try:
            result_maxsharpe = optimize.minimize(
                negative_sharpe,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            max_sharpe_weights = result_maxsharpe.x
            max_sharpe_ret, max_sharpe_vol = portfolio_metrics(max_sharpe_weights)
            max_sharpe = (max_sharpe_ret - risk_free_rate) / (max_sharpe_vol + 1e-8)
        except:
            max_sharpe_weights = x0
            max_sharpe_ret, max_sharpe_vol = portfolio_metrics(x0)
            max_sharpe = 0.0
        
        # Frontier: n_points from min vol to max return
        frontier = []
        for target_ret in np.linspace(min_var_ret, mean_returns.max(), n_points):
            def constraint_return(w):
                return w @ mean_returns - target_ret
            
            constraints_with_target = (
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
                {'type': 'eq', 'fun': constraint_return},
            )
            
            try:
                result = optimize.minimize(
                    portfolio_volatility,
                    x0,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints_with_target,
                )
                if result.success:
                    _, vol = portfolio_metrics(result.x)
                    frontier.append({'return': float(target_ret), 'volatility': float(vol)})
            except:
                pass
        
        return {
            'min_variance': {
                'weights': {asset: float(w) for asset, w in zip(assets, min_var_weights)},
                'return': float(min_var_ret),
                'volatility': float(min_var_vol),
            },
            'max_sharpe': {
                'weights': {asset: float(w) for asset, w in zip(assets, max_sharpe_weights)},
                'return': float(max_sharpe_ret),
                'volatility': float(max_sharpe_vol),
                'sharpe_ratio': float(max_sharpe),
            },
            'frontier': frontier,
        }
    
    def portfolio_analytics(
        self,
        returns: Union[pd.DataFrame, dict[str, float]],
        weights: Union[dict[str, float], float, int, None] = None,
        portfolio_value: float = 100.0,
        horizon: int = 5,
    ) -> dict:
        """
        Comprehensive portfolio analytics report.
        
        Integrates all methods for dashboard consumption.
        """
        if isinstance(returns, dict):
            inferred_weights = returns
            if isinstance(weights, (int, float)):
                portfolio_value = float(weights)
            weights = inferred_weights
            returns = self._fetch_returns_for_weights(weights)

        if not isinstance(returns, pd.DataFrame):
            raise ValueError("Portfolio returns must be a DataFrame")
        if not isinstance(weights, dict):
            raise ValueError("Portfolio weights must be provided")

        # Portfolio VaR
        var_result = self.portfolio_var(returns, weights, 0.95, horizon)
        
        # Scenarios
        portfolio_returns = (returns[list(weights.keys())] * pd.Series(
            [weights[col] for col in returns.columns if col in weights], 
            index=[col for col in returns.columns if col in weights]
        )).sum(axis=1)
        
        scenarios = self.engine.simulate_return_scenarios(
            portfolio_returns.dropna(), horizon, portfolio_value
        )
        
        # Risk decomposition
        component = self.component_var(returns, weights)
        marginal = self.marginal_var(returns, weights)
        
        # Correlation info
        try:
            corr_data = self.correlations.rolling_correlation(list(weights.keys()))
            correlation_matrix = corr_data.get('current_matrix', {})
        except:
            correlation_matrix = {}
        
        return {
            'portfolio_value': float(portfolio_value),
            'horizon_days': horizon,
            'risk_metrics': {
                'var': var_result.get('portfolio_var', 0),
                'var_95': var_result.get('portfolio_var', 0),
                'diversification_ratio': var_result.get('diversification_ratio', 1.0),
            },
            'scenarios': scenarios.get('scenarios', []),
            'scenario_summary': scenarios.get('summary', {}),
            'risk_decomposition': {
                'component_var': component,
                'marginal_var': marginal,
            },
            'correlation_matrix': correlation_matrix.to_dict() if hasattr(correlation_matrix, 'to_dict') else {},
            'timestamps': pd.Timestamp.now().isoformat(),
        }
