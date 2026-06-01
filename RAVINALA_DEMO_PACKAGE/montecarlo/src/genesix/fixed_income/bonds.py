"""
Bond analytics — the foundation of fixed income.

A bond is a stream of cash flows. Everything in fixed income reduces to:
"What is this stream of cash flows worth today, and how does its value
change when rates move?"

Key concepts:
- Price: present value of all future cash flows
- Yield to Maturity (YTM): internal rate of return if held to maturity
- Duration: sensitivity of price to yield changes (first derivative)
- Convexity: curvature of price-yield relationship (second derivative)
- DV01: dollar value of 1 basis point move
- Key Rate Duration: sensitivity to specific maturity points on the curve
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from typing import Optional


class BondAnalytics:
    """Bond analytics: price, duration, convexity, DV01, key rate durations."""

    def price(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        Bond price from yield to maturity.

        P = Σ_{i=1}^{N} C/(1+y/f)^i + F/(1+y/f)^N

        Args:
            face: par value (typically 100)
            coupon_rate: annual coupon rate (0.05 = 5%)
            ytm: yield to maturity (annualized)
            maturity: years to maturity
            frequency: coupons per year (2 = semi-annual)

        Returns: clean price (no accrued interest)
        """
        N = int(round(maturity * frequency))
        C = face * coupon_rate / frequency
        y = ytm / frequency
        periods = np.arange(1, N + 1)
        cf = np.full(N, C)
        cf[-1] += face
        return float(np.sum(cf / (1 + y) ** periods))

    def ytm_from_price(
        self,
        price: float,
        face: float,
        coupon_rate: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        Solve for YTM given price (Brent's method).

        No closed-form solution exists for coupon bonds — solves numerically.
        """
        def objective(y):
            return self.price(face, coupon_rate, y, maturity, frequency) - price

        # Bracket: yield between 0.01 bp and 99%
        return float(brentq(objective, 1e-6, 0.9999, xtol=1e-10))

    def macaulay_duration(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        Macaulay duration — weighted average time to receive cash flows.

        D_mac = (1/P) × Σ_{i=1}^{N} t_i × CF_i / (1+y/f)^i

        Units: years. A zero-coupon bond has duration exactly equal to maturity.
        A coupon bond has duration < maturity (you receive cash earlier).
        """
        N = int(round(maturity * frequency))
        C = face * coupon_rate / frequency
        y = ytm / frequency
        periods = np.arange(1, N + 1)
        times = periods / frequency  # years
        cf = np.full(N, C)
        cf[-1] += face
        pvs = cf / (1 + y) ** periods
        P = pvs.sum()
        return float(np.sum(times * pvs) / P)

    def modified_duration(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        Modified duration — direct price sensitivity to yield.

        D_mod = D_mac / (1 + y/f)

        ΔP/P ≈ -D_mod × Δy

        A bond with D_mod = 7.5 loses ~7.5% for every 1% (100 bps) yield rise.
        """
        D_mac = self.macaulay_duration(face, coupon_rate, ytm, maturity, frequency)
        return D_mac / (1 + ytm / frequency)

    def convexity(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        Convexity — second-order price sensitivity.

        C = (1/P) × Σ t_i(t_i + 1/f) × CF_i / (1+y/f)^(i+2)

        ΔP/P ≈ -D_mod × Δy + ½ × C × (Δy)²

        Always positive for plain vanilla bonds — "free gamma."
        Bonds gain more from falling rates than they lose from rising rates.
        """
        N = int(round(maturity * frequency))
        C = face * coupon_rate / frequency
        y = ytm / frequency
        f = frequency
        periods = np.arange(1, N + 1)
        times = periods / f
        cf = np.full(N, C)
        cf[-1] += face
        P = self.price(face, coupon_rate, ytm, maturity, frequency)
        conv_sum = np.sum(times * (times + 1 / f) * cf / (1 + y) ** (periods + 2))
        return float(conv_sum / P)

    def dv01(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> float:
        """
        DV01 — Dollar Value of 01 (1 basis point).

        DV01 = |P(y - 0.0001) - P(y + 0.0001)| / 2

        "If rates move 1bp, how many dollars does this bond gain/lose per 100 face?"
        DV01 ≈ D_mod × P × 0.0001
        """
        bump = 0.0001
        p_up = self.price(face, coupon_rate, ytm + bump, maturity, frequency)
        p_dn = self.price(face, coupon_rate, ytm - bump, maturity, frequency)
        return float(abs(p_dn - p_up) / 2)

    def key_rate_durations(
        self,
        face: float,
        coupon_rate: float,
        maturity: float,
        frequency: int,
        curve: dict,
        bump_size: float = 0.0001,
    ) -> dict:
        """
        Key Rate Durations — sensitivity to specific yield curve points.

        Bumps each key rate by bump_size, reprices, computes price sensitivity.
        Key rates: 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y.

        Sum of KRDs ≈ Modified Duration (by construction).

        Financial insight: a bullet bond has KRD concentrated near its maturity.
        A barbell (2Y + 30Y) has KRD at those tenors but not in between.
        """
        key_tenors = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
        key_names = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]

        # Price bond using flat curve at par yield
        # For KRD we use: each coupon period, find the applicable zero rate by
        # linear interpolation of key rates, then bump one tenor at a time.
        N = int(round(maturity * frequency))
        periods = np.arange(1, N + 1)
        times = periods / frequency

        def _interp_rate(t, rates_dict):
            """Linear interpolate zero rate from key tenors."""
            tenors = sorted(rates_dict.keys())
            rates = [rates_dict[k] for k in tenors]
            return float(np.interp(t, tenors, rates))

        def _price_from_curve(rates_dict):
            C = face * coupon_rate / frequency
            cf = np.full(N, C)
            cf[-1] += face
            pv = 0.0
            for i, t in enumerate(times):
                r = _interp_rate(t, rates_dict)
                pv += cf[i] / (1 + r / frequency) ** (i + 1)
            return pv

        base_price = _price_from_curve(curve)
        krds = {}
        for name, tenor in zip(key_names, key_tenors):
            bumped_up = dict(curve)
            bumped_dn = dict(curve)
            if tenor in bumped_up:
                bumped_up[tenor] = curve[tenor] + bump_size
                bumped_dn[tenor] = curve[tenor] - bump_size
            else:
                bumped_up[tenor] = bump_size
                bumped_dn[tenor] = -bump_size
            p_up = _price_from_curve(bumped_up)
            p_dn = _price_from_curve(bumped_dn)
            krd = -(p_up - p_dn) / (2 * bump_size * base_price)
            krds[name] = float(krd)

        krds["sum"] = float(sum(krds[k] for k in key_names))
        return krds

    def bond_risk_report(
        self,
        face: float,
        coupon_rate: float,
        ytm: float,
        maturity: float,
        frequency: int = 2,
    ) -> dict:
        """
        Complete risk report for a single bond.
        """
        P = self.price(face, coupon_rate, ytm, maturity, frequency)
        D_mac = self.macaulay_duration(face, coupon_rate, ytm, maturity, frequency)
        D_mod = self.modified_duration(face, coupon_rate, ytm, maturity, frequency)
        C_vex = self.convexity(face, coupon_rate, ytm, maturity, frequency)
        dv = self.dv01(face, coupon_rate, ytm, maturity, frequency)

        # Bump and reprice ±100bp
        bump_100 = 0.01
        p_up_100 = self.price(face, coupon_rate, ytm + bump_100, maturity, frequency)
        p_dn_100 = self.price(face, coupon_rate, ytm - bump_100, maturity, frequency)

        # Effective duration (numerical)
        eff_dur = -(p_up_100 - p_dn_100) / (2 * bump_100 * P)

        # Breakeven: yield move to lose 1 year of carry (approx coupon/price per year)
        carry = face * coupon_rate / P
        breakeven = carry / D_mod if D_mod > 0 else 0.0

        # Flat key rate curve at YTM
        flat_curve = {1: ytm, 2: ytm, 3: ytm, 5: ytm, 7: ytm, 10: ytm, 20: ytm, 30: ytm}
        krds = self.key_rate_durations(face, coupon_rate, maturity, frequency, flat_curve)

        # Annual coupon / price
        current_yield = face * coupon_rate / P

        return {
            "price": float(P),
            "ytm": float(ytm),
            "current_yield": float(current_yield),
            "macaulay_duration": float(D_mac),
            "modified_duration": float(D_mod),
            "effective_duration": float(eff_dur),
            "convexity": float(C_vex),
            "dv01": float(dv),
            "price_if_rates_up_100bp": float(p_up_100),
            "price_if_rates_down_100bp": float(p_dn_100),
            "breakeven_rate_move_bps": float(breakeven * 10000),
            "key_rate_durations": krds,
        }
