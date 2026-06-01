"""
Lévy processes and jump-diffusion models.

A Lévy process generalises Brownian motion by allowing jumps.
Formally, L(t) is a Lévy process if:
1. L(0) = 0
2. Independent and stationary increments
3. Stochastically continuous (no fixed discontinuities)

The Lévy-Khintchine theorem characterises the characteristic function:
E[exp(iuL(t))] = exp(t × ψ(u))
where ψ(u) = iαu - ½σ²u² + ∫(e^{iux} - 1 - iux·1_{|x|<1}) ν(dx)

Models implemented:
- Kou double-exponential jump-diffusion (asymmetric jumps)
- Variance Gamma (VG) — infinite activity, no diffusion component
- Normal Inverse Gaussian (NIG) — flexible skew and kurtosis

Reference: Kou (2002), Madan, Carr & Chang (1998), Barndorff-Nielsen (1997)
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Tuple
from scipy.stats import norm
from math import factorial


class KouDoubleExponential:
    """
    Kou (2002) double-exponential jump-diffusion model.

    dS/S = (r - λk̄) dt + σ dW + J dN

    Jump sizes follow a double-exponential (asymmetric Laplace) distribution:
    - With probability p:  J ~ Exp(η₊)   (positive jump, mean 1/η₊)
    - With probability 1-p: -J ~ Exp(η₋)  (negative jump, mean 1/η₋)

    k̄ = E[e^J - 1] = p·η₊/(η₊-1) + (1-p)·η₋/(η₋+1) - 1

    Advantages over Merton:
    - Asymmetric jumps: capture the observed crash/rally asymmetry
    - Analytical formula for European/barrier options
    - Better fit to observed volatility smile for equities (steep put skew)
    """

    def __init__(
        self,
        S0: float,
        mu: float,
        sigma: float,
        lam: float,
        p: float,
        eta_pos: float,
        eta_neg: float,
        seed: int = 42,
    ):
        """
        Args:
            S0: initial price
            mu: drift
            sigma: diffusion volatility
            lam: jump intensity (jumps/year)
            p: probability of upward jump
            eta_pos: rate of upward exponential (mean upward jump = 1/eta_pos)
            eta_neg: rate of downward exponential (mean downward jump = 1/eta_neg)
        """
        assert eta_pos > 1, "eta_pos must be > 1 for finite mean"
        assert eta_neg > 0, "eta_neg must be > 0"
        assert 0 <= p <= 1, "p must be in [0,1]"

        self.S0 = S0
        self.mu = mu
        self.sigma = sigma
        self.lam = lam
        self.p = p
        self.eta_pos = eta_pos
        self.eta_neg = eta_neg
        self.rng = np.random.default_rng(seed)

        # Compensator k̄ = E[e^J - 1]
        self.kbar = (
            p * eta_pos / (eta_pos - 1)
            + (1 - p) * eta_neg / (eta_neg + 1)
            - 1
        )

    def _sample_jump(self, n: int) -> np.ndarray:
        """Sample n jump sizes from the double-exponential distribution."""
        is_up = self.rng.random(n) < self.p
        up_jumps = self.rng.exponential(1 / self.eta_pos, size=n)
        down_jumps = -self.rng.exponential(1 / self.eta_neg, size=n)
        return np.where(is_up, up_jumps, down_jumps)

    def simulate(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """
        Simulate Kou double-exponential jump-diffusion paths.

        Returns:
            np.ndarray of shape (n_steps + 1, n_paths)
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        drift_adj = (self.mu - self.lam * self.kbar - 0.5 * self.sigma**2) * dt

        S = np.zeros((n_steps + 1, n_paths))
        S[0] = self.S0

        for k in range(n_steps):
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            diffusion = np.exp(drift_adj + self.sigma * dW)

            n_jumps = self.rng.poisson(self.lam * dt, size=n_paths)
            jump_factor = np.ones(n_paths)
            for i in range(n_paths):
                if n_jumps[i] > 0:
                    jumps = self._sample_jump(n_jumps[i])
                    jump_factor[i] = np.exp(np.sum(jumps))

            S[k + 1] = S[k] * diffusion * jump_factor

        return S

    def european_call_price_mc(
        self, K: float, T: float, r: float, n_paths: int = 100_000
    ) -> dict:
        """Monte Carlo European call price under Kou model."""
        paths = self.simulate(T, n_steps=252, n_paths=n_paths)
        ST = paths[-1, :]
        payoffs = np.maximum(ST - K, 0)
        price = float(np.exp(-r * T) * np.mean(payoffs))
        stderr = float(np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths))
        return {"price": price, "stderr": stderr}

    def tail_probability(self, x: float) -> dict:
        """
        P(J > x) and P(J < -x) for x > 0.
        Compares to a Gaussian with same variance to show fat tails.
        """
        var_jump = (
            self.p * (2 / self.eta_pos**2)
            + (1 - self.p) * (2 / self.eta_neg**2)
        )
        mean_jump = self.p / self.eta_pos - (1 - self.p) / self.eta_neg

        p_right = self.p * np.exp(-self.eta_pos * x)
        p_left = (1 - self.p) * np.exp(-self.eta_neg * x)
        p_gaussian = 2 * norm.sf(x / np.sqrt(var_jump))

        return {
            "P(J > x)": float(p_right),
            "P(J < -x)": float(p_left),
            "total_tail_prob": float(p_right + p_left),
            "gaussian_tail_prob": float(p_gaussian),
            "fat_tail_ratio": float((p_right + p_left) / p_gaussian),
            "interpretation": (
                f"At x={x:.2f} the double-exponential tail is "
                f"{(p_right + p_left) / p_gaussian:.1f}x heavier than Gaussian. "
                "This is why OTM options are underpriced by Black-Scholes."
            ),
        }


