"""
Itô calculus — the chain rule for stochastic processes.

In ordinary calculus: df = f'(x) dx
In Itô calculus:      df = f'(X) dX + ½f''(X) (dX)²

The extra ½f''(X)(dX)² term exists because for Brownian motion,
(dW)² = dt (not 0 like in ordinary calculus). This is the single
most important fact in mathematical finance.

Applications implemented here:
1. Itô's lemma for common functions (log, exp, power)
2. Black-Scholes derivation from Itô's lemma
3. Itô isometry and martingale properties
"""

from __future__ import annotations

import numpy as np
from typing import Optional
from .brownian import BrownianMotion, GeometricBrownianMotion


class ItoCalculus:
    """Itô calculus tools and demonstrations."""

    @staticmethod
    def ito_lemma_demonstration(
        S0: float = 100,
        mu: float = 0.10,
        sigma: float = 0.20,
        T: float = 1.0,
        n_steps: int = 10_000,
        n_paths: int = 10_000,
    ) -> dict:
        """
        Demonstrate Itô's lemma by applying it to f(S) = log(S).

        If S follows GBM: dS = μS dt + σS dW

        By Itô's lemma: d(log S) = (1/S)dS - (1/2)(1/S²)(dS)²
                                   = (μ - σ²/2) dt + σ dW

        This means log(S(T)) - log(S(0)) ~ N((μ - σ²/2)T, σ²T)

        The -σ²/2 is called the Itô correction or convexity adjustment.
        It explains why the median return is LOWER than the mean return.

        Returns:
            {
                'theoretical_mean': (μ - σ²/2)T,
                'simulated_mean': float,
                'naive_mean_WITHOUT_ito': μT,
                'error_without_ito': float,
                'theoretical_variance': σ²T,
                'simulated_variance': float,
                'ito_correction': -σ²T/2,
            }
        """
        gbm = GeometricBrownianMotion(seed=42)
        paths = gbm.simulate(S0, mu, sigma, T, n_steps=n_steps, n_paths=n_paths)
        log_returns = np.log(paths[-1, :] / S0)

        theoretical_mean = (mu - 0.5 * sigma**2) * T
        theoretical_var = sigma**2 * T
        naive_mean = mu * T
        ito_correction = -0.5 * sigma**2 * T

        simulated_mean = float(np.mean(log_returns))
        simulated_var = float(np.var(log_returns))
        error_without_ito = abs(naive_mean - simulated_mean)

        return {
            "theoretical_mean": theoretical_mean,
            "simulated_mean": simulated_mean,
            "naive_mean_WITHOUT_ito": naive_mean,
            "error_without_ito": error_without_ito,
            "theoretical_variance": theoretical_var,
            "simulated_variance": simulated_var,
            "ito_correction": ito_correction,
            "explanation": (
                f"Without the Itô correction you would expect E[log return] = μT = {naive_mean:.4f}. "
                f"The correct answer is (μ - σ²/2)T = {theoretical_mean:.4f}. "
                f"The Itô correction is -σ²/2 = {ito_correction/T:.4f} per year. "
                f"For σ={sigma:.0%} this is {abs(ito_correction)*100:.1f}% per {T:.0f} year(s) — "
                f"ignoring it OVER-estimates log returns by {error_without_ito*100:.2f}%."
            ),
        }

    @staticmethod
    def derive_black_scholes_from_ito() -> str:
        """
        Step-by-step derivation of the Black-Scholes PDE using Itô's lemma.

        Returns: formatted string with full derivation.
        """
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║           BLACK-SCHOLES PDE — DERIVATION VIA ITÔ'S LEMMA                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Step 1: Asset dynamics (GBM)
──────────────────────────────
  dS = μS dt + σS dW

Step 2: Apply Itô's lemma to V(S, t)
──────────────────────────────────────
  dV = (∂V/∂t) dt + (∂V/∂S) dS + ½(∂²V/∂S²)(dS)²

  Since (dS)² = σ²S² dt  [because (dW)² = dt]:

  dV = [∂V/∂t + μS·∂V/∂S + ½σ²S²·∂²V/∂S²] dt + σS·∂V/∂S dW

Step 3: Construct a delta-hedged portfolio
───────────────────────────────────────────
  Π = V − Δ·S   (long option, short Δ shares)

  dΠ = dV − Δ dS
     = [∂V/∂t + μS·∂V/∂S + ½σ²S²·∂²V/∂S²] dt + σS·∂V/∂S dW
       − Δ [μS dt + σS dW]

Step 4: Choose Δ = ∂V/∂S  (delta hedge eliminates dW)
───────────────────────────────────────────────────────
  dΠ = [∂V/∂t + ½σ²S²·∂²V/∂S²] dt

  The portfolio is NOW RISKLESS — no dW term!

