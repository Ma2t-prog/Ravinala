"""
Ravinala — Position Book Manager Backend
Multi-position Greeks aggregation, scenario analysis, hedging suggestions.
"""

from __future__ import annotations

import uuid
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks


@dataclass
class Position:
    id: str
    name: str
    direction: str       # "long" or "short"
    option_type: str     # "call", "put", "stock"
    quantity: int        # contracts
    strike: float
    expiry: float        # T in years
    spot: float
    vol: float
    rate: float
    div_yield: float = 0.0
    entry_price: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def b(self) -> float:
        return self.rate - self.div_yield

    @property
    def sign(self) -> int:
        return 1 if self.direction == "long" else -1

    def current_price(self) -> float:
        S, K, T, r, b, sigma = self.spot, self.strike, self.expiry, self.rate, self.b, self.vol
        if self.option_type == "call":
            return BSG.call_price(S, K, T, r, b, sigma)
        elif self.option_type == "put":
            return BSG.put_price(S, K, T, r, b, sigma)
        else:
            return self.spot

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction,
            "option_type": self.option_type,
            "quantity": self.quantity,
            "strike": self.strike,
            "expiry": self.expiry,
            "spot": self.spot,
            "vol": self.vol,
            "rate": self.rate,
            "div_yield": self.div_yield,
            "entry_price": self.entry_price,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        return cls(**d)


def new_position(
    name: str, direction: str, option_type: str, quantity: int,
    strike: float, expiry_days: int, spot: float, vol: float, rate: float,
    div_yield: float = 0.0, entry_price: float = 0.0,
) -> Position:
    return Position(
        id=str(uuid.uuid4())[:8],
        name=name,
        direction=direction,
        option_type=option_type,
        quantity=quantity,
        strike=strike,
        expiry=max(expiry_days / 365.0, 1e-6),
        spot=spot,
        vol=vol,
        rate=rate,
        div_yield=div_yield,
        entry_price=entry_price,
    )


def position_greeks(pos: Position) -> Dict[str, float]:
    """Greeks for one position, scaled by qty*100."""
    scale = pos.sign * pos.quantity * 100
    S, K, T, r, b, sigma = pos.spot, pos.strike, pos.expiry, pos.rate, pos.b, pos.vol
    T = max(T, 1e-6)

    if pos.option_type == "stock":
        return {
            "price": pos.spot,
            "delta": scale * 1.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho": 0.0,
            "vanna": 0.0,
            "volga": 0.0,
        }

    ot = pos.option_type
    return {
        "price": pos.current_price(),
        "delta": scale * BSG.delta(S, K, T, r, b, sigma, ot),
        "gamma": scale * BSG.gamma(S, K, T, r, b, sigma),
        "vega": scale * BSG.vega(S, K, T, r, b, sigma),
        "theta": scale * BSG.theta(S, K, T, r, b, sigma, ot),
        "rho": scale * BSG.rho(S, K, T, r, b, sigma, ot),
        "vanna": scale * BSG.vanna(S, K, T, r, b, sigma),
        "volga": scale * BSG.volga(S, K, T, r, b, sigma),
    }


def book_greeks(positions: List[Position]) -> Dict[str, float]:
    """Aggregate Greeks for the whole book."""
    keys = ["delta", "gamma", "vega", "theta", "rho", "vanna", "volga"]
    result = {k: 0.0 for k in keys}
    for pos in positions:
        g = position_greeks(pos)
        for k in keys:
            result[k] += g[k]
    return result


