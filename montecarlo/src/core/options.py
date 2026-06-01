"""
Ravinala by TSIVAHINY Matthias — European Call and Put option classes.
"""

from dataclasses import dataclass
import numpy as np
from scipy.stats import norm
from pricing import BlackScholes, MonteCarlo


@dataclass
class Option:
    """Base class for European options."""
    spot_price: float      # S
    strike_price: float    # K
    expiration: float      # T (years)
    risk_free_rate: float  # r
    volatility: float      # σ

    def __post_init__(self) -> None:
        if self.spot_price <= 0:
            raise ValueError("Spot price must be positive")
        if self.strike_price <= 0:
            raise ValueError("Strike price must be positive")
        if self.expiration <= 0:
            raise ValueError("Expiration must be positive")
        if self.volatility <= 0:
            raise ValueError("Volatility must be positive")

    # ── shared helpers ────────────────────────────────────────────────────────
    def _d1(self) -> float:
        S, K, T, r, sigma = self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility
        return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    def _d2(self) -> float:
        return self._d1() - self.volatility * np.sqrt(self.expiration)

    def gamma(self) -> float:
        return BlackScholes.gamma(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def vega(self) -> float:
        return BlackScholes.vega(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def vanna(self) -> float:
        return BlackScholes.vanna(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def volga(self) -> float:
        return BlackScholes.volga(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)


class Call(Option):
    """European Call option."""

    def bs_price(self) -> float:
        return BlackScholes.call_price(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def mc_price(self, num_simulations: int = 10_000, num_steps: int = 252) -> float:
        return MonteCarlo.call_price(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility, num_simulations, num_steps)

    def delta(self) -> float:
        return BlackScholes.delta_call(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def theta(self) -> float:
        return BlackScholes.theta_call(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def rho(self) -> float:
        return BlackScholes.rho_call(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)


class Put(Option):
    """European Put option."""

    def bs_price(self) -> float:
        return BlackScholes.put_price(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def mc_price(self, num_simulations: int = 10_000, num_steps: int = 252) -> float:
        return MonteCarlo.put_price(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility, num_simulations, num_steps)

    def delta(self) -> float:
        return BlackScholes.delta_put(self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility)

    def theta(self) -> float:
        S, K, T, r, sigma = self.spot_price, self.strike_price, self.expiration, self.risk_free_rate, self.volatility
        d1_val = self._d1()
        d2_val = self._d2()
        return (
            -S * norm.pdf(d1_val) * sigma / (2.0 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2_val)
        ) / 365.0

    def rho(self) -> float:
        d2_val = self._d2()
        return -self.strike_price * self.expiration * np.exp(-self.risk_free_rate * self.expiration) * norm.cdf(-d2_val) / 100.0
