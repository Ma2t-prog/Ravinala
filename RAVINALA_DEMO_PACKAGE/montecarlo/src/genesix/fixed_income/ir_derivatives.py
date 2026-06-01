"""
Interest rate derivatives pricing.

Instruments:
- Interest Rate Swap (IRS): exchange fixed for floating
- Swap rate, NPV, DV01, risk report

All pricing uses market discount factors (curve-based, model-agnostic).
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional


class InterestRateSwap:
    """
    Interest Rate Swap — the most traded derivative in the world.

    Fixed leg: pays fixed_rate × notional × δ_i, semi-annually
    Floating leg: pays forward_rate × notional × δ_i, quarterly

    Swap rate = (1 - DF(T_N)) / Σ DF(T_i) × δ_i
    """

    def swap_rate(
        self,
        maturities: list,
        discount_factors: list,
        day_fractions: list,
    ) -> float:
        """
        Par swap rate that makes NPV = 0 at inception.

        SR = (DF(T_0) - DF(T_N)) / Σ DF(T_i) × δ_i

        (DF(T_0) = 1.0 for spot-starting swap)
        """
        dfs = np.asarray(discount_factors)
        deltas = np.asarray(day_fractions)
        numerator = 1.0 - dfs[-1]  # spot-starting: DF(T_0)=1
        denominator = np.sum(dfs * deltas)
        if denominator < 1e-10:
            return 0.0
        return float(numerator / denominator)

    def npv(
        self,
        fixed_rate: float,
        notional: float,
        maturities: list,
        discount_factors: list,
        forward_rates: list,
        day_fractions: list,
        is_payer: bool = True,
    ) -> float:
        """
        Net Present Value of an existing swap.

        Fixed leg PV = fixed_rate × notional × Σ DF_i × δ_i
        Floating leg PV = notional × Σ f_i × DF_i × δ_i ≈ notional × (1 - DF_N)

        NPV (payer) = Floating - Fixed
        """
        dfs = np.asarray(discount_factors)
        deltas = np.asarray(day_fractions)
        fwds = np.asarray(forward_rates)

        fixed_pv = fixed_rate * notional * np.sum(dfs * deltas)
        floating_pv = notional * np.sum(fwds * dfs * deltas)

        if is_payer:
            return float(floating_pv - fixed_pv)
        else:
            return float(fixed_pv - floating_pv)

    def dv01(
        self,
        fixed_rate: float,
        notional: float,
        maturities: list,
        discount_factors: list,
        day_fractions: list,
    ) -> float:
        """
        DV01: change in NPV for a 1bp parallel curve shift.

        For a payer swap: DV01 = -fixed_rate × notional × Σ δ_i × DF_i × (-T_i × 0.0001)
        Approximated numerically by bumping all discount factors.
        """
        dfs = np.asarray(discount_factors)
        deltas = np.asarray(day_fractions)
        mats = np.asarray(maturities)

        bump = 0.0001
        # Bump discount factors down (rates up) by 1bp
        dfs_up = dfs * np.exp(-bump * mats)
        # Annuity
        ann_base = np.sum(dfs * deltas)
        ann_up = np.sum(dfs_up * deltas)

        npv_base = notional * (1 - dfs[-1]) - notional * fixed_rate * ann_base
        npv_up = notional * (1 - dfs_up[-1]) - notional * fixed_rate * ann_up

        return float(npv_up - npv_base)

    def swap_risk_report(
        self,
        fixed_rate: float,
        notional: float,
        maturities: list,
        discount_factors: list,
        forward_rates: list,
        day_fractions: list,
    ) -> dict:
        """
        Complete risk report for an interest rate swap.
        """
        par = self.swap_rate(maturities, discount_factors, day_fractions)
        npv_val = self.npv(fixed_rate, notional, maturities, discount_factors,
                           forward_rates, day_fractions, is_payer=True)
        dv01_val = self.dv01(fixed_rate, notional, maturities, discount_factors,
                              day_fractions)

        # Carry: floating rate - fixed rate (current period)
        current_floating = float(forward_rates[0]) if len(forward_rates) > 0 else par
        carry = current_floating - fixed_rate

        # Bump ±50bp
        dfs = np.asarray(discount_factors)
        mats = np.asarray(maturities)
        deltas = np.asarray(day_fractions)
        fwds = np.asarray(forward_rates)

        def _npv_bumped(bump_bps):
            b = bump_bps * 0.0001
            dfs_b = dfs * np.exp(-b * mats)
            fwds_b = fwds + b  # approximate: forward rates shift too
            return self.npv(fixed_rate, notional, maturities, list(dfs_b),
                            list(fwds_b), day_fractions, is_payer=True)

        mtm_up50 = _npv_bumped(50)
        mtm_dn50 = _npv_bumped(-50)

        breakeven = -npv_val / dv01_val if abs(dv01_val) > 0 else 0.0

        return {
            "npv": float(npv_val),
            "par_rate": float(par),
            "fixed_rate": float(fixed_rate),
            "dv01": float(dv01_val),
            "carry_bps": float(carry * 10000),
            "breakeven_bps": float(breakeven),
            "mtm_if_rates_up_50bp": float(mtm_up50),
            "mtm_if_rates_down_50bp": float(mtm_dn50),
            "notional": float(notional),
        }
