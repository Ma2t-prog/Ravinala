"""
Heath-Jarrow-Morton (HJM) framework.

Instead of modeling a single short rate r(t), HJM models the ENTIRE
instantaneous forward rate curve f(t, T) for all maturities T.

The HJM no-arbitrage drift restriction:
    α(t,T) = σ(t,T) × ∫_t^T σ(t,u) du

Under the risk-neutral measure, the drift of the forward rate is FULLY
determined by the volatility structure — you can't choose both freely.

Special cases:
- Ho-Lee: σ(t,T) = σ (constant) → α(t,T) = σ²(T-t)
- Hull-White: σ(t,T) = σ e^{-κ(T-t)} → reduces to Hull-White short rate model

Reference: Heath, Jarrow, Morton (1992)
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional


class HJMFramework:
    """
    General HJM forward rate simulation.

    The forward rate evolves as:
    df(t,T) = α(t,T) dt + σ(t,T) dW(t)

    where α(t,T) = σ(t,T) × ∫_t^T σ(t,u) du  (HJM drift restriction)
    """

    def __init__(
        self,
        sigma_fn: Optional[Callable] = None,
        seed: int = 42,
    ):
        """
        Args:
            sigma_fn: callable(t, T) → volatility of f(t,T).
                      Default: Ho-Lee constant volatility (σ=0.01)
        """
        self.sigma_fn = sigma_fn or (lambda t, T: 0.01)
        self.rng = np.random.default_rng(seed)

    def _hjm_drift(self, t: float, T: float, n_quad: int = 50) -> float:
        """
        HJM no-arbitrage drift: α(t,T) = σ(t,T) × ∫_t^T σ(t,u) du

        Uses numerical integration (trapezoid rule).
        """
        u_grid = np.linspace(t, T, n_quad)
        integrand = np.array([self.sigma_fn(t, u) for u in u_grid])
        integral = np.trapezoid(integrand, u_grid)
        return float(self.sigma_fn(t, T) * integral)

    def simulate(
        self,
        initial_forward_curve: Callable,
        maturities: np.ndarray,
        T_sim: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> dict:
        """
        Simulate HJM forward rate paths.

        Args:
            initial_forward_curve: callable(T) → initial forward rate f(0,T)
            maturities: array of maturities to simulate (e.g. [0.25, 0.5, 1, 2, 5, 10])
            T_sim: simulation horizon
            n_steps: number of time steps
            n_paths: number of Monte Carlo paths

        Returns:
            {
                'forward_rates': np.ndarray of shape (n_steps+1, n_maturities, n_paths),
                'bond_prices': np.ndarray of shape (n_steps+1, n_maturities, n_paths),
                'short_rates': np.ndarray of shape (n_steps+1, n_paths),
                'time_grid': np.ndarray,
                'maturities': np.ndarray,
            }
        """
        dt = T_sim / n_steps
        sqrt_dt = np.sqrt(dt)
        t_grid = np.linspace(0, T_sim, n_steps + 1)
        M = len(maturities)

        # Initialize forward rate array: f[step, maturity_idx, path]
        f = np.zeros((n_steps + 1, M, n_paths))
        for j, T in enumerate(maturities):
            f[0, j, :] = float(initial_forward_curve(T))

        for k in range(n_steps):
            t_k = t_grid[k]
            dW = self.rng.standard_normal(n_paths) * sqrt_dt  # single Brownian increment

            for j, T in enumerate(maturities):
                if T <= t_k:
                    f[k + 1, j, :] = f[k, j, :]
                    continue
                alpha = self._hjm_drift(t_k, T)
                sigma = self.sigma_fn(t_k, T)
                f[k + 1, j, :] = f[k, j, :] + alpha * dt + sigma * dW

        # Compute bond prices from forward rates: P(t,T) = exp(-∫_t^T f(t,u) du)
        bond_prices = np.zeros_like(f)
        for k in range(n_steps + 1):
            t_k = t_grid[k]
            for j, T in enumerate(maturities):
                if T <= t_k:
                    bond_prices[k, j, :] = 1.0
                else:
                    # Integrate forward rates from t_k to T using trapezoidal rule
                    valid = maturities >= t_k
                    valid_m = maturities[valid]
                    valid_f = f[k, valid, :]
                    if len(valid_m) < 2:
                        bond_prices[k, j, :] = 1.0
                    else:
                        # Integrate from t_k to T
                        idx_T = np.searchsorted(valid_m, T)
                        m_seg = valid_m[:idx_T + 1] if idx_T < len(valid_m) else valid_m
                        f_seg = valid_f[:idx_T + 1] if idx_T < len(valid_f) else valid_f
                        if len(m_seg) >= 2:
                            integral = np.trapezoid(f_seg, m_seg, axis=0)
                            bond_prices[k, j, :] = np.exp(-integral)
                        else:
                            bond_prices[k, j, :] = 1.0

        # Short rate = f(t, t) ≈ forward rate at the shortest maturity
        short_rates = f[:, 0, :]  # approximate by shortest maturity forward rate

        return {
            "forward_rates": f,
            "bond_prices": bond_prices,
            "short_rates": short_rates,
            "time_grid": t_grid,
            "maturities": maturities,
        }

    @staticmethod
    def ho_lee(sigma: float = 0.01) -> "HJMFramework":
        """
        Ho-Lee model as special case of HJM.

        σ(t,T) = σ (constant)
        α(t,T) = σ²(T-t)  (HJM drift)

        The simplest HJM model — normal rates, flat vol term structure.
        """
        return HJMFramework(sigma_fn=lambda t, T: sigma)

    @staticmethod
    def exponential_decay(sigma: float = 0.01, kappa: float = 0.5) -> "HJMFramework":
        """
        Exponential decay vol — equivalent to Hull-White.

        σ(t,T) = σ × e^{-κ(T-t)}

        This is the Gaussian HJM that reduces to the Hull-White model.
        """
        return HJMFramework(sigma_fn=lambda t, T: sigma * np.exp(-kappa * (T - t)))

    def price_zcb(
        self,
        forward_rates_at_t: np.ndarray,
        maturities_at_t: np.ndarray,
        t: float,
        T: float,
    ) -> float:
        """
        Price a ZCB at time t maturing at T from the simulated forward curve.

        P(t,T) = exp(-∫_t^T f(t,u) du)
        """
        mask = maturities_at_t >= t
        m = maturities_at_t[mask]
        f = forward_rates_at_t[mask]
        mask2 = m <= T
        m = m[mask2]
        f = f[mask2]
        if len(m) < 2:
            return 1.0
        return float(np.exp(-np.trapezoid(f, m)))