Step 5: No-arbitrage requires riskless portfolio earns r
─────────────────────────────────────────────────────────
  dΠ = r·Π dt = r(V − ∂V/∂S · S) dt

Step 6: Equate to obtain the Black-Scholes PDE
────────────────────────────────────────────────
  ∂V/∂t + ½σ²S²·∂²V/∂S² = r(V − S·∂V/∂S)

  ┌─────────────────────────────────────────────────────────┐
  │  ∂V/∂t  +  rS·∂V/∂S  +  ½σ²S²·∂²V/∂S²  −  rV  =  0  │
  └─────────────────────────────────────────────────────────┘

KEY INSIGHT: μ (the asset's drift) has VANISHED.
─────────────────────────────────────────────────
  The option price does not depend on the asset's expected return.
  A bull and a bear must agree on the option price — this is the
  essence of risk-neutral pricing and the foundation of modern finance.

Boundary condition (European call): V(S, T) = max(S − K, 0)
Solution: Black-Scholes formula  C = S·N(d₁) − K·e^{−rT}·N(d₂)
  where d₁ = [ln(S/K) + (r + σ²/2)T] / (σ√T)
        d₂ = d₁ − σ√T
"""

    @staticmethod
    def ito_isometry_demonstration(
        T: float = 1.0,
        n_steps: int = 10_000,
        n_paths: int = 10_000,
    ) -> dict:
        """
        Demonstrate Itô isometry: E[(∫₀ᵀ f(t) dW)²] = E[∫₀ᵀ f(t)² dt]

        Demonstration with f(t) = t:
        Analytical: E[(∫₀ᵀ t dW)²] = ∫₀ᵀ t² dt = T³/3
        """
        bm = BrownianMotion(seed=42)
        dt = T / n_steps
        t_grid = np.linspace(0, T - dt, n_steps)  # f(t_k) = t_k

        # Simulate ∫₀ᵀ t dW(t) for many paths
        dW = np.random.default_rng(42).normal(0, np.sqrt(dt), size=(n_steps, n_paths))
        stoch_integral = np.sum(t_grid.reshape(-1, 1) * dW, axis=0)  # (n_paths,)

        # Analytical: T³/3
        analytical = T**3 / 3.0
        simulated_var = float(np.var(stoch_integral))

        return {
            "analytical_variance": analytical,
            "simulated_variance": simulated_var,
            "relative_error_pct": abs(simulated_var - analytical) / analytical * 100,
            "isometry_holds": abs(simulated_var - analytical) / analytical < 0.05,
            "explanation": (
                "Itô isometry: Var[∫₀ᵀ t dW] = ∫₀ᵀ t² dt = T³/3. "
                f"Analytical = {analytical:.6f}, Simulated = {simulated_var:.6f}. "
                "This holds because Itô integrals are martingales with zero mean "
                "and the variance is fully determined by the integrand squared."
            ),
        }

    @staticmethod
    def product_rule_ito(
        X_paths: np.ndarray,
        Y_paths: np.ndarray,
        dt: float,
    ) -> dict:
        """
        Itô product rule: d(XY) = X dY + Y dX + dX dY

        The extra dX dY term is absent in ordinary calculus.
        For two correlated GBMs: dX dY = σ_X σ_Y ρ dt.

        Demonstrates numerically by comparing:
        1. Direct product XY computed from paths
        2. Reconstructed using Itô product rule

        Returns:
            {
                'max_reconstruction_error': float,
                'cross_variation_term': float,
                'pct_due_to_cross_term': float,
            }
        """
        # Direct product at final time
        XY_direct = X_paths[-1] * Y_paths[-1]

        # Reconstruct via Itô product rule (cumulative sum approximation)
        dX = np.diff(X_paths, axis=0)
        dY = np.diff(Y_paths, axis=0)
        X_prev = X_paths[:-1]
        Y_prev = Y_paths[:-1]

        cross_variation = np.sum(dX * dY, axis=0)  # Σ dX_k dY_k
        xy_ito = (
            X_paths[0] * Y_paths[0]
            + np.sum(X_prev * dY + Y_prev * dX, axis=0)
            + cross_variation
        )

        max_error = float(np.max(np.abs(XY_direct - xy_ito)))
        mean_xy = float(np.mean(np.abs(XY_direct)))
        cross_term_size = float(np.mean(np.abs(cross_variation)))

        return {
            "max_reconstruction_error": max_error,
            "cross_variation_term": cross_term_size,
            "pct_due_to_cross_term": cross_term_size / (mean_xy + 1e-12) * 100,
            "reconstruction_accurate": max_error < 1e-6 * mean_xy,
        }
