"""
Stochastic Differential Equation solvers.

Numerical methods for simulating SDEs that don't have closed-form solutions.

Three methods implemented:
1. Euler-Maruyama: simplest, O(√dt) strong convergence
2. Milstein: adds correction term, O(dt) strong convergence
3. Exact simulation: for specific models with known transition densities

Models implemented:
- GBM (has exact solution — used as validation benchmark)
- Ornstein-Uhlenbeck (mean-reverting — interest rates, vol)
- CIR / Cox-Ingersoll-Ross (mean-reverting, non-negative — rates, vol)
- Heston stochastic volatility (2-factor: price + vol)
- Merton jump-diffusion (GBM + Poisson jumps)
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional, Tuple


class SDESolver:
    """Generic SDE solver with multiple numerical schemes."""

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.default_rng(seed)

    def euler_maruyama(
        self,
        drift_fn: Callable,
        diffusion_fn: Callable,
        X0: float,
        T: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> np.ndarray:
        """
        Euler-Maruyama scheme for dX = a(X,t) dt + b(X,t) dW.

        X_{k+1} = X_k + a(X_k, t_k) Δt + b(X_k, t_k) ΔW_k

        Args:
            drift_fn: callable(X, t) → drift coefficient a(X, t)
            diffusion_fn: callable(X, t) → diffusion coefficient b(X, t)
            X0: initial value
            T: time horizon
            n_steps: number of time steps
            n_paths: number of Monte Carlo paths

        Returns:
            np.ndarray of shape (n_steps + 1, n_paths)

        Convergence: O(√Δt) strong, O(Δt) weak.
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        X = np.zeros((n_steps + 1, n_paths))
        X[0] = X0
        t_grid = np.linspace(0, T, n_steps + 1)

        for k in range(n_steps):
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            X[k + 1] = X[k] + drift_fn(X[k], t_grid[k]) * dt + diffusion_fn(X[k], t_grid[k]) * dW

        return X

    def milstein(
        self,
        drift_fn: Callable,
        diffusion_fn: Callable,
        diffusion_deriv_fn: Callable,
        X0: float,
        T: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> np.ndarray:
        """
        Milstein scheme — adds b(X)×b'(X)×(ΔW² - Δt)/2 correction.

        X_{k+1} = X_k + a(X_k,t_k)Δt + b(X_k,t_k)ΔW_k
                  + ½ b(X_k,t_k) b'(X_k,t_k) (ΔW_k² - Δt)

        Args:
            diffusion_deriv_fn: callable(X, t) → db/dX

        Convergence: O(Δt) strong, O(Δt) weak.
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        X = np.zeros((n_steps + 1, n_paths))
        X[0] = X0
        t_grid = np.linspace(0, T, n_steps + 1)

        for k in range(n_steps):
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            b = diffusion_fn(X[k], t_grid[k])
            b_prime = diffusion_deriv_fn(X[k], t_grid[k])
            X[k + 1] = (
                X[k]
                + drift_fn(X[k], t_grid[k]) * dt
                + b * dW
                + 0.5 * b * b_prime * (dW**2 - dt)
            )

        return X


class OrnsteinUhlenbeck:
    """
    Ornstein-Uhlenbeck process — mean-reverting stochastic process.

    dX = κ(θ - X) dt + σ dW

    κ = speed of mean reversion (higher = faster reversion)
    θ = long-term mean (equilibrium level)
    σ = volatility of the process

    Exact transition density:
    X(t) | X(s) ~ N(θ + (X(s)-θ)e^{-κ(t-s)}, σ²/(2κ)(1-e^{-2κ(t-s)}))

    Used for: interest rate modeling (Vasicek), pairs trading (spread dynamics),
    mean-reverting volatility, commodity prices.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.default_rng(seed)

    def simulate_exact(
        self,
        X0: float,
        kappa: float,
        theta: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int = 1,
    ) -> np.ndarray:
        """Simulate using exact transition density (no discretization error)."""
        dt = T / n_steps
        X = np.zeros((n_steps + 1, n_paths))
        X[0] = X0

        exp_k = np.exp(-kappa * dt)
        var_step = sigma**2 / (2 * kappa) * (1 - np.exp(-2 * kappa * dt))
        std_step = np.sqrt(var_step)

        for k in range(n_steps):
            mean_k = theta + (X[k] - theta) * exp_k
            X[k + 1] = mean_k + std_step * self.rng.standard_normal(n_paths)

        return X

    def expected_value(self, X0: float, kappa: float, theta: float, T: float) -> float:
        """E[X(T)] = θ + (X0 - θ)×exp(-κT)"""
        return theta + (X0 - theta) * np.exp(-kappa * T)

    def variance(self, kappa: float, sigma: float, T: float) -> float:
        """Var[X(T)] = σ²/(2κ) × (1 - exp(-2κT))"""
        return sigma**2 / (2 * kappa) * (1 - np.exp(-2 * kappa * T))

    def half_life(self, kappa: float) -> float:
        """Time to revert halfway to mean: t_{1/2} = ln(2)/κ"""
        return np.log(2) / kappa

    def stationary_distribution(self, kappa: float, theta: float, sigma: float) -> dict:
        """Long-run distribution: N(θ, σ²/(2κ))"""
        return {
            "mean": theta,
            "variance": sigma**2 / (2 * kappa),
            "std": sigma / np.sqrt(2 * kappa),
        }


class CIRProcess:
    """
    Cox-Ingersoll-Ross process — mean-reverting AND non-negative.

    dX = κ(θ - X) dt + σ√X dW

    The √X in the diffusion ensures X ≥ 0 (if 2κθ ≥ σ², the Feller condition).

    Used for: interest rates (CIR model), stochastic variance (Heston model).
    Transition density: non-central chi-squared distribution.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.default_rng(seed)

    def simulate(
        self,
        X0: float,
        kappa: float,
        theta: float,
        sigma: float,
        T: float,
        n_steps: int,
        n_paths: int = 1,
        scheme: str = "milstein",
    ) -> np.ndarray:
        """
        Simulate CIR paths.

        CRITICAL: Euler-Maruyama can produce negative values.
        Uses Milstein with full truncation by default.
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        X = np.zeros((n_steps + 1, n_paths))
        X[0] = X0

        for k in range(n_steps):
            X_pos = np.maximum(X[k], 0.0)
            sqrt_X = np.sqrt(X_pos)
            dW = self.rng.standard_normal(n_paths) * sqrt_dt

            if scheme == "milstein":
                # Milstein: b = σ√X, b' = σ/(2√X)
                X[k + 1] = (
                    X[k]
                    + kappa * (theta - X_pos) * dt
                    + sigma * sqrt_X * dW
                    + 0.25 * sigma**2 * (dW**2 - dt)
                )
            else:  # euler
                X[k + 1] = (
                    X[k]
                    + kappa * (theta - X_pos) * dt
                    + sigma * sqrt_X * dW
                )

            # Full truncation to keep non-negative
            X[k + 1] = np.maximum(X[k + 1], 0.0)

        return X

    def feller_condition_satisfied(self, kappa: float, theta: float, sigma: float) -> bool:
        """Check 2κθ ≥ σ². If not, process can hit zero."""
        return 2 * kappa * theta >= sigma**2


class HestonModel:
    """
    Heston stochastic volatility model — 2-factor model.

    dS = μS dt + √v S dW₁
    dv = κ(θ - v) dt + ξ√v dW₂
    dW₁ dW₂ = ρ dt

    Parameters:
    S  = asset price (GBM with stochastic vol)
    v  = instantaneous variance (CIR process)
    κ  = mean-reversion speed of variance
    θ  = long-term variance level
    ξ  = volatility of volatility ("vol of vol")
    ρ  = correlation between price and vol (typically ρ < 0: "leverage effect")

    ρ < 0 means: when price drops, volatility rises.
    This is why implied volatility smiles are skewed for equities.
    """

    def __init__(
        self,
        S0: float,
        v0: float,
        mu: float,
        kappa: float,
        theta: float,
        xi: float,
        rho: float,
        seed: int = 42,
    ):
        self.S0 = S0
        self.v0 = v0
        self.mu = mu
        self.kappa = kappa
        self.theta = theta
        self.xi = xi
        self.rho = rho
        self.rng = np.random.default_rng(seed)

    def simulate(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate Heston paths using Euler-Milstein with full truncation.

        Returns:
            (S_paths, v_paths): tuple of arrays, each (n_steps+1, n_paths)
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)

        S = np.zeros((n_steps + 1, n_paths))
        v = np.zeros((n_steps + 1, n_paths))
        S[0] = self.S0
        v[0] = self.v0

        # Cholesky: W1 = Z1, W2 = ρZ1 + √(1-ρ²)Z2
        sqrt_1_rho2 = np.sqrt(1 - self.rho**2)

        for k in range(n_steps):
            Z1 = self.rng.standard_normal(n_paths)
            Z2 = self.rng.standard_normal(n_paths)
            dW1 = Z1 * sqrt_dt
            dW2 = (self.rho * Z1 + sqrt_1_rho2 * Z2) * sqrt_dt

            v_pos = np.maximum(v[k], 0.0)
            sqrt_v = np.sqrt(v_pos)

            # Variance process (CIR — Milstein with full truncation)
            v[k + 1] = np.maximum(
                v[k]
                + self.kappa * (self.theta - v_pos) * dt
                + self.xi * sqrt_v * dW2
                + 0.25 * self.xi**2 * (dW2**2 - dt),
                0.0,
            )

            # Price process (log-Euler for positivity)
            S[k + 1] = S[k] * np.exp(
                (self.mu - 0.5 * v_pos) * dt + sqrt_v * dW1
            )

        return S, v

    def characteristic_function(self, u: complex, T: float) -> complex:
        """
        Heston characteristic function φ(u) = E[exp(iu × log(S(T)/S(0)))].

        Heston (1993) closed-form expression.
        Used for semi-analytical European option pricing via Fourier inversion.
        """
        S0, v0 = self.S0, self.v0
        kappa, theta, xi, rho, mu = self.kappa, self.theta, self.xi, self.rho, self.mu

        # Heston (1993) formulation
        alpha = -0.5 * (u**2 + 1j * u)
        beta = kappa - rho * xi * 1j * u
        gamma = 0.5 * xi**2

        discriminant = np.sqrt(beta**2 - 4 * alpha * gamma)
        r_plus = (beta + discriminant) / (xi**2)
        r_minus = (beta - discriminant) / (xi**2)

        g = r_minus / r_plus
        exp_disc = np.exp(-discriminant * T)

        D = r_minus * (1 - exp_disc) / (1 - g * exp_disc)
        C = kappa * (r_minus * T - 2 / xi**2 * np.log((1 - g * exp_disc) / (1 - g)))

        return np.exp(C * theta + D * v0 + 1j * u * np.log(S0 * np.exp(mu * T)))

    def european_call_price(self, K: float, T: float, r: float) -> float:
        """
        Semi-analytical European call price via Fourier inversion (Carr-Madan).

        C = exp(-rT) / π × ∫₀^∞ Re[exp(-iu ln K) × φ(u - iα)] / (α² + α - u² + iu(2α+1)) du
        """
        from scipy.integrate import quad

        alpha = 1.5  # damping parameter

        def integrand(u: float) -> float:
            phi = self.characteristic_function(u - 1j * (alpha + 1), T)
            numerator = np.exp(-r * T) * phi
            denominator = alpha**2 + alpha - u**2 + 1j * u * (2 * alpha + 1)
            psi = numerator / denominator
            return np.real(np.exp(-1j * u * np.log(K)) * psi)

        result, _ = quad(integrand, 0, 500, limit=200, epsabs=1e-6)
        return np.exp(-alpha * np.log(K)) / np.pi * result

    def implied_vol_smile(self, strikes: np.ndarray, T: float, r: float) -> dict:
        """
        Compute implied volatility for each strike via Black-Scholes inversion.

        Returns: dict with strikes and implied vols.
        """
        from scipy.optimize import brentq
        from scipy.stats import norm

        def bs_call(S, K, T, r, sigma):
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

        ivs = []
        for K in strikes:
            try:
                price = self.european_call_price(K, T, r)
                intrinsic = max(self.S0 * np.exp((self.mu - r) * T) - K * np.exp(-r * T), 0)
                if price <= intrinsic + 1e-8:
                    ivs.append(np.nan)
                    continue
                iv = brentq(lambda sig: bs_call(self.S0, K, T, r, sig) - price, 1e-4, 10.0)
                ivs.append(iv)
            except Exception:
                ivs.append(np.nan)

        return {"strikes": list(strikes), "implied_vols": ivs}


class MertonJumpDiffusion:
    """
    Merton (1976) jump-diffusion model.

    dS/S = (μ - λk̄) dt + σ dW + J dN

    Where:
    - N is a Poisson process with intensity λ (jumps/year)
    - J ~ N(μ_J, σ_J²) is the log-jump size
    - k̄ = E[e^J - 1] = exp(μ_J + σ_J²/2) - 1 (compensator)

    Real markets have jumps. GBM doesn't. This is why GBM underprices
    out-of-the-money options — the tails are too thin.
    """

    def __init__(
        self,
        S0: float,
        mu: float,
        sigma: float,
        lam: float,
        mu_J: float,
        sigma_J: float,
        seed: int = 42,
    ):
        self.S0 = S0
        self.mu = mu
        self.sigma = sigma
        self.lam = lam          # jump intensity (jumps/year)
        self.mu_J = mu_J        # mean log-jump size
        self.sigma_J = sigma_J  # std of log-jump size
        self.kbar = np.exp(mu_J + 0.5 * sigma_J**2) - 1  # compensator
        self.rng = np.random.default_rng(seed)

    def simulate(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """
        Simulate Merton jump-diffusion paths.

        For each time step:
        1. Diffusion: exp((μ - λk̄ - σ²/2)dt + σ dW)
        2. Jumps: exp(Σ J_i) for N ~ Poisson(λdt) jumps
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        drift_adj = (self.mu - self.lam * self.kbar - 0.5 * self.sigma**2) * dt

        S = np.zeros((n_steps + 1, n_paths))
        S[0] = self.S0

        for k in range(n_steps):
            # Diffusion component
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            diffusion = np.exp(drift_adj + self.sigma * dW)

            # Jump component
            n_jumps = self.rng.poisson(self.lam * dt, size=n_paths)
            jump_factor = np.ones(n_paths)

            for path in range(n_paths):
                if n_jumps[path] > 0:
                    jump_sizes = self.rng.normal(self.mu_J, self.sigma_J, size=n_jumps[path])
                    jump_factor[path] = np.exp(np.sum(jump_sizes))

            S[k + 1] = S[k] * diffusion * jump_factor

        return S

    def european_call_price(self, K: float, T: float, r: float) -> float:
        """
        Merton's analytical formula for European call.

        C = Σ_{n=0}^{N_max} [exp(-λ'T)(λ'T)^n / n!] × BS(S0, K, T, r_n, σ_n)

        where λ' = λ(1 + k̄), r_n and σ_n are adjusted for n jumps.
        Truncate at N_max ≈ 20.
        """
        from scipy.stats import norm
        from math import factorial

        def bs_call(S, K, T, r, sigma):
            if sigma <= 0 or T <= 0:
                return max(S - K * np.exp(-r * T), 0.0)
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

        lam_prime = self.lam * (1 + self.kbar)
        N_max = 20
        price = 0.0

        for n in range(N_max + 1):
            poisson_weight = np.exp(-lam_prime * T) * (lam_prime * T)**n / factorial(n)
            r_n = r - self.lam * self.kbar + n * self.mu_J / T
            sigma_n = np.sqrt(self.sigma**2 + n * self.sigma_J**2 / T)
            price += poisson_weight * bs_call(self.S0, K, T, r_n, sigma_n)

        return price
