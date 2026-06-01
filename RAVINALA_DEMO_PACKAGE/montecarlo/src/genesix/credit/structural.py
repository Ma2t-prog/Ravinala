"""
Structural credit risk — Merton (1974) model.

Key insight: equity is a CALL OPTION on the firm's assets.
If firm value V drops below debt D at maturity, the firm defaults.

E = max(V - D, 0)  ← Black-Scholes with strike = D

This lets us price corporate bonds and estimate default probability
using nothing more than stock prices and balance sheet data.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
from typing import Optional


class MertonModel:
    """
    Merton (1974) structural credit model.

    Firm value: dV = μV dt + σ_V V dW
    Default: V(T) < D

    Equity = Call(V, K=D, T, r, σ_V)
    Risky Debt = Risk-free Debt - Put(V, K=D, T, r, σ_V)
    """

    def __init__(self, V: float, D: float, sigma_V: float, r: float, T: float):
        """
        Args:
            V: current firm asset value
            D: face value of debt
            sigma_V: asset volatility
            r: risk-free rate
            T: debt maturity (years)
        """
        self.V = V
        self.D = D
        self.sigma_V = sigma_V
        self.r = r
        self.T = T

    def _d1_d2(self):
        d1 = (np.log(self.V / self.D) + (self.r + 0.5 * self.sigma_V**2) * self.T) / (
            self.sigma_V * np.sqrt(self.T)
        )
        d2 = d1 - self.sigma_V * np.sqrt(self.T)
        return float(d1), float(d2)

    def equity_value(self) -> float:
        """Equity = Call option on firm assets with strike = debt."""
        d1, d2 = self._d1_d2()
        return float(
            self.V * norm.cdf(d1) - self.D * np.exp(-self.r * self.T) * norm.cdf(d2)
        )

    def debt_value(self) -> float:
        """
        Risky debt value = risk-free bond - put option on assets.

        D_risky = D×e^{-rT} - Put(V, D, T, r, σ_V)
        """
        d1, d2 = self._d1_d2()
        put = (
            self.D * np.exp(-self.r * self.T) * norm.cdf(-d2)
            - self.V * norm.cdf(-d1)
        )
        return float(self.D * np.exp(-self.r * self.T) - put)

    def default_probability(self) -> float:
        """
        Risk-neutral probability of default = N(-d₂).

        P(V(T) < D) under the risk-neutral measure Q.
        """
        _, d2 = self._d1_d2()
        return float(norm.cdf(-d2))

    def distance_to_default(self, mu: float) -> float:
        """
        Distance to default under the real-world measure.

        DD = (ln(V/D) + (μ - σ²/2)T) / (σ_V √T)

        Used by KMV/Moody's: maps to empirical default frequency tables.
        """
        dd = (np.log(self.V / self.D) + (mu - 0.5 * self.sigma_V**2) * self.T) / (
            self.sigma_V * np.sqrt(self.T)
        )
        return float(dd)

    def credit_spread(self) -> float:
        """
        Credit spread = yield on risky debt - risk-free rate.

        spread = -(1/T) × ln(D_risky / (D × e^{-rT}))
        """
        D_risky = self.debt_value()
        D_riskfree = self.D * np.exp(-self.r * self.T)
        if D_risky <= 0 or D_riskfree <= 0:
            return 0.0
        return float(-(1 / self.T) * np.log(D_risky / D_riskfree))

    def leverage_ratio(self) -> float:
        """D / V — higher leverage → higher PD."""
        return float(self.D / self.V)

    def implied_from_equity(self, E_market: float, sigma_E: float) -> dict:
        """
        Solve for (V, σ_V) from observed equity price and equity vol.

        Two equations (Itô's lemma relates equity vol to asset vol):
        1. E = V×N(d₁) - D×e^{-rT}×N(d₂)   [Black-Scholes]
        2. σ_E × E = N(d₁) × σ_V × V         [delta relation]

        Returns the implied (V, σ_V) and updated model metrics.
        """
        D, r, T = self.D, self.r, self.T

        def equations(x):
            V_imp, sigma_imp = x
            if V_imp <= 0 or sigma_imp <= 0:
                return [1e6, 1e6]
            d1 = (np.log(V_imp / D) + (r + 0.5 * sigma_imp**2) * T) / (
                sigma_imp * np.sqrt(T)
            )
            d2 = d1 - sigma_imp * np.sqrt(T)
            E_calc = V_imp * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2)
            sigma_E_calc = norm.cdf(d1) * sigma_imp * V_imp / E_market
            return [E_calc - E_market, sigma_E_calc - sigma_E]

        try:
            V_init = E_market + D * np.exp(-r * T)
            sigma_init = sigma_E * E_market / V_init
            x0 = [V_init, max(sigma_init, 0.05)]
            V_sol, sigma_sol = fsolve(equations, x0, full_output=False)
            V_sol, sigma_sol = float(abs(V_sol)), float(abs(sigma_sol))
        except Exception:
            V_sol = E_market + D * np.exp(-r * T)
            sigma_sol = sigma_E

        implied_model = MertonModel(V_sol, D, sigma_sol, r, T)
        return {
            "implied_V": V_sol,
            "implied_sigma_V": sigma_sol,
            "default_probability": implied_model.default_probability(),
            "distance_to_default": implied_model.distance_to_default(r),
            "credit_spread_bps": implied_model.credit_spread() * 10000,
            "leverage_ratio": implied_model.leverage_ratio(),
        }

    def full_report(self, mu: float = None) -> dict:
        """Complete Merton model report."""
        if mu is None:
            mu = self.r
        d1, d2 = self._d1_d2()
        return {
            "asset_value": float(self.V),
            "debt_face": float(self.D),
            "equity_value": self.equity_value(),
            "debt_value": self.debt_value(),
            "default_probability_rn": self.default_probability(),
            "distance_to_default": self.distance_to_default(mu),
            "credit_spread_bps": self.credit_spread() * 10000,
            "leverage_ratio": self.leverage_ratio(),
            "d1": float(d1),
            "d2": float(d2),
        }
