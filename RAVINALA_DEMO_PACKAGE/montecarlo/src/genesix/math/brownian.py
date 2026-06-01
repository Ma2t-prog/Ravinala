"""
Brownian motion and Geometric Brownian Motion.

This is the foundation of continuous-time finance. Every option pricing
model, every risk model, every simulation in GenesiX ultimately rests
on Brownian motion.

Mathematical background:
A standard Brownian motion (Wiener process) W(t) satisfies:
1. W(0) = 0
2. W(t) has independent increments
3. W(t) - W(s) ~ N(0, t-s) for t > s
4. W(t) is continuous in t (almost surely)

Geometric Brownian Motion (GBM):
dS = μS dt + σS dW
Solution (via Itô's lemma):
S(t) = S(0) × exp((μ - σ²/2)t + σW(t))

This is the model behind Black-Scholes. Its main flaw: it assumes
constant volatility and normally distributed log-returns.
Real markets have fat tails, volatility clustering, and jumps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


class BrownianMotion:
    """Standard Brownian motion simulation and analytics."""

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.default_rng(seed)

    def simulate_path(self, T: float, n_steps: int, n_paths: int = 1) -> np.ndarray:
        """
        Simulate standard Brownian motion paths.

        Args:
            T: total time horizon (in years, e.g. 1.0 = 1 year)
            n_steps: number of time steps
            n_paths: number of independent paths

        Returns:
            np.ndarray of shape (n_steps + 1, n_paths)
            First row is W(0) = 0 for all paths.

        Implementation:
            dt = T / n_steps
            dW ~ N(0, dt) for each step
            W(t_k) = W(t_{k-1}) + dW_k
        """
        dt = T / n_steps
        dW = self.rng.normal(0, np.sqrt(dt), size=(n_steps, n_paths))
        W = np.zeros((n_steps + 1, n_paths))
        W[1:] = np.cumsum(dW, axis=0)
        return W

    def simulate_correlated_paths(
        self,
        T: float,
        n_steps: int,
        n_assets: int,
        correlation_matrix: np.ndarray,
        n_paths: int = 1,
    ) -> np.ndarray:
        """
        Simulate correlated Brownian motions via Cholesky decomposition.

        For d assets with correlation matrix C:
        L = cholesky(C)
        Z = independent standard normals (d × n_steps × n_paths)
        dW = L @ Z × √dt

        This is used in multi-asset option pricing and portfolio simulation.

        Args:
            correlation_matrix: (n_assets × n_assets) positive definite

        Returns:
            np.ndarray of shape (n_steps + 1, n_assets, n_paths)
        """
        dt = T / n_steps
        L = np.linalg.cholesky(correlation_matrix)
        Z = self.rng.standard_normal((n_steps, n_assets, n_paths))
        dW = np.einsum("ij,kjl->kil", L, Z) * np.sqrt(dt)
        W = np.zeros((n_steps + 1, n_assets, n_paths))
        W[1:] = np.cumsum(dW, axis=0)
        return W

    def quadratic_variation(self, path: np.ndarray, T: float) -> float:
        """
        Compute quadratic variation [W]_T of a Brownian path.

        For true Brownian motion: [W]_T = T (almost surely).
        This is the KEY property that makes Itô calculus different
        from ordinary calculus: (dW)² = dt, not 0.

        Computed as: [W]_T = Σ (W(t_{k+1}) - W(t_k))²

        Returns: float (should be close to T for true Brownian motion)
        """
        increments = np.diff(path, axis=0)
        return float(np.sum(increments**2))

    def verify_properties(
        self, T: float = 1.0, n_steps: int = 10000, n_paths: int = 5000
    ) -> dict:
        """
        Statistical verification of Brownian motion properties.
        Useful for testing and educational demonstration.

        Returns:
            {
                'mean_WT': float,                          # should be ≈ 0
                'var_WT': float,                           # should be ≈ T
                'mean_quadratic_variation': float,         # should be ≈ T
                'increment_normality_pvalue': float,       # Jarque-Bera test
                'independent_increments_correlation': float,  # should be ≈ 0
            }
        """
        paths = self.simulate_path(T, n_steps, n_paths)
        WT = paths[-1, :]

        mean_WT = float(np.mean(WT))
        var_WT = float(np.var(WT))

        qvs = [
            self.quadratic_variation(paths[:, i : i + 1], T)
            for i in range(min(100, n_paths))
        ]
        mean_qv = float(np.mean(qvs))

        from scipy.stats import jarque_bera

        mid = n_steps // 2
        increment = paths[mid + 1, :] - paths[mid, :]
        _, jb_pval = jarque_bera(increment)

        inc1 = paths[n_steps // 3, :] - paths[0, :]
        inc2 = paths[-1, :] - paths[2 * n_steps // 3, :]
        corr = float(np.corrcoef(inc1, inc2)[0, 1])

        return {
            "mean_WT": mean_WT,
            "var_WT": var_WT,
            "expected_var": T,
            "mean_quadratic_variation": mean_qv,
            "expected_qv": T,
            "increment_normality_pvalue": float(jb_pval),
            "independent_increments_correlation": corr,
        }


class GeometricBrownianMotion:
    """
    Geometric Brownian Motion — the standard asset price model.

    SDE: dS = μS dt + σS dW

    Solution (via Itô's lemma applied to log(S)):
    S(t) = S(0) × exp((μ - σ²/2)t + σW(t))

    The -σ²/2 term is the Itô correction — it arises because
    Itô's lemma has a second-order term that doesn't vanish
    (unlike in ordinary calculus, because (dW)² = dt ≠ 0).

    Properties of GBM:
    - S(t) > 0 always (prices can't go negative)
    - log(S(t)) ~ N(log(S(0)) + (μ-σ²/2)t, σ²t)
    - E[S(t)] = S(0) × exp(μt)
    - Var[S(t)] = S(0)² × exp(2μt) × (exp(σ²t) - 1)
    """

    def __init__(self, seed: Optional[int] = 42):
        self.bm = BrownianMotion(seed)

    def simulate(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> np.ndarray:
        """
        Simulate GBM paths using exact solution (not Euler discretization).

        Args:
            S0: initial price
            mu: drift (annualized), e.g. 0.10 = 10% expected return
            sigma: volatility (annualized), e.g. 0.20 = 20% vol
            T: time horizon in years
            n_steps: number of time steps
            n_paths: number of independent paths

        Returns:
            np.ndarray of shape (n_steps + 1, n_paths)
            First row is S(0) = S0 for all paths.

        Implementation:
            S(t_k) = S0 × exp((μ - σ²/2)×t_k + σ×W(t_k))
        """
        W = self.bm.simulate_path(T, n_steps, n_paths)
        t = np.linspace(0, T, n_steps + 1).reshape(-1, 1)
        S = S0 * np.exp((mu - 0.5 * sigma**2) * t + sigma * W)
        return S

    def simulate_multi_asset(
        self,
        S0: np.ndarray,
        mu: np.ndarray,
        sigma: np.ndarray,
        correlation: np.ndarray,
        T: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> np.ndarray:
        """
        Simulate correlated multi-asset GBM.

        Used for basket options, portfolio simulation, multi-asset stress tests.

        Args:
            S0: (n_assets,) initial prices
            mu: (n_assets,) drifts
            sigma: (n_assets,) volatilities
            correlation: (n_assets × n_assets) correlation matrix

        Returns:
            np.ndarray of shape (n_steps + 1, n_assets, n_paths)
        """
        n_assets = len(S0)
        W = self.bm.simulate_correlated_paths(T, n_steps, n_assets, correlation, n_paths)
        t = np.linspace(0, T, n_steps + 1).reshape(-1, 1, 1)

        S0_arr = np.array(S0).reshape(1, -1, 1)
        mu_arr = np.array(mu).reshape(1, -1, 1)
        sigma_arr = np.array(sigma).reshape(1, -1, 1)

        S = S0_arr * np.exp((mu_arr - 0.5 * sigma_arr**2) * t + sigma_arr * W)
        return S

    def analytical_moments(
        self, S0: float, mu: float, sigma: float, T: float
    ) -> dict:
        """
        Exact analytical moments of GBM.

        Returns:
            {
                'expected_price': S0 × exp(μT),
                'variance': S0² × exp(2μT) × (exp(σ²T) - 1),
                'std': sqrt(variance),
                'median_price': S0 × exp((μ - σ²/2)T),
                'mode_price': S0 × exp((μ - 3σ²/2)T),
                'log_return_mean': (μ - σ²/2)T,
                'log_return_std': σ√T,
            }
        """
        return {
            "expected_price": S0 * np.exp(mu * T),
            "variance": S0**2 * np.exp(2 * mu * T) * (np.exp(sigma**2 * T) - 1),
            "std": S0 * np.exp(mu * T) * np.sqrt(np.exp(sigma**2 * T) - 1),
            "median_price": S0 * np.exp((mu - 0.5 * sigma**2) * T),
            "mode_price": S0 * np.exp((mu - 1.5 * sigma**2) * T),
            "log_return_mean": (mu - 0.5 * sigma**2) * T,
            "log_return_std": sigma * np.sqrt(T),
        }

    def verify_against_analytical(
        self,
        S0: float = 100,
        mu: float = 0.10,
        sigma: float = 0.20,
        T: float = 1.0,
        n_paths: int = 50000,
    ) -> dict:
        """
        Verify simulation against analytical solution.

        Returns dict comparing simulated vs analytical moments.
        Used for testing and educational demonstration.
        """
        paths = self.simulate(S0, mu, sigma, T, n_steps=252, n_paths=n_paths)
        ST = paths[-1, :]

        analytical = self.analytical_moments(S0, mu, sigma, T)

        return {
            "analytical_mean": analytical["expected_price"],
            "simulated_mean": float(np.mean(ST)),
            "analytical_std": analytical["std"],
            "simulated_std": float(np.std(ST)),
            "analytical_median": analytical["median_price"],
            "simulated_median": float(np.median(ST)),
            "mean_error_pct": abs(np.mean(ST) - analytical["expected_price"])
            / analytical["expected_price"]
            * 100,
        }
