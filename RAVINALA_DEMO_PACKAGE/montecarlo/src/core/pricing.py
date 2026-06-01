"""
Ravinala by TSIVAHINY Matthias — Legacy pricing classes (Black-Scholes & Monte Carlo).
Maintained for API compatibility. New code should use engine.BlackScholesGreeks.
"""

import numpy as np
from scipy.stats import norm
from utils import d1, d2, validate_inputs, vanna as calc_vanna, volga as calc_volga


class BlackScholes:
    """Analytical Black-Scholes pricing (no carry — b=r assumed)."""

    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        d1_val = d1(S, K, T, r, sigma)
        d2_val = d2(d1_val, sigma, T)
        return S * norm.cdf(d1_val) - K * np.exp(-r * T) * norm.cdf(d2_val)

    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        d1_val = d1(S, K, T, r, sigma)
        d2_val = d2(d1_val, sigma, T)
        return K * np.exp(-r * T) * norm.cdf(-d2_val) - S * norm.cdf(-d1_val)

    @staticmethod
    def delta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        return norm.cdf(d1(S, K, T, r, sigma))

    @staticmethod
    def delta_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        return norm.cdf(d1(S, K, T, r, sigma)) - 1.0

    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        return norm.pdf(d1(S, K, T, r, sigma)) / (S * sigma * np.sqrt(T))

    @staticmethod
    def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        return S * norm.pdf(d1(S, K, T, r, sigma)) * np.sqrt(T) / 100.0

    @staticmethod
    def theta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        d1_val = d1(S, K, T, r, sigma)
        d2_val = d2(d1_val, sigma, T)
        return (
            -S * norm.pdf(d1_val) * sigma / (2.0 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2_val)
        ) / 365.0

    @staticmethod
    def rho_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
        validate_inputs(S, K, T, r, sigma)
        d1_val = d1(S, K, T, r, sigma)
        d2_val = d2(d1_val, sigma, T)
        return K * T * np.exp(-r * T) * norm.cdf(d2_val) / 100.0

    @staticmethod
    def vanna(S: float, K: float, T: float, r: float, sigma: float) -> float:
        return calc_vanna(S, K, T, r, sigma)

    @staticmethod
    def volga(S: float, K: float, T: float, r: float, sigma: float) -> float:
        return calc_volga(S, K, T, r, sigma)


class MonteCarlo:
    """Vectorized Monte Carlo pricing with antithetic variates."""

    @staticmethod
    def _simulate_terminal(
        S: float, K: float, T: float, r: float, sigma: float,
        num_simulations: int, num_steps: int,
    ) -> np.ndarray:
        """Return terminal spot prices using antithetic variates (2×num_simulations paths)."""
        validate_inputs(S, K, T, r, sigma)
        dt = T / num_steps
        drift = (r - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt)

        # Generate all increments at once: (num_steps, num_simulations)
        Z = np.random.standard_normal((num_steps, num_simulations))
        log_returns = drift + diffusion * Z        # (num_steps, num_sims)
        log_returns_anti = drift + diffusion * (-Z)

        S_T = S * np.exp(log_returns.sum(axis=0))
        S_T_anti = S * np.exp(log_returns_anti.sum(axis=0))
        return np.concatenate([S_T, S_T_anti])

    @staticmethod
    def call_price(
        S: float, K: float, T: float, r: float, sigma: float,
        num_simulations: int = 10_000, num_steps: int = 252,
    ) -> float:
        S_T = MonteCarlo._simulate_terminal(S, K, T, r, sigma, num_simulations, num_steps)
        return float(np.exp(-r * T) * np.mean(np.maximum(S_T - K, 0.0)))

    @staticmethod
    def put_price(
        S: float, K: float, T: float, r: float, sigma: float,
        num_simulations: int = 10_000, num_steps: int = 252,
    ) -> float:
        S_T = MonteCarlo._simulate_terminal(S, K, T, r, sigma, num_simulations, num_steps)
        return float(np.exp(-r * T) * np.mean(np.maximum(K - S_T, 0.0)))
