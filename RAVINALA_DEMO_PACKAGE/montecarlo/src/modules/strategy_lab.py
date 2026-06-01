"""
Ravinala — Option Strategy Lab Backend
Multi-leg options strategy builder: payoffs, Greeks, breakevens, strategy recognition.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks


@dataclass
class Leg:
    direction: str          # "long" or "short"
    option_type: str        # "call", "put", or "stock"
    quantity: int           # number of contracts (1 contract = 100 shares)
    strike: float
    expiry: float           # time to expiry in years
    spot: float
    vol: float
    rate: float
    div_yield: float = 0.0
    premium: Optional[float] = None  # computed from BS if None

    @property
    def b(self) -> float:
        return self.rate - self.div_yield

    @property
    def sign(self) -> int:
        return 1 if self.direction == "long" else -1

    def bs_price(self) -> float:
        if self.option_type == "call":
            return BSG.call_price(self.spot, self.strike, self.expiry, self.rate, self.b, self.vol)
        elif self.option_type == "put":
            return BSG.put_price(self.spot, self.strike, self.expiry, self.rate, self.b, self.vol)
        else:  # stock
            return self.spot


def fill_premiums(legs: List[Leg]) -> List[Leg]:
    """Fill missing premiums using Black-Scholes."""
    for leg in legs:
        if leg.premium is None:
            leg.premium = leg.bs_price()
    return legs


def leg_greeks(leg: Leg) -> Dict[str, float]:
    """Greeks for one leg, scaled by quantity * 100."""
    scale = leg.sign * leg.quantity * 100
    S, K, T, r, b, sigma = leg.spot, leg.strike, leg.expiry, leg.rate, leg.b, leg.vol

    if leg.option_type == "stock":
        return {
            "price": leg.spot,
            "delta": scale * 1.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho": 0.0,
            "vanna": 0.0,
            "volga": 0.0,
        }

    ot = leg.option_type
    return {
        "price": leg.premium or leg.bs_price(),
        "delta": scale * BSG.delta(S, K, T, r, b, sigma, ot),
        "gamma": scale * BSG.gamma(S, K, T, r, b, sigma),
        "vega": scale * BSG.vega(S, K, T, r, b, sigma),
        "theta": scale * BSG.theta(S, K, T, r, b, sigma, ot),
        "rho": scale * BSG.rho(S, K, T, r, b, sigma, ot),
        "vanna": scale * BSG.vanna(S, K, T, r, b, sigma),
        "volga": scale * BSG.volga(S, K, T, r, b, sigma),
    }


def net_greeks(legs: List[Leg]) -> Dict[str, float]:
    """Aggregate Greeks across all legs."""
    keys = ["delta", "gamma", "vega", "theta", "rho", "vanna", "volga"]
    result = {k: 0.0 for k in keys}
    for leg in legs:
        g = leg_greeks(leg)
        for k in keys:
            result[k] += g[k]
    return result


def _leg_payoff_at_expiry(leg: Leg, spots: np.ndarray) -> np.ndarray:
    premium = leg.premium if leg.premium is not None else leg.bs_price()
    qty = leg.quantity * 100

    if leg.option_type == "call":
        intrinsic = np.maximum(spots - leg.strike, 0.0)
    elif leg.option_type == "put":
        intrinsic = np.maximum(leg.strike - spots, 0.0)
    else:  # stock
        intrinsic = spots - leg.spot  # P&L from entry

    if leg.direction == "long":
        return qty * (intrinsic - premium)
    else:
        return qty * (premium - intrinsic)


def payoff_at_expiry(legs: List[Leg], spots: np.ndarray) -> np.ndarray:
    """Total P&L at expiry for an array of spot prices."""
    if not legs:
        return np.zeros_like(spots)
    fill_premiums(legs)
    return sum(_leg_payoff_at_expiry(leg, spots) for leg in legs)


def _leg_payoff_today(leg: Leg, spots: np.ndarray, time_remaining: float) -> np.ndarray:
    """MtM P&L for one leg repriced at time_remaining."""
    premium = leg.premium if leg.premium is not None else leg.bs_price()
    qty = leg.quantity * 100
    T = max(time_remaining, 1e-6)

    if leg.option_type == "stock":
        intrinsic = spots - leg.spot
        if leg.direction == "long":
            return qty * intrinsic
        else:
            return -qty * intrinsic

    prices = np.array([
        (BSG.call_price(s, leg.strike, T, leg.rate, leg.b, leg.vol)
         if leg.option_type == "call"
         else BSG.put_price(s, leg.strike, T, leg.rate, leg.b, leg.vol))
        for s in spots
    ])

    if leg.direction == "long":
        return qty * (prices - premium)
    else:
        return qty * (premium - prices)


def payoff_today(legs: List[Leg], spots: np.ndarray, time_remaining: float) -> np.ndarray:
    """Total MtM P&L for all legs repriced at time_remaining."""
    if not legs:
        return np.zeros_like(spots)
    fill_premiums(legs)
    return sum(_leg_payoff_today(leg, spots, time_remaining) for leg in legs)


def breakevens(legs: List[Leg]) -> List[float]:
    """Find breakeven spot prices from sign changes in payoff_at_expiry."""
    if not legs:
        return []
    spots = np.linspace(
        min(l.strike for l in legs) * 0.5,
        max(l.strike for l in legs) * 1.5,
        2000
    )
    pnl = payoff_at_expiry(legs, spots)
    bes = []
    for i in range(len(pnl) - 1):
        if pnl[i] * pnl[i + 1] < 0:
            # linear interpolation
            be = spots[i] - pnl[i] * (spots[i + 1] - spots[i]) / (pnl[i + 1] - pnl[i])
            bes.append(round(be, 4))
    return bes


def max_profit_loss(legs: List[Leg], spots: np.ndarray) -> Tuple[float, float]:
    """Return (max_profit, max_loss) from payoff_at_expiry."""
    pnl = payoff_at_expiry(legs, spots)
    return float(np.max(pnl)), float(np.min(pnl))


# ─────────────────────────── STRATEGY RECOGNITION ───────────────────────────

def _calls(legs: List[Leg]) -> List[Leg]:
    return [l for l in legs if l.option_type == "call"]

def _puts(legs: List[Leg]) -> List[Leg]:
    return [l for l in legs if l.option_type == "put"]

def _long(legs: List[Leg]) -> List[Leg]:
    return [l for l in legs if l.direction == "long"]

def _short(legs: List[Leg]) -> List[Leg]:
    return [l for l in legs if l.direction == "short"]

def _stocks(legs: List[Leg]) -> List[Leg]:
    return [l for l in legs if l.option_type == "stock"]

def _same_expiry(legs: List[Leg]) -> bool:
    expiries = [round(l.expiry, 6) for l in legs]
    return len(set(expiries)) == 1

def _strikes_sorted(legs: List[Leg]) -> List[float]:
    return sorted(set(l.strike for l in legs))


def recognize_strategy(legs: List[Leg]) -> str:
    if not legs:
        return "Empty"

    n = len(legs)
    calls = _calls(legs)
    puts = _puts(legs)
    stocks = _stocks(legs)
    long_calls = [l for l in calls if l.direction == "long"]
    short_calls = [l for l in calls if l.direction == "short"]
    long_puts = [l for l in puts if l.direction == "long"]
    short_puts = [l for l in puts if l.direction == "short"]

    strikes = _strikes_sorted(legs)
    same_exp = _same_expiry(legs)

    # ── Single leg ──────────────────────────────────────────────────────────
    if n == 1:
        l = legs[0]
        if l.option_type == "stock":
            return "Long Stock" if l.direction == "long" else "Short Stock"
        return f"{'Long' if l.direction == 'long' else 'Short'} {l.option_type.capitalize()}"

    # ── Two legs ─────────────────────────────────────────────────────────────
    if n == 2 and same_exp:
        # Straddle: long call + long put, same strike
        if len(long_calls) == 1 and len(long_puts) == 1:
            if long_calls[0].strike == long_puts[0].strike:
                return "Long Straddle"

        # Short Straddle
        if len(short_calls) == 1 and len(short_puts) == 1:
            if short_calls[0].strike == short_puts[0].strike:
                return "Short Straddle"

        # Strangle: long call + long put, different strikes
        if len(long_calls) == 1 and len(long_puts) == 1:
            return "Long Strangle"

        if len(short_calls) == 1 and len(short_puts) == 1:
            return "Short Strangle"

        # Vertical spreads
        if len(calls) == 2:
            k = sorted([c.strike for c in calls])
            lc = [c for c in calls if c.direction == "long"]
            sc = [c for c in calls if c.direction == "short"]
            if lc and sc:
                if lc[0].strike < sc[0].strike:
                    return "Bull Call Spread"
                else:
                    return "Bear Call Spread"

        if len(puts) == 2:
            lp = [p for p in puts if p.direction == "long"]
            sp = [p for p in puts if p.direction == "short"]
            if lp and sp:
                if lp[0].strike > sp[0].strike:
                    return "Bear Put Spread"
                else:
                    return "Bull Put Spread"

        # Risk Reversal: long call + short put (or reverse)
        if len(long_calls) == 1 and len(short_puts) == 1:
            return "Risk Reversal"
        if len(short_calls) == 1 and len(long_puts) == 1:
            return "Risk Reversal (Bearish)"

        # Calendar / Diagonal
        if not same_exp and len(calls) == 2:
            ks = [c.strike for c in calls]
            if ks[0] == ks[1]:
                return "Calendar Call Spread"
            return "Diagonal Call Spread"
        if not same_exp and len(puts) == 2:
            ks = [p.strike for p in puts]
            if ks[0] == ks[1]:
                return "Calendar Put Spread"
            return "Diagonal Put Spread"

        # Covered Call / Protective Put
        if len(stocks) == 1 and len(short_calls) == 1:
            if stocks[0].direction == "long":
                return "Covered Call"
        if len(stocks) == 1 and len(long_puts) == 1:
            if stocks[0].direction == "long":
                return "Protective Put"

        # Synthetic
        if len(long_calls) == 1 and len(short_puts) == 1:
            if long_calls[0].strike == short_puts[0].strike:
                return "Synthetic Long"
        if len(short_calls) == 1 and len(long_puts) == 1:
            if short_calls[0].strike == long_puts[0].strike:
                return "Synthetic Short"

    # ── Two legs, different expiry ────────────────────────────────────────────
    if n == 2 and not same_exp:
        if len(calls) == 2:
            ks = [c.strike for c in calls]
            return "Calendar Call Spread" if ks[0] == ks[1] else "Diagonal Call Spread"
        if len(puts) == 2:
            ks = [p.strike for p in puts]
            return "Calendar Put Spread" if ks[0] == ks[1] else "Diagonal Put Spread"

    # ── Three legs ────────────────────────────────────────────────────────────
    if n == 3 and same_exp:
        # Strip: 1 long call + 2 long puts, same strike
        if len(long_calls) == 1 and len(long_puts) == 2:
            ks = set(l.strike for l in long_puts)
            if len(ks) == 1 and list(ks)[0] == long_calls[0].strike:
                return "Strip"

        # Strap: 2 long calls + 1 long put, same strike
        if len(long_calls) == 2 and len(long_puts) == 1:
            ks = set(l.strike for l in long_calls)
            if len(ks) == 1 and list(ks)[0] == long_puts[0].strike:
                return "Strap"

        # Ratio spreads
        if len(calls) == 3 and len(long_calls) == 1 and len(short_calls) == 2:
            return "Call Ratio Spread"
        if len(puts) == 3 and len(long_puts) == 1 and len(short_puts) == 2:
            return "Put Ratio Spread"

        # Collar: stock + long put + short call
        if len(stocks) == 1 and len(long_puts) == 1 and len(short_calls) == 1:
            return "Collar"

        # Jade Lizard: short put + short call spread
        if len(short_puts) == 1 and len(short_calls) == 1 and len(long_calls) == 1:
            sc_sorted = sorted(short_calls + long_calls, key=lambda x: x.strike)
            if sc_sorted[0].direction == "short":
                return "Jade Lizard"

        # Butterfly (all calls or all puts, 3 strikes)
        if len(calls) == 3 and len(strikes) == 3:
            k1, k2, k3 = strikes
            if abs((k2 - k1) - (k3 - k2)) < 0.01 * k2:
                lc_ks = sorted(c.strike for c in long_calls)
                if len(long_calls) == 2 and len(short_calls) == 1:
                    if short_calls[0].strike == k2:
                        return "Call Butterfly"
        if len(puts) == 3 and len(strikes) == 3:
            if len(long_puts) == 2 and len(short_puts) == 1:
                return "Put Butterfly"

    # ── Four legs ─────────────────────────────────────────────────────────────
    if n == 4 and same_exp:
        # Iron Condor: long put + short put + short call + long call (4 strikes)
        if len(long_calls) == 1 and len(short_calls) == 1 and len(long_puts) == 1 and len(short_puts) == 1:
            sorted_legs = sorted(legs, key=lambda x: x.strike)
            types = [(l.option_type, l.direction) for l in sorted_legs]
            expected_condor = [("put","long"),("put","short"),("call","short"),("call","long")]
            if types == expected_condor:
                return "Iron Condor"
            # Iron Butterfly: middle two strikes same
            inner_strikes = sorted(set([short_calls[0].strike, short_puts[0].strike]))
            if len(inner_strikes) == 1:
                return "Iron Butterfly"
            return "Iron Condor"

        # Regular butterfly (calls or puts, 4 legs = 1+2+1)
        if len(calls) == 4:
            lc_count = len(long_calls)
            sc_count = len(short_calls)
            if lc_count == 2 and sc_count == 2:
                return "Call Condor"
        if len(puts) == 4:
            lp_count = len(long_puts)
            sp_count = len(short_puts)
            if lp_count == 2 and sp_count == 2:
                return "Put Condor"

    return "Custom"
