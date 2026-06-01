"""
Ravinala — P&L Attribution Engine Backend
Taylor decomposition: ΔP = Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt + Vanna·ΔS·Δσ + ½Volga·Δσ² + ρ·Δr + residual
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks


@dataclass
class AttributionResult:
    delta_pnl: float
    gamma_pnl: float
    vega_pnl: float
    theta_pnl: float
    vanna_pnl: float
    volga_pnl: float
    rho_pnl: float
    residual: float
    total_theoretical: float
    total_actual: float

    @property
    def breakdown(self) -> dict:
        return {
            "Delta": self.delta_pnl,
            "Gamma": self.gamma_pnl,
            "Vega": self.vega_pnl,
            "Theta": self.theta_pnl,
            "Vanna": self.vanna_pnl,
            "Volga": self.volga_pnl,
            "Rho": self.rho_pnl,
            "Residual": self.residual,
        }


def attribute_pnl(
    S0: float,
    S1: float,
    sigma0: float,
    sigma1: float,
    T0: float,
    T1: float,
    r: float,
    K: float,
    option_type: str,
    quantity: int = 1,
    div_yield: float = 0.0,
    dr: float = 0.0,
) -> AttributionResult:
    """
    Taylor decomposition of P&L.
    Greeks evaluated at (S0, sigma0, T0).
    Actual P&L = BS(S1, sigma1, T1) - BS(S0, sigma0, T0).
    All values scaled by quantity * 100.
    """
    scale = quantity * 100
    b0 = r - div_yield
    b1 = (r + dr) - div_yield
    T0 = max(T0, 1e-6)
    T1 = max(T1, 1e-6)

    # Prices
    if option_type == "call":
        P0 = BSG.call_price(S0, K, T0, r, b0, sigma0)
        P1 = BSG.call_price(S1, K, T1, r + dr, b1, sigma1)
    else:
        P0 = BSG.put_price(S0, K, T0, r, b0, sigma0)
        P1 = BSG.put_price(S1, K, T1, r + dr, b1, sigma1)

    total_actual = scale * (P1 - P0)

    # Greeks at initial state
    delta = BSG.delta(S0, K, T0, r, b0, sigma0, option_type)
    gamma = BSG.gamma(S0, K, T0, r, b0, sigma0)
    # vega from engine is per 1% vol → convert to per unit vol for attribution
    vega_raw = BSG.vega(S0, K, T0, r, b0, sigma0) * 100.0
    theta = BSG.theta(S0, K, T0, r, b0, sigma0, option_type)
    rho_raw = BSG.rho(S0, K, T0, r, b0, sigma0, option_type) * 100.0
    vanna = BSG.vanna(S0, K, T0, r, b0, sigma0)
    volga = BSG.volga(S0, K, T0, r, b0, sigma0)

    dS = S1 - S0
    dsigma = sigma1 - sigma0
    dt = T1 - T0  # positive if time passes (T decreases, so dt = T1-T0 < 0 typically)

    # Taylor terms
    delta_pnl = scale * delta * dS
    gamma_pnl = scale * 0.5 * gamma * dS**2
    vega_pnl = scale * vega_raw * dsigma
    theta_pnl = scale * theta * abs(dt) * 365  # theta is per day; dt in years
    vanna_pnl = scale * vanna * dS * dsigma
    volga_pnl = scale * 0.5 * volga * dsigma**2
    rho_pnl = scale * rho_raw * dr

    total_theoretical = delta_pnl + gamma_pnl + vega_pnl + theta_pnl + vanna_pnl + volga_pnl + rho_pnl
    residual = total_actual - total_theoretical

    return AttributionResult(
        delta_pnl=delta_pnl,
        gamma_pnl=gamma_pnl,
        vega_pnl=vega_pnl,
        theta_pnl=theta_pnl,
        vanna_pnl=vanna_pnl,
        volga_pnl=volga_pnl,
        rho_pnl=rho_pnl,
        residual=residual,
        total_theoretical=total_theoretical,
        total_actual=total_actual,
    )


def simulate_price_path(
    S0: float,
    sigma: float,
    r: float,
    div_yield: float = 0.0,
    n_days: int = 30,
    n_paths: int = 5,
    seed: int = 42,
) -> np.ndarray:
    """GBM simulation. Returns array shape (n_paths, n_days+1)."""
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    mu = r - div_yield
    paths = np.zeros((n_paths, n_days + 1))
    paths[:, 0] = S0
    z = rng.standard_normal((n_paths, n_days))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    paths[:, 1:] = S0 * np.exp(np.cumsum(log_returns, axis=1))
    return paths


def multi_day_attribution(
    paths: np.ndarray,
    K: float,
    T0: float,
    r: float,
    sigma: float,
    option_type: str,
    quantity: int = 1,
    div_yield: float = 0.0,
    vol_shock_per_day: float = 0.001,
) -> pd.DataFrame:
    """
    For each path and each day, compute P&L attribution.
    Returns DataFrame: path, day, spot, delta_pnl, gamma_pnl, vega_pnl,
                       theta_pnl, vanna_pnl, volga_pnl, residual, cumulative_pnl
    """
    n_paths, n_steps = paths.shape
    dt_year = 1.0 / 252.0
    rows = []

    for path_idx in range(n_paths):
        cumulative = 0.0
        for day in range(1, n_steps):
            S0 = paths[path_idx, day - 1]
            S1 = paths[path_idx, day]
            T_curr = max(T0 - (day - 1) * dt_year, dt_year)
            T_next = max(T0 - day * dt_year, 1e-6)
            sigma0 = sigma + vol_shock_per_day * (day - 1)
            sigma1 = sigma + vol_shock_per_day * day

            result = attribute_pnl(
                S0, S1, sigma0, sigma1, T_curr, T_next,
                r, K, option_type, quantity, div_yield
            )

            cumulative += result.total_actual
            rows.append({
                "path": path_idx + 1,
                "day": day,
                "spot": S1,
                "delta_pnl": result.delta_pnl,
                "gamma_pnl": result.gamma_pnl,
                "vega_pnl": result.vega_pnl,
                "theta_pnl": result.theta_pnl,
                "vanna_pnl": result.vanna_pnl,
                "volga_pnl": result.volga_pnl,
                "residual": result.residual,
                "daily_pnl": result.total_actual,
                "cumulative_pnl": cumulative,
            })

    return pd.DataFrame(rows)


def sensitivity_attribution(
    S0: float,
    sigma0: float,
    T0: float,
    r: float,
    K: float,
    option_type: str,
    quantity: int = 1,
    div_yield: float = 0.0,
    shock_range: float = 0.30,
    n_points: int = 61,
) -> pd.DataFrame:
    """
    Show how each attribution component changes as S1 varies ±shock_range% from S0.
    """
    shocks = np.linspace(-shock_range, shock_range, n_points)
    T1 = max(T0 - 1.0 / 252.0, 1e-6)
    rows = []
    for pct in shocks:
        S1 = S0 * (1 + pct)
        result = attribute_pnl(S0, S1, sigma0, sigma0, T0, T1, r, K, option_type, quantity, div_yield)
        rows.append({
            "shock_pct": pct * 100,
            "spot": S1,
            "Delta": result.delta_pnl,
            "Gamma": result.gamma_pnl,
            "Vega": result.vega_pnl,
            "Theta": result.theta_pnl,
            "Vanna": result.vanna_pnl,
            "Volga": result.volga_pnl,
            "Residual": result.residual,
            "Total": result.total_actual,
        })
    return pd.DataFrame(rows)
