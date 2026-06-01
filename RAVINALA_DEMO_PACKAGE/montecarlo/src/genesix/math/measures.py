"""
Risk-neutral pricing, Girsanov theorem, and Feynman-Kac formula.

Three pillars of derivative pricing theory:

1. Girsanov theorem: change from real-world (P) to risk-neutral (Q) measure
2. Risk-neutral pricing: E^Q[exp(-rT) × payoff] gives the option price
3. Feynman-Kac: connects SDEs to PDEs (Black-Scholes PDE is a special case)

Understanding these separates someone who USES Black-Scholes from
someone who UNDERSTANDS why it works.
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional
from scipy.stats import norm


class RiskNeutralPricing:
    """Risk-neutral pricing framework."""

    @staticmethod
    def explain_risk_neutral_measure() -> str:
        """
        Plain English + math explanation of the risk-neutral measure.
        """
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    THE RISK-NEUTRAL MEASURE                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Under the REAL-WORLD measure P:
  dS = μS dt + σS dW^P    (asset expected return = μ)

Under the RISK-NEUTRAL measure Q:
  dS = rS dt + σS dW^Q    (asset expected return = r, the risk-free rate)

KEY INSIGHT: We don't need to know μ to price options!
─────────────────────────────────────────────────────
  Two traders can disagree on μ (one bullish, one bearish).
  But they MUST agree on the option price (no-arbitrage principle).
  Therefore the option price CANNOT depend on μ.

  Under Q, we replace μ with r — which everyone agrees on.
  Price = E^Q[exp(-rT) × payoff]

The Girsanov Theorem — switching from P to Q:
──────────────────────────────────────────────
  dW^Q = dW^P + θ dt    where θ = (μ - r) / σ  (market price of risk)

  The Radon-Nikodym derivative:
  dQ/dP = exp(-θ W^P(T) - ½θ²T)

  This is the "weight" that converts expectations under P to expectations under Q.

Practical interpretation:
─────────────────────────
  A trader with μ = 15%, r = 5%, σ = 20% has market price of risk θ = 0.5.
  When pricing options, we "pretend" assets grow at r = 5%, not μ = 15%.
  The risk premium is already embedded in option prices via the vol parameter σ.
"""

    @staticmethod
    def price_european_option_mc(
        payoff_fn: Callable,
        S0: float,
        r: float,
        sigma: float,
        T: float,
        n_paths: int = 100_000,
        seed: int = 42,
    ) -> dict:
        """
        Generic European option pricing by risk-neutral Monte Carlo.

        Price = exp(-rT) × E^Q[payoff(S(T))]

        Under Q: S(T) = S0 × exp((r - σ²/2)T + σ√T × Z), Z ~ N(0,1)

        Args:
            payoff_fn: callable(ST) → payoff at maturity
                       e.g. lambda ST: np.maximum(ST - K, 0) for a call
        """
        rng = np.random.default_rng(seed)
        Z = rng.standard_normal(n_paths)
        ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)

        payoffs = payoff_fn(ST)
        price = np.exp(-r * T) * np.mean(payoffs)
        stderr = np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths)

        return {
            "price": float(price),
            "stderr": float(stderr),
            "confidence_interval_95": (float(price - 1.96 * stderr), float(price + 1.96 * stderr)),
            "n_paths": n_paths,
        }

    @staticmethod
    def demonstrate_girsanov(
        S0: float = 100,
        mu: float = 0.15,
        r: float = 0.05,
        sigma: float = 0.20,
        T: float = 1.0,
        K: float = 100,
        n_paths: int = 100_000,
    ) -> dict:
        """
        Show that pricing under P and Q give the SAME option price.

        Under P: S(T) = S0 × exp((μ - σ²/2)T + σ√T × Z)
                 Price_P = E^P[exp(-rT) × payoff × (dQ/dP)]
                 where dQ/dP = exp(-θW(T) - ½θ²T), θ = (μ-r)/σ

        Under Q: S(T) = S0 × exp((r - σ²/2)T + σ√T × Z)
                 Price_Q = exp(-rT) × E^Q[payoff]
        """
        rng = np.random.default_rng(42)
        theta = (mu - r) / sigma  # market price of risk

        # Under Q (risk-neutral)
        Z = rng.standard_normal(n_paths)
        ST_Q = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)
        payoffs_Q = np.maximum(ST_Q - K, 0)
        price_Q = float(np.exp(-r * T) * np.mean(payoffs_Q))

        # Under P with Radon-Nikodym correction
        W_T = np.sqrt(T) * Z  # Brownian motion at T under Q
        # Re-interpret: under P, W^P(T) = W^Q(T) - θT (Girsanov)
        W_P = W_T - theta * T  # this recovers the same paths viewed under P
        ST_P = S0 * np.exp((mu - 0.5 * sigma**2) * T + sigma * W_P)
        radon_nikodym = np.exp(-theta * W_P - 0.5 * theta**2 * T)
        payoffs_P = np.maximum(ST_P - K, 0)
        price_P = float(np.exp(-r * T) * np.mean(payoffs_P * radon_nikodym))

        # Black-Scholes exact
        d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        bs_price = float(S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))

        return {
            "price_under_P": price_P,
            "price_under_Q": price_Q,
            "black_scholes_exact": bs_price,
            "max_difference_P_vs_BS": abs(price_P - bs_price),
            "max_difference_Q_vs_BS": abs(price_Q - bs_price),
            "market_price_of_risk_theta": theta,
            "interpretation": (
                f"Under P (μ={mu:.0%}): {price_P:.4f} | "
                f"Under Q (r={r:.0%}): {price_Q:.4f} | "
                f"Black-Scholes: {bs_price:.4f}. "
                f"Both measures converge to the same price — "
                f"this is Girsanov's theorem in action. "
                f"The market price of risk θ={(mu-r)/sigma:.2f} converts P to Q."
            ),
        }

    @staticmethod
    def feynman_kac_demonstration() -> str:
        """
        Show the Feynman-Kac connection: SDE ↔ PDE.
        """
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FEYNMAN-KAC THEOREM                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