class VarianceGamma:
    """
    Variance Gamma (VG) process — Madan, Carr & Chang (1998).

    X_VG(t) = θ·G(t) + σ·W(G(t))

    where G(t) ~ Gamma(t/ν, ν) is a random time change (Gamma process).

    VG has:
    - Infinite activity (infinitely many small jumps)
    - No Gaussian diffusion component
    - Finite variation (smoother paths than Brownian motion)
    - Controllable skewness (via θ) and kurtosis (via ν)

    Parameters:
    σ  = volatility of the Brownian component (σ > 0)
    ν  = variance of the Gamma process (ν > 0) — controls kurtosis
    θ  = drift of the Brownian component — controls skewness

    For equities: θ < 0 (negative skew, crash risk)
    """

    def __init__(
        self,
        S0: float,
        r: float,
        sigma: float,
        nu: float,
        theta: float,
        seed: int = 42,
    ):
        self.S0 = S0
        self.r = r
        self.sigma = sigma
        self.nu = nu
        self.theta = theta
        self.rng = np.random.default_rng(seed)

        # Risk-neutral drift correction
        # ω = (1/ν) × log(1 - θ·ν - ½σ²ν)
        self.omega = (1 / nu) * np.log(1 - theta * nu - 0.5 * sigma**2 * nu)

    def simulate(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """
        Simulate VG stock price paths.

        Method:
        1. Simulate Gamma subordinator G(t): increments ~ Gamma(dt/ν, ν)
        2. Evaluate Brownian motion at G(t): W(G(t))
        3. X_VG(t) = θG(t) + σW(G(t))
        4. S(t) = S0 × exp((r + ω)t + X_VG(t))
        """
        dt = T / n_steps
        t_grid = np.linspace(0, T, n_steps + 1)

        S = np.zeros((n_steps + 1, n_paths))
        S[0] = self.S0

        # Gamma increments: shape = dt/ν, scale = ν
        dG = self.rng.gamma(dt / self.nu, self.nu, size=(n_steps, n_paths))

        # Brownian increments evaluated at Gamma times
        Z = self.rng.standard_normal((n_steps, n_paths))
        dX = self.theta * dG + self.sigma * np.sqrt(dG) * Z

        # Cumulative VG path
        X_vg = np.zeros((n_steps + 1, n_paths))
        X_vg[1:] = np.cumsum(dX, axis=0)

        for i in range(1, n_steps + 1):
            S[i] = self.S0 * np.exp(
                (self.r + self.omega) * t_grid[i] + X_vg[i]
            )

        return S

    def cumulants(self, T: float) -> dict:
        """
        Analytical cumulants of X_VG(T).

        Mean:   θT
        Var:    (σ² + νθ²)T
        Skew:   θ·ν·(3σ² + 2νθ²) / (σ² + νθ²)^{3/2} × T^{-1/2}
        Kurt:   3 + 3ν(σ⁴ + 4σ²νθ² + 2ν²θ⁴) / (σ² + νθ²)² / T
        """
        var = (self.sigma**2 + self.nu * self.theta**2) * T
        skew = (
            self.theta
            * self.nu
            * (3 * self.sigma**2 + 2 * self.nu * self.theta**2)
            / (self.sigma**2 + self.nu * self.theta**2) ** 1.5
            / np.sqrt(T)
        )
        kurt_excess = (
            3
            * self.nu
            * (
                self.sigma**4
                + 4 * self.sigma**2 * self.nu * self.theta**2
                + 2 * self.nu**2 * self.theta**4
            )
            / (self.sigma**2 + self.nu * self.theta**2) ** 2
            / T
        )

        return {
            "mean": float(self.theta * T),
            "variance": float(var),
            "skewness": float(skew),
            "excess_kurtosis": float(kurt_excess),
        }


class NormalInverseGaussian:
    """
    Normal Inverse Gaussian (NIG) process — Barndorff-Nielsen (1997).

    X_NIG(t) ~ NIG(α, β, δ·t, μ·t)

    where:
    α  = tail heaviness (larger α = lighter tails)
    β  = asymmetry (β < 0: negative skew, β > 0: positive skew)
    δ  = scale
    μ  = location

    NIG is a generalisation of the normal distribution that allows:
    - Arbitrary skewness and kurtosis (independently controlled)
    - Semi-heavy tails (heavier than Gaussian, lighter than Cauchy)
    - Good fit to financial return distributions

    Characteristic function:
    E[exp(iuX)] = exp(iμu - δ(√(α²-(β+iu)²) - √(α²-β²)))
    """

    def __init__(
        self,
        alpha: float,
        beta: float,
        delta: float,
        mu: float = 0.0,
        seed: int = 42,
    ):
        assert alpha > abs(beta), "Require α > |β| for valid NIG"
        self.alpha = alpha
        self.beta = beta
        self.delta = delta
        self.mu = mu
        self.rng = np.random.default_rng(seed)
        self.gamma = np.sqrt(alpha**2 - beta**2)

    def simulate_increments(self, dt: float, n: int) -> np.ndarray:
        """
        Simulate NIG increments over time step dt.

        Method: Normal Mean-Variance Mixture.
        1. Sample IG mixing variable: V ~ InvGaussian(δdt/γ, δ²dt²)
        2. Sample: X | V ~ N(μdt + βV, V)
        """
        # Inverse Gaussian samples
        mu_ig = self.delta * dt / self.gamma
        lam_ig = (self.delta * dt) ** 2
        V = self._sample_inverse_gaussian(mu_ig, lam_ig, n)

        # Normal conditional
        Z = self.rng.standard_normal(n)
        return self.mu * dt + self.beta * V + np.sqrt(V) * Z

    def _sample_inverse_gaussian(self, mu: float, lam: float, n: int) -> np.ndarray:
        """Sample from InvGaussian(mu, lam) using Michael et al. (1976) method."""
        v = self.rng.standard_normal(n)
        y = v**2
        x = mu + mu**2 * y / (2 * lam) - mu / (2 * lam) * np.sqrt(4 * mu * lam * y + mu**2 * y**2)
        u = self.rng.random(n)
        return np.where(u <= mu / (mu + x), x, mu**2 / x)

    def simulate(
        self, S0: float, r: float, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """Simulate stock price paths under NIG dynamics."""
        dt = T / n_steps
        # Risk-neutral correction: ω such that E[e^X] = 1
        omega = self.delta * (self.gamma - np.sqrt(self.alpha**2 - (self.beta + 1) ** 2))

        S = np.zeros((n_steps + 1, n_paths))
        S[0] = S0
        X = np.zeros(n_paths)

        for k in range(n_steps):
            dX = np.array([self.simulate_increments(dt, 1)[0] for _ in range(n_paths)])
            X += dX
            S[k + 1] = S0 * np.exp((r + omega) * (k + 1) * dt + X)

        return S

    def cumulants(self) -> dict:
        """Analytical cumulants per unit time."""
        a, b, d = self.alpha, self.beta, self.delta
        g = self.gamma
        return {
            "mean": float(self.mu + d * b / g),
            "variance": float(d * a**2 / g**3),
            "skewness_coefficient": float(3 * b / (a * np.sqrt(d / g))),
            "excess_kurtosis": float(3 * (1 + 4 * b**2 / a**2) / (d * g / a**2)),
        }
