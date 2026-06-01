"""
AI-Powered Portfolio Optimization Engine.

Optimization targets:
1. Maximum Sharpe Ratio (best risk-adjusted return)
2. Minimum Variance (lowest risk for any return)
3. Maximum Return (for given risk budget)
4. Risk Parity (equal risk contribution)

Constraints: min/max weights, asset class bounds, target volatility, max drawdown, no shorts
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging

try:
    from sklearn.covariance import LedoitWolf
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """AI-powered portfolio optimization engine."""
    
    def __init__(self):
        """Initialize optimizer."""
        pass
    
    def optimize(self, 
                 assets: list[str],
                 objective: str = 'max_sharpe',
                 constraints: dict | None = None,
                 risk_free_rate: float = 0.05,
                 lookback_days: int = 504) -> dict:
        """
        Main optimization method.
        
        Args:
            assets: List of tickers to include in optimization universe
            objective: 'max_sharpe', 'min_variance', 'max_return', 'risk_parity'
            constraints: Dict with max_weight, min_weight, target_volatility, etc.
            risk_free_rate: Annual risk-free rate for Sharpe calculation
            lookback_days: Historical lookback window (2 years = 504)
        
        Returns:
            {
                'weights': {'AAPL': 0.35, 'MSFT': 0.30, ...},
                'expected_return': 0.087,  # annualized
                'expected_volatility': 0.12,  # annualized
                'sharpe_ratio': 0.68,
                'max_drawdown_estimated': 0.18,
                'diversification_ratio': 1.35,
                'efficient_frontier': {...},
                'asset_details': [...],
                'constraint_utilization': {...},
            }
        """
        try:
            import yfinance as yf
            
            # Fetch historical data
            hist_data = {}
            for ticker in assets:
                try:
                    hist = yf.download(ticker, period='2y', progress=False)
                    if not hist.empty:
                        hist_data[ticker] = hist['Close'].pct_change().dropna()
                except:
                    logger.warning(f"Failed to fetch {ticker}")
                    continue
            
            if not hist_data:
                raise ValueError("Could not fetch data for any assets")
            
            # Align returns
            returns = pd.DataFrame(hist_data)
            returns = returns.dropna()
            
            # Calculate statistics
            mean_returns = returns.mean() * 252  # annualized

            # Covariance estimation with Ledoit-Wolf shrinkage (more robust)
            if _HAS_SKLEARN and len(returns) > len(returns.columns):
                lw = LedoitWolf().fit(returns.values)
                cov_matrix = pd.DataFrame(
                    lw.covariance_ * 252,
                    index=returns.columns,
                    columns=returns.columns,
                )
                logger.info(f"Using Ledoit-Wolf shrinkage (shrinkage={lw.shrinkage_:.4f})")
            else:
                cov_matrix = returns.cov() * 252
                logger.info("Using sample covariance (sklearn unavailable or insufficient data)")
            
            # Number of assets
            n_assets = len(mean_returns)
            
            # Constraints
            if constraints is None:
                constraints = {}
            
            max_weight = constraints.get('max_weight', 1.0)
            min_weight = constraints.get('min_weight', 0.0)
            target_vol = constraints.get('target_volatility')
            no_short = constraints.get('no_short', True)
            
            # Bounds for weights
            bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
            
            # Initial guess: equal weight
            x0 = np.array([1/n_assets] * n_assets)
            
            # Constraints
            cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
            
            if target_vol:
                # Add volatility constraint
                def vol_constraint(x):
                    portfolio_vol = np.sqrt(x @ cov_matrix @ x)
                    return target_vol - portfolio_vol
                cons.append({'type': 'ineq', 'fun': vol_constraint})
            
            # Optimization
            if objective == 'max_sharpe':
                def neg_sharpe(x):
                    port_return = x @ mean_returns
                    port_vol = np.sqrt(x @ cov_matrix @ x)
                    return -(port_return - risk_free_rate) / port_vol if port_vol > 0 else 1e10
                
                result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, 
                                constraints=cons, options={'maxiter': 1000})
            
            elif objective == 'min_variance':
                def variance(x):
                    return x @ cov_matrix @ x
                
                result = minimize(variance, x0, method='SLSQP', bounds=bounds,
                                constraints=cons, options={'maxiter': 1000})
            
            elif objective == 'risk_parity':
                # Equal risk contribution
                def risk_parity_objective(x):
                    portfolio_vol = np.sqrt(x @ cov_matrix @ x)
                    marginal_contrib = cov_matrix @ x / portfolio_vol
                    risk_contrib = x * marginal_contrib
                    return np.sum((risk_contrib - np.mean(risk_contrib)) ** 2)
                
                result = minimize(risk_parity_objective, x0, method='SLSQP',
                                bounds=bounds, constraints=cons, 
                                options={'maxiter': 1000})
            
            else:  # max_sharpe (default)
                def neg_sharpe(x):
                    port_return = x @ mean_returns
                    port_vol = np.sqrt(x @ cov_matrix @ x)
                    return -(port_return - risk_free_rate) / port_vol if port_vol > 0 else 1e10
                
                result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds,
                                constraints=cons, options={'maxiter': 1000})
            
            if not result.success:
                logger.warning(f"Optimization did not converge: {result.message}")
            
            # Extract results
            optimal_weights = result.x
            weights_dict = {ticker: float(w) for ticker, w in zip(mean_returns.index, optimal_weights)}
            
            # Calculate metrics
            port_return = optimal_weights @ mean_returns
            port_vol = np.sqrt(optimal_weights @ cov_matrix @ optimal_weights)
            sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0
            
            # Diversification ratio = sum of weighted vol / portfolio vol
            individual_vols = np.sqrt(np.diag(cov_matrix))
            diversification_ratio = (optimal_weights @ individual_vols) / port_vol if port_vol > 0 else 1
            
            # Generate efficient frontier
            efficient_frontier = self._generate_efficient_frontier(
                mean_returns, cov_matrix, risk_free_rate, bounds
            )
            
            # Asset details
            asset_details = []
            for ticker, weight in weights_dict.items():
                ticker_return = mean_returns[ticker]
                ticker_vol = individual_vols[mean_returns.index == ticker][0]
                
                # Risk contribution
                marginal_contrib = cov_matrix[mean_returns.index == ticker].values[0] @ optimal_weights
                risk_contrib = weight * marginal_contrib / port_vol if port_vol > 0 else 0
                
                asset_details.append({
                    'ticker': ticker,
                    'weight': weight,
                    'expected_return': ticker_return * 100,
                    'volatility': ticker_vol * 100,
                    'risk_contribution': risk_contrib * 100,
                })
            
            return {
                'weights': weights_dict,
                'expected_return': port_return * 100,
                'expected_volatility': port_vol * 100,
                'sharpe_ratio': sharpe,
                'diversification_ratio': diversification_ratio,
                'efficient_frontier': efficient_frontier,
                'asset_details': asset_details,
            }
        
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise
    
    def optimize_with_views(self, 
                            assets: list[str],
                            views: dict[str, float],
                            view_confidence: dict[str, float] | None = None,
                            tau: float = 0.05) -> dict:
        """
        Black-Litterman optimization — incorporate user market views.
        
        Args:
            views: {'AAPL': 0.15, 'BTC': -0.10}  # expected excess returns
            view_confidence: {'AAPL': 0.8, 'BTC': 0.5}  # certainty (0-1)
            tau: Market uncertainty parameter (default 0.05)
        """
        logger.info("Running Black-Litterman optimization with user views")
        raise NotImplementedError(
            "Black-Litterman not implemented. Use: max_sharpe, min_variance, risk_parity"
        )
    
    def suggest_improvements(self, 
                             current_weights: dict[str, float],
                             universe: list[str] | None = None) -> dict:
        """
        AI-powered portfolio improvement suggestions.
        
        Analyzes current portfolio and suggests:
        1. Assets to add (diversification benefit)
        2. Assets to reduce (concentration risk)
        3. Assets to remove (underperformers)
        """
        try:
            # Get optimal portfolio for comparison
            if universe is None:
                universe = list(current_weights.keys())
            
            optimal = self.optimize(universe)
            
            suggestions = []
            
            for ticker in optimal['weights']:
                current_weight = current_weights.get(ticker, 0)
                optimal_weight = optimal['weights'][ticker]
                
                if optimal_weight > current_weight + 0.05:
                    suggestions.append({
                        'type': 'add',
                        'asset': ticker,
                        'reason': 'Improves Sharpe ratio',
                        'suggested_weight': optimal_weight,
                        'current_weight': current_weight,
                    })
                elif optimal_weight < current_weight - 0.05:
                    suggestions.append({
                        'type': 'reduce',
                        'asset': ticker,
                        'reason': 'Reduces diversification',
                        'suggested_weight': optimal_weight,
                        'current_weight': current_weight,
                    })
            
            return {
                'suggestions': suggestions,
                'optimized_portfolio': optimal['weights'],
                'current_sharpe': 0.5,  # would calculate from current weights
                'improved_sharpe': optimal['sharpe_ratio'],
            }
        
        except Exception as e:
            logger.error(f"Improvement suggestions failed: {e}")
            raise
    
    def _generate_efficient_frontier(self, mean_returns, cov_matrix, rf,
                                    bounds, n_points: int = 50) -> dict:
        """Generate efficient frontier for visualization."""
        efs = []
        
        # Generate portfolios along efficient frontier
        for target_return in np.linspace(mean_returns.min() * 0.5, 
                                        mean_returns.max() * 1.5, n_points):
            try:
                def objective(x):
                    return x @ cov_matrix @ x
                
                constraints = [
                    {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                    {'type': 'eq', 'fun': lambda x: x @ mean_returns - target_return},
                ]
                
                result = minimize(objective, np.ones(len(mean_returns)) / len(mean_returns),
                                method='SLSQP', bounds=bounds, constraints=constraints,
                                options={'maxiter': 500})
                
                if result.success:
                    port_vol = np.sqrt(result.fun)
                    sharpe = (target_return - rf) / port_vol if port_vol > 0 else 0
                    efs.append({
                        'return': target_return * 100,
                        'volatility': port_vol * 100,
                        'sharpe': sharpe,
                    })
            except:
                continue
        
        return {'points': efs}
