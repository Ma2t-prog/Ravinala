"""
Ravinala by TSIVAHINY Matthias — Cross-Asset Pricing Engine
Black-Scholes, Greeks, and correlated multi-asset Monte Carlo.
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import fminbound
from typing import Callable, Dict, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


class BlackScholesGreeks:
    """
    Black-Scholes prices and full Greeks suite (Δ, Γ, ν, Θ, ρ, Vanna, Volga).
    Uses carry parameterization:  b=r (stock), b=r-q (dividend), b=r-rf (FX), b=0 (futures).
    """

    @staticmethod
    def d_values(
        S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> Tuple[float, float]:
        """Return (d1, d2). Returns (nan, nan) if T<=0 or sigma<=0."""
        if T <= 0 or sigma <= 0:
            return float("nan"), float("nan")
        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (b + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
        return d1, d1 - sigma * sqrt_T

    @classmethod
    def call_price(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        if T <= 0:
            return max(S - K, 0.0)
        d1, d2 = cls.d_values(S, K, T, r, b, sigma)
        fwd_factor = np.exp((b - r) * T)
        return S * fwd_factor * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    @classmethod
    def put_price(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        if T <= 0:
            return max(K - S, 0.0)
        d1, d2 = cls.d_values(S, K, T, r, b, sigma)
        fwd_factor = np.exp((b - r) * T)
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * fwd_factor * norm.cdf(-d1)

    @classmethod
    def delta(
        cls,
        S: float, K: float, T: float, r: float, b: float, sigma: float,
        option_type: str = "call",
    ) -> float:
        if T <= 0:
            return 1.0 if option_type == "call" else 0.0
        d1, _ = cls.d_values(S, K, T, r, b, sigma)
        fwd_factor = np.exp((b - r) * T)
        if option_type == "call":
            return fwd_factor * norm.cdf(d1)
        return fwd_factor * (norm.cdf(d1) - 1.0)

    @classmethod
    def gamma(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        if T <= 0 or sigma <= 0:
            return 0.0
        d1, _ = cls.d_values(S, K, T, r, b, sigma)
        return np.exp((b - r) * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

    @classmethod
    def vega(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        """Per 1% vol change."""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1, _ = cls.d_values(S, K, T, r, b, sigma)
        return S * np.exp((b - r) * T) * norm.pdf(d1) * np.sqrt(T) / 100.0

    @classmethod
    def theta(
        cls,
        S: float, K: float, T: float, r: float, b: float, sigma: float,
        option_type: str = "call",
    ) -> float:
        """Per calendar day."""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1, d2 = cls.d_values(S, K, T, r, b, sigma)
        fwd_factor = np.exp((b - r) * T)
        disc = np.exp(-r * T)
        decay = S * fwd_factor * norm.pdf(d1) * sigma / (2.0 * np.sqrt(T))
        if option_type == "call":
            return (-decay - b * S * fwd_factor * norm.cdf(d1) + r * K * disc * norm.cdf(d2)) / 365.0
        return (-decay + b * S * fwd_factor * norm.cdf(-d1) - r * K * disc * norm.cdf(-d2)) / 365.0

    @classmethod
    def rho(
        cls,
        S: float, K: float, T: float, r: float, b: float, sigma: float,
        option_type: str = "call",
    ) -> float:
        """Per 1% rate change."""
        if T <= 0 or sigma <= 0:
            return 0.0
        _, d2 = cls.d_values(S, K, T, r, b, sigma)
        disc = K * T * np.exp(-r * T) / 100.0
        if option_type == "call":
            return disc * norm.cdf(d2)
        return -disc * norm.cdf(-d2)

    @classmethod
    def vanna(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        """∂²C/∂S∂σ — cross-gamma between spot and vol."""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1, d2 = cls.d_values(S, K, T, r, b, sigma)
        return -np.exp((b - r) * T) * norm.pdf(d1) * d2 / sigma

    @classmethod
    def volga(
        cls, S: float, K: float, T: float, r: float, b: float, sigma: float
    ) -> float:
        """∂²C/∂σ² — vol-of-vol sensitivity."""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1, d2 = cls.d_values(S, K, T, r, b, sigma)
        return S * np.exp((b - r) * T) * norm.pdf(d1) * np.sqrt(T) * d1 * d2 / sigma


class MultiAssetPricer:
    """Monte Carlo engine for multi-asset pricing with Cholesky correlation."""

    def __init__(self, n_simulations: int = 10_000, random_seed: Optional[int] = None):
        self.n_sims = n_simulations
        self._rng = np.random.default_rng(random_seed)

    def simulate_paths(
        self,
        spots: np.ndarray,
        carries: np.ndarray,
        vols: np.ndarray,
        T: float,
        n_steps: int,
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Simulate correlated GBM paths via Cholesky decomposition.
        Returns array of shape (n_sims, n_steps+1, n_assets).
        """
        n_assets = len(spots)
        dt = T / n_steps

        if correlation_matrix is None:
            correlation_matrix = np.eye(n_assets)

        try:
            L = np.linalg.cholesky(correlation_matrix)
        except np.linalg.LinAlgError:
            L = np.eye(n_assets)

        # Precompute per-asset drift and diffusion scale
        drifts = (carries - 0.5 * vols**2) * dt          # (n_assets,)
        diff_scale = vols * np.sqrt(dt)                    # (n_assets,)

        paths = np.empty((self.n_sims, n_steps + 1, n_assets))
        paths[:, 0, :] = spots

        # Generate all increments at once: (n_steps, n_sims, n_assets)
        Z = self._rng.standard_normal((n_steps, self.n_sims, n_assets))
        Z_corr = Z @ L.T  # apply correlation

        log_increments = drifts + diff_scale * Z_corr  # broadcast over sims
        np.cumsum(log_increments, axis=0, out=log_increments)

        paths[:, 1:, :] = spots * np.exp(np.moveaxis(log_increments, 0, 1))
        return paths

    def payoff_distribution(
        self,
        payoff_func: Callable,
        spots: np.ndarray,
        carries: np.ndarray,
        vols: np.ndarray,
        T: float,
        r: float,
        n_steps: int = 252,
        correlation_matrix: Optional[np.ndarray] = None,
        **payoff_kwargs,
    ) -> Dict:
        """Price a derivative and return distribution statistics."""
        paths = self.simulate_paths(spots, carries, vols, T, n_steps, correlation_matrix)
        payoffs = np.array([payoff_func(s, **payoff_kwargs) for s in paths[:, -1, :]])
        pv = payoffs * np.exp(-r * T)
        return {
            "price": float(np.mean(pv)),
            "std_error": float(np.std(pv) / np.sqrt(self.n_sims)),
            "paths": paths,
            "payoffs": payoffs,
            "pv": pv,
            "mean_payoff": float(np.mean(payoffs)),
            "std_payoff": float(np.std(payoffs)),
            "percentile_5": float(np.percentile(pv, 5)),
            "percentile_95": float(np.percentile(pv, 95)),
        }