General Statement:
──────────────────
  If X follows:  dX = μ(X,t) dt + σ(X,t) dW

  And we define: u(x,t) = E[g(X(T)) | X(t) = x]

  Then u satisfies the PDE:
  ∂u/∂t + μ(x,t)·∂u/∂x + ½σ²(x,t)·∂²u/∂x² = 0
  with terminal condition: u(x,T) = g(x)

Connection to Black-Scholes:
─────────────────────────────
  Under Q: dS = rS dt + σS dW

  Identify:  μ(S,t) = rS,   σ(S,t) = σS,   g(S) = max(S-K, 0)

  Feynman-Kac gives exactly the Black-Scholes PDE:
  ∂V/∂t + rS·∂V/∂S + ½σ²S²·∂²V/∂S² - rV = 0

  The -rV term arises because u(x,t) = E^Q[e^{-r(T-t)} g(X(T)) | X(t)=x]
  (discounted expectation).

Implications — Two Equivalent Approaches:
───────────────────────────────────────────
  1. Monte Carlo (SDE view):
     Simulate many paths of dS = rS dt + σS dW under Q.
     Average the discounted payoff: price = e^{-rT} E^Q[payoff(S(T))]

  2. Finite Differences (PDE view):
     Discretize the Black-Scholes PDE on a grid.
     March backward in time from terminal condition.

  BOTH give the same answer. Feynman-Kac guarantees this equivalence.

  The choice between them is purely numerical:
  - Monte Carlo: scales well to high dimensions, good for path-dependent options
  - Finite Differences: fast for 1D/2D, better for American options (free boundary)
"""

    @staticmethod
    def black_scholes(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = "call",
    ) -> dict:
        """
        Black-Scholes analytical formula.

        Returns price, delta, gamma, vega, theta, rho.
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = norm.cdf(d1)
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * (norm.cdf(d2) if option_type == "call" else norm.cdf(-d2))
        ) / 365

        return {
            "price": float(price),
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta),
            "rho": float(rho),
            "d1": float(d1),
            "d2": float(d2),
        }
