"""
Ravinala — Scenario Matrix & Greeks Surface Backend
2D P&L heatmaps and 3D Greek surfaces using Black-Scholes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Literal, Tuple
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks


def _compute_metric(
    S: float, K: float, T: float, r: float, b: float, sigma: float,
    option_type: str, metric: str
) -> float:
    """Compute a single metric value."""
    if T <= 0 or sigma <= 0:
        if metric == "price":
            return max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        return 0.0

    ot = option_type
    m = metric.lower()
    if m == "price":
        return BSG.call_price(S, K, T, r, b, sigma) if ot == "call" else BSG.put_price(S, K, T, r, b, sigma)
    elif m == "delta":
        return BSG.delta(S, K, T, r, b, sigma, ot)
    elif m == "gamma":
        return BSG.gamma(S, K, T, r, b, sigma)
    elif m == "vega":
        return BSG.vega(S, K, T, r, b, sigma)
    elif m == "theta":
        return BSG.theta(S, K, T, r, b, sigma, ot)
    elif m == "rho":
        return BSG.rho(S, K, T, r, b, sigma, ot)
    elif m == "vanna":
        return BSG.vanna(S, K, T, r, b, sigma)
    elif m == "volga":
        return BSG.volga(S, K, T, r, b, sigma)
    return 0.0


def build_scenario_matrix(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    div_yield: float = 0.0,
    spot_range_pct: float = 0.30,
    vol_range_pct: float = 0.50,
    n_spots: int = 15,
    n_vols: int = 15,
    metric: str = "price",
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Build a scenario matrix of `metric` over a grid of spot × vol values.
    Returns (matrix_df, spots_array, vols_array).
    Rows = vol axis (high to low), cols = spot axis (low to high).
    """
    b = r - div_yield
    spots = np.linspace(S * (1 - spot_range_pct), S * (1 + spot_range_pct), n_spots)
    vols = np.linspace(max(sigma * (1 - vol_range_pct), 0.01), sigma * (1 + vol_range_pct), n_vols)

    matrix = np.zeros((n_vols, n_spots))
    for i, v in enumerate(vols):
        for j, s in enumerate(spots):
            matrix[i, j] = _compute_metric(s, K, T, r, b, v, option_type, metric)

    df = pd.DataFrame(
        matrix[::-1],  # high vol at top
        index=[f"{v*100:.1f}%" for v in vols[::-1]],
        columns=[f"{s:.2f}" for s in spots],
    )
    return df, spots, vols


def greeks_vs_spot(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    div_yield: float = 0.0,
    n_spots: int = 100,
) -> pd.DataFrame:
    """DataFrame with columns: spot, price, delta, gamma, vega, theta, rho."""
    b = r - div_yield
    T = max(T, 1e-6)
    spots = np.linspace(S * 0.5, S * 1.5, n_spots)
    rows = []
    for s in spots:
        rows.append({
            "spot": s,
            "price": _compute_metric(s, K, T, r, b, sigma, option_type, "price"),
            "delta": _compute_metric(s, K, T, r, b, sigma, option_type, "delta"),
            "gamma": _compute_metric(s, K, T, r, b, sigma, option_type, "gamma"),
            "vega": _compute_metric(s, K, T, r, b, sigma, option_type, "vega"),
            "theta": _compute_metric(s, K, T, r, b, sigma, option_type, "theta"),
            "rho": _compute_metric(s, K, T, r, b, sigma, option_type, "rho"),
        })
    return pd.DataFrame(rows)


def greeks_surface_3d(
    S: float,
    K: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    div_yield: float = 0.0,
    greek: str = "delta",
    spot_range_pct: float = 0.30,
    n_spots: int = 30,
    n_times: int = 20,
    T_max: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Greek surface vs (spot, time_to_expiry).
    Returns (spots, times, surface) where surface[i, j] = greek at spots[i], times[j].
    """
    b = r - div_yield
    spots = np.linspace(S * (1 - spot_range_pct), S * (1 + spot_range_pct), n_spots)
    times = np.linspace(0.01, T_max, n_times)

    surface = np.zeros((n_spots, n_times))
    for i, s in enumerate(spots):
        for j, t in enumerate(times):
            surface[i, j] = _compute_metric(s, K, t, r, b, sigma, option_type, greek)

    return spots, times, surface


def vol_surface_3d(
    S: float,
    K: float,
    r: float,
    option_type: str = "call",
    div_yield: float = 0.0,
    greek: str = "price",
    spot_range_pct: float = 0.30,
    vol_range_pct: float = 0.50,
    sigma_center: float = 0.25,
    n_spots: int = 30,
    n_vols: int = 20,
    T: float = 0.25,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Greek surface vs (spot, vol) at fixed T.
    Returns (spots, vols, surface).
    """
    b = r - div_yield
    spots = np.linspace(S * (1 - spot_range_pct), S * (1 + spot_range_pct), n_spots)
    vols = np.linspace(max(sigma_center * (1 - vol_range_pct), 0.01), sigma_center * (1 + vol_range_pct), n_vols)

    surface = np.zeros((n_spots, n_vols))
    for i, s in enumerate(spots):
        for j, v in enumerate(vols):
            surface[i, j] = _compute_metric(s, K, T, r, b, v, option_type, greek)

    return spots, vols, surface


def term_structure(
    S: float,
    K: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    div_yield: float = 0.0,
    greek: str = "delta",
    n_spots: int = 80,
    expiries_days: List[int] = None,
) -> pd.DataFrame:
    """
    Greek vs spot for multiple expiries.
    Returns DataFrame: columns = spot, T_Xd for each expiry.
    """
    from typing import List
    if expiries_days is None:
        expiries_days = [7, 14, 30, 60, 90, 180, 365]

    b = r - div_yield
    spots = np.linspace(S * 0.6, S * 1.4, n_spots)
    df = pd.DataFrame({"spot": spots})
    for days in expiries_days:
        T = days / 365.0
        label = f"{days}d"
        df[label] = [_compute_metric(s, K, T, r, b, sigma, option_type, greek) for s in spots]
    return df