class ZeroCouponBond:
    """Zero-Coupon Bond pricing (funding leg of structured products)."""

    @staticmethod
    def price(notional: float, T: float, r: float, spread: float = 0.0) -> float:
        """ZCB = Notional / (1 + r + spread)^T"""
        if T <= 0:
            return notional
        return notional / (1.0 + r + spread) ** T

    @staticmethod
    def budget_for_option(notional: float, T: float, r: float, spread: float) -> float:
        """Available option premium budget = Notional − ZCB price."""
        return notional - ZeroCouponBond.price(notional, T, r, spread)


class CouponSolver:
    """Solve for the fair-value coupon given structured product constraints."""

    @staticmethod
    def solve_coupon(
        coupon_dates: np.ndarray,
        barrier_threshold: float,
        option_value_per_date: float,
        r: float,
        n_iters: int = 100,
    ) -> float:
        """
        Find maximum coupon such that PV(coupons) + option_value = 100.
        Uses bounded scalar minimization.
        """
        discount_factors = np.exp(-r * coupon_dates)

        def objective(coupon: float) -> float:
            pv_coupons = coupon * np.sum(discount_factors)
            return (pv_coupons + option_value_per_date - 100.0) ** 2

        return float(fminbound(objective, 0.0, 20.0, xtol=1e-4))
