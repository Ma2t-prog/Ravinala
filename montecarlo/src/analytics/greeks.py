"""
Options Greeks Calculator

Calculates the Greeks for options pricing and risk management:
- Delta: Sensitivity to spot price change
- Gamma: Change in Delta
- Vega: Sensitivity to volatility (per 1%)
- Theta: Time decay (per day)
- Rho: Sensitivity to interest rates (per 1%)

Uses Black-Scholes model for European-style options.

Usage:
    from analytics.greeks import GreeksCalculator
    
    S = 150.25     # Spot price
    K = 150.00     # Strike price
    r = 0.05       # Risk-free rate
    sigma = 0.25   # Volatility (25%)
    T = 0.1667     # Time to expiration (60 days = 60/365 years)
    
    delta = GreeksCalculator.delta(S, K, r, sigma, T, "call")
    gamma = GreeksCalculator.gamma(S, K, r, sigma, T, "call")
    vega = GreeksCalculator.vega(S, K, r, sigma, T, "call")
    theta = GreeksCalculator.theta(S, K, r, sigma, T, "call")
    rho = GreeksCalculator.rho(S, K, r, sigma, T, "call")
"""

import numpy as np
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

class GreeksCalculator:
    """
    Calculates option Greeks using Black-Scholes model.
    
    Assumptions:
    - European-style options (exercise only at expiration)
    - No dividends
    - No transaction costs
    - Constant volatility
    """
    
    @staticmethod
    def black_scholes(
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        option_type: str = "call"
    ) -> tuple:
        """
        Black-Scholes option pricing formula.
        
        Args:
            S: Spot price (current underlying price)
            K: Strike price (exercise price)
            r: Risk-free rate (annual, e.g., 0.05 = 5%)
            sigma: Volatility (annual, e.g., 0.25 = 25%)
            T: Time to expiration (years, e.g., 0.1667 = 60 days)
            option_type: "call" or "put"
        
        Returns:
            (price, d1, d2) - Option price and intermediate values
        """
        # Prevent division by zero
        if T <= 0 or sigma <= 0:
            logger.warning("Invalid inputs: T > 0 and sigma > 0 required")
            return 0.0, 0.0, 0.0
        
        # d1 and d2 from Black-Scholes
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Option price
        if option_type.lower() == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type.lower() == "put":
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError(f"Unknown option type: {option_type}")
        
        return price, d1, d2
    
    @staticmethod
    def delta(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """
        Delta: Rate of change of option price with respect to spot price.
        
        Interpretation:
        - Call delta: 0 to 1 (OTM call has low delta, ITM high)
        - Put delta: -1 to 0 (OTM put has near 0, ITM near -1)
        
        Example: Delta = 0.6 means for $1 increase in spot, call increases $0.60
        
        Args:
            option_type: "call" or "put"
        
        Returns:
            Delta value (sensitivity to 1$ spot move)
        """
        _, d1, _ = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        if option_type.lower() == "call":
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """
        Gamma: Change in delta for 1$ move in spot price.
        
        High gamma = delta changes quickly (risky)
        Low gamma = delta stable (less risky)
        
        Returns:
            Gamma value (sensitivity of delta)
        """
        _, d1, _ = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        # Gamma formula (same for calls and puts)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        return gamma
    
    @staticmethod
    def vega(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """
        Vega: Option price change for 1% increase in volatility.
        
        High vega = sensitive to vol changes
        Example: Vega = 0.2 means +1% vol → option price +$0.20
        
        Returns:
            Vega value (change per 1% vol change)
        """
        _, d1, _ = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        # Vega formula (same for calls and puts)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% volatility
        
        return vega
    
    @staticmethod
    def theta(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """
        Theta: Option price change per 1 day passing (time decay).
        
        Negative theta = option loses value as time passes (good for sellers)
        Example: Theta = -0.05 means option loses $0.05 per day
        
        Returns:
            Theta value (change per day, annualized volatility basis)
        """
        _, d1, d2 = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        if option_type.lower() == "call":
            theta_val = (
                -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * norm.cdf(d2)
            )
        else:  # put
            theta_val = (
                -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * norm.cdf(-d2)
            )
        
        return theta_val / 365  # Return per day
    
    @staticmethod
    def rho(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """
        Rho: Option price change for 1% increase in interest rates.
        
        Example: Rho = 0.3 means +1% rates → call option +$0.30
        
        Returns:
            Rho value (change per 1% rate change)
        """
        _, _, d2 = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        if option_type.lower() == "call":
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:  # put
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return rho
    
    @staticmethod
    def price(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> float:
        """Get option price"""
        price, _, _ = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        return price
    
    @staticmethod
    def get_all_greeks(S: float, K: float, r: float, sigma: float, T: float, option_type: str = "call") -> dict:
        """
        Calculate all Greeks at once.
        
        Returns:
            Dict with price and all Greeks
        """
        price, _, _ = GreeksCalculator.black_scholes(S, K, r, sigma, T, option_type)
        
        return {
            "price": price,
            "delta": GreeksCalculator.delta(S, K, r, sigma, T, option_type),
            "gamma": GreeksCalculator.gamma(S, K, r, sigma, T, option_type),
            "vega": GreeksCalculator.vega(S, K, r, sigma, T, option_type),
            "theta": GreeksCalculator.theta(S, K, r, sigma, T, option_type),
            "rho": GreeksCalculator.rho(S, K, r, sigma, T, option_type),
        }

# ================================
# EXAMPLE USAGE
# ================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # AAPL call option example
    S = 150.25      # AAPL current price
    K = 150.00      # Strike price
    r = 0.05        # 5% risk-free rate
    sigma = 0.25    # 25% volatility
    T = 60 / 365    # 60 days to expiration
    
    print("\n=== AAPL $150 Call Option ===")
    print(f"Spot: ${S} | Strike: ${K} | Vol: {sigma*100:.1f}% | Days: 60 | Rate: {r*100:.1f}%\n")
    
    greeks = GreeksCalculator.get_all_greeks(S, K, r, sigma, T, "call")
    
    print(f"Option Price: ${greeks['price']:.2f}")
    print(f"\nGreeks:")
    print(f"  Delta: {greeks['delta']:.4f} (per $1 spot move)")
    print(f"  Gamma: {greeks['gamma']:.4f} (delta sensitivity)")
    print(f"  Vega:  ${greeks['vega']:.4f} (per 1% vol)")
    print(f"  Theta: ${greeks['theta']:.4f} (per day)")
    print(f"  Rho:   ${greeks['rho']:.4f} (per 1% rate)")
    
    # Put option
    print("\n=== AAPL $150 Put Option ===")
    put_greeks = GreeksCalculator.get_all_greeks(S, K, r, sigma, T, "put")
    
    print(f"Option Price: ${put_greeks['price']:.2f}")
    print(f"\nGreeks:")
    print(f"  Delta: {put_greeks['delta']:.4f}")
    print(f"  Gamma: {put_greeks['gamma']:.4f}")
    print(f"  Vega:  ${put_greeks['vega']:.4f}")
    print(f"  Theta: ${put_greeks['theta']:.4f}")
    print(f"  Rho:   ${put_greeks['rho']:.4f}")
