"""
Ravinala Risk Management Module
Value-at-Risk, Conditional VaR, Stress Testing, Scenario Analysis
"""

import numpy as np
from scipy.stats import norm
from typing import Tuple, Dict, List
import warnings

warnings.filterwarnings('ignore')


class RiskAnalytics:
    """Comprehensive risk calculation suite."""

    @staticmethod
    def value_at_risk_historical(returns: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        """Historical VaR via empirical quantile."""
        var = np.percentile(returns, (1 - confidence) * 100)
        return var, abs(var)

    @staticmethod
    def value_at_risk_parametric(returns: np.ndarray, confidence: float = 0.95, position_value: float = 100.0) -> Tuple[float, float]:
        """
        Parametric VaR assuming normal distribution.

        Formula: VaR = μ + σ * Z(1-confidence)
        """
        mu = np.mean(returns)
        sigma = np.std(returns)
        z_score = norm.ppf(1 - confidence)
        var = mu + sigma * z_score
        dollar_loss = abs(var * position_value)
        return var, dollar_loss

    @staticmethod
    def conditional_var(returns: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        """Conditional VaR (Expected Shortfall) — average of losses beyond VaR."""
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()
        return cvar, abs(cvar)

    @staticmethod
    def stress_test_scenario(spot: float, strike: float, T: float, r: float,
                             vol: float, carry: float, spot_shock: float = -0.20) -> Dict:
        """
        Compute P&L under extreme market moves.

        spot_shock: Spot price shock (e.g., -0.20 = -20% crash). Vol is also shocked
        by +50% to reflect typical stress co-movement.
        """
        from engine import BlackScholesGreeks

        bs = BlackScholesGreeks()

        base_call = bs.call_price(spot, strike, T, r, carry, vol)
        base_put = bs.put_price(spot, strike, T, r, carry, vol)

        shocked_spot = spot * (1 + spot_shock)
        shocked_call = bs.call_price(shocked_spot, strike, T, r, carry, vol)
        shocked_put = bs.put_price(shocked_spot, strike, T, r, carry, vol)

        vol_shock = vol * 1.5
        shocked_vol_call = bs.call_price(shocked_spot, strike, T, r, carry, vol_shock)
        shocked_vol_put = bs.put_price(shocked_spot, strike, T, r, carry, vol_shock)

        return {
            'spot_shock_pct': spot_shock * 100,
            'shocked_spot': shocked_spot,
            'call_pnl_spot': shocked_call - base_call,
            'put_pnl_spot': shocked_put - base_put,
            'call_pnl_vol': shocked_vol_call - base_call,
            'put_pnl_vol': shocked_vol_put - base_put,
            'call_pnl_combined': shocked_vol_call - base_call,
            'put_pnl_combined': shocked_vol_put - base_put,
        }

    @staticmethod
    def scenario_multiple_shocks(spot: float, strike: float, T: float, r: float,
                                 vol: float, carry: float) -> Dict[str, Dict]:
        """Multiple stress scenarios: -20%, -10%, 0%, +10%, +20%."""
        shocks = [-0.20, -0.10, 0.0, 0.10, 0.20]
        return {
            f"{shock * 100:+.0f}% Spot": RiskAnalytics.stress_test_scenario(
                spot, strike, T, r, vol, carry, shock
            )
            for shock in shocks
        }

    @staticmethod
    def var_by_delta_normal(delta: float, spot: float, vol: float, T: float,
                            position_size: float = 1.0, confidence: float = 0.95) -> float:
        """
        Delta-Normal VaR approximation using Greeks.

        VaR ≈ Position * Delta * Spot * Vol * sqrt(T) * Z(confidence)
        """
        spot_shock = vol * np.sqrt(T) * norm.ppf(confidence)
        pnl_change = position_size * delta * spot * spot_shock
        return abs(pnl_change)

    @staticmethod
    def var_by_monte_carlo(payoff_pv: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        """VaR from a Monte Carlo payoff distribution."""
        initial_value = np.mean(payoff_pv)
        pnl = payoff_pv - initial_value
        var = np.percentile(pnl, (1 - confidence) * 100)
        return var, abs(var)

    @staticmethod
    def risk_decomposition(spot: float, strike: float, T: float, r: float,
                           vol: float, carry: float, option_type: str = 'call') -> Dict[str, float]:
        """
        Break down risk by Greeks:
        - Delta risk (spot moves)
        - Gamma risk (convexity)
        - Vega risk (vol moves)
        - Theta risk (time decay)
        - Rho risk (rate moves)
        """
        from engine import BlackScholesGreeks

        bs = BlackScholesGreeks()

        delta = bs.delta(spot, strike, T, r, carry, vol, option_type)
        gamma = bs.gamma(spot, strike, T, r, carry, vol)
        vega = bs.vega(spot, strike, T, r, carry, vol)
        theta = bs.theta(spot, strike, T, r, carry, vol, option_type)
        rho = bs.rho(spot, strike, T, r, carry, vol, option_type)

        return {
            '-1% Spot': delta * spot * (-0.01),
            '+1% Spot': delta * spot * (0.01),
            'Gamma Risk (1% move)': 0.5 * gamma * (spot * 0.01) ** 2,
            '+100bps Vol': vega * 0.01,
            '-100bps Vol': -vega * 0.01,
            '1 Day Decay': theta,
            '+100bps Rate': rho * 0.01,
        }


class PortfolioRisk:
    """Portfolio-level risk aggregation."""

    @staticmethod
    def aggregate_greeks(positions: List[Dict]) -> Dict[str, float]:
        """Aggregate Greeks across multiple positions (weighted by notional)."""
        keys = ['delta', 'gamma', 'vega', 'theta', 'rho']
        return {
            f'portfolio_{k}': sum(p.get(k, 0) * p.get('notional', 1) for p in positions)
            for k in keys
        }

    @staticmethod
    def marginal_var(position_delta: float, portfolio_delta: float, var_portfolio: float) -> float:
        """
        Marginal VaR — contribution of a position to portfolio risk.

        Simplified: Marginal VaR ≈ (Position Delta / Portfolio Delta) * Portfolio VaR
        """
        if portfolio_delta == 0:
            return 0
        return (position_delta / portfolio_delta) * var_portfolio

    @staticmethod
    def correlation_breakdown_warning(correlation: float, historical_avg: float = 0.5,
                                      threshold: float = 0.05) -> bool:
        """Alert if correlation deviates significantly from historical average (tail risk signal)."""
        return abs(correlation - historical_avg) > threshold