def book_summary_df(positions: List[Position]) -> pd.DataFrame:
    """DataFrame summary of all positions with P&L."""
    rows = []
    for pos in positions:
        g = position_greeks(pos)
        curr_price = pos.current_price()
        pnl = pos.sign * pos.quantity * 100 * (curr_price - pos.entry_price)
        rows.append({
            "ID": pos.id,
            "Name": pos.name,
            "Type": pos.option_type.capitalize(),
            "Dir": pos.direction.capitalize(),
            "Qty": pos.quantity,
            "Strike": pos.strike,
            "Expiry (d)": round(pos.expiry * 365),
            "Spot": pos.spot,
            "Vol %": f"{pos.vol*100:.1f}%",
            "Entry": round(pos.entry_price, 4),
            "Current": round(curr_price, 4),
            "P&L": round(pnl, 2),
            "Delta": round(g["delta"], 4),
            "Gamma": round(g["gamma"], 6),
            "Vega": round(g["vega"], 4),
            "Theta": round(g["theta"], 4),
            "Rho": round(g["rho"], 4),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def hedge_suggestions(positions: List[Position], spot: float, vol: float, rate: float) -> List[Dict]:
    """Suggest hedges to neutralize delta, gamma, vega."""
    if not positions:
        return []

    book = book_greeks(positions)
    suggestions = []
    ref_pos = positions[0]  # use first position params as reference for ATM option
    S, K, T, r, b = spot, spot, ref_pos.expiry, rate, rate - ref_pos.div_yield

    # Delta hedge with stock
    delta_net = book["delta"]
    if abs(delta_net) > 1.0:
        shares = -round(delta_net)
        direction = "short" if shares < 0 else "long"
        suggestions.append({
            "greek": "Delta",
            "instrument": "Stock",
            "suggestion": f"{'Buy' if direction=='long' else 'Sell'} {abs(shares)} shares of underlying",
            "quantity": abs(shares),
            "direction": direction,
            "option_type": "stock",
            "strike": spot,
            "expiry_days": 0,
        })

    # Gamma hedge with ATM call
    gamma_net = book["gamma"]
    if abs(gamma_net) > 0.01:
        atm_gamma = BSG.gamma(S, K, T, r, b, vol) * 100  # per contract
        if abs(atm_gamma) > 1e-8:
            n_contracts = -int(round(gamma_net / atm_gamma))
            if abs(n_contracts) > 0:
                direction = "long" if n_contracts > 0 else "short"
                suggestions.append({
                    "greek": "Gamma",
                    "instrument": "ATM Call",
                    "suggestion": f"{'Buy' if direction=='long' else 'Sell'} {abs(n_contracts)} ATM call contract(s) (K={K:.2f})",
                    "quantity": abs(n_contracts),
                    "direction": direction,
                    "option_type": "call",
                    "strike": K,
                    "expiry_days": int(T * 365),
                })

    # Vega hedge with ATM straddle
    vega_net = book["vega"]
    if abs(vega_net) > 1.0:
        atm_vega = BSG.vega(S, K, T, r, b, vol) * 100  # per contract
        if abs(atm_vega) > 1e-8:
            n_contracts = -int(round(vega_net / atm_vega))
            if abs(n_contracts) > 0:
                direction = "long" if n_contracts > 0 else "short"
                suggestions.append({
                    "greek": "Vega",
                    "instrument": "ATM Straddle",
                    "suggestion": f"{'Buy' if direction=='long' else 'Sell'} {abs(n_contracts)} ATM straddle(s) (K={K:.2f})",
                    "quantity": abs(n_contracts),
                    "direction": direction,
                    "option_type": "call",
                    "strike": K,
                    "expiry_days": int(T * 365),
                })

    return suggestions


def scenario_book(
    positions: List[Position],
    spot_shocks: List[float],
    vol_shocks: List[float],
) -> pd.DataFrame:
    """
    P&L matrix under spot/vol shocks (percentage changes as decimals).
    Returns DataFrame: rows=vol_shocks (high→low), cols=spot_shocks.
    """
    if not positions:
        return pd.DataFrame()

    matrix = np.zeros((len(vol_shocks), len(spot_shocks)))
    for i, vs in enumerate(vol_shocks):
        for j, ss in enumerate(spot_shocks):
            total_pnl = 0.0
            for pos in positions:
                new_spot = pos.spot * (1 + ss)
                new_vol = max(pos.vol * (1 + vs), 0.005)
                S, K, T, r, b = new_spot, pos.strike, pos.expiry, pos.rate, pos.rate - pos.div_yield
                T = max(T, 1e-6)

                if pos.option_type == "call":
                    new_price = BSG.call_price(new_spot, K, T, r, b, new_vol)
                elif pos.option_type == "put":
                    new_price = BSG.put_price(new_spot, K, T, r, b, new_vol)
                else:
                    new_price = new_spot

                pnl = pos.sign * pos.quantity * 100 * (new_price - pos.entry_price)
                total_pnl += pnl

            matrix[i, j] = round(total_pnl, 2)

    row_labels = [f"{v*100:+.0f}% vol" for v in sorted(vol_shocks, reverse=True)]
    col_labels = [f"{s*100:+.0f}%" for s in spot_shocks]
    sorted_matrix = matrix[np.argsort(vol_shocks)[::-1], :]
    return pd.DataFrame(sorted_matrix, index=row_labels, columns=col_labels)
