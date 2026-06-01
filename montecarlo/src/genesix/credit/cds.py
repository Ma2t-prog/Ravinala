"""
Credit Default Swap pricing.

A CDS is insurance against default:
- Protection buyer pays spread × notional × δ_i periodically
- On default: seller pays (1 - R) × notional

The par CDS spread is what makes NPV = 0 at inception.
It's the market's price of credit risk — in basis points.
"""

from __future__ import annotations

import numpy as np
from typing import Callable, Optional
from .reduced_form import HazardRateModel


class CDSPricer:
    """Price and risk-manage Credit Default Swaps."""

    def __init__(self, recovery: float = 0.40):
        self.recovery = recovery
        self._hrm = HazardRateModel()

    def price(
        self,
        notional: float,
        spread: float,
        hazard_rates: dict,
        maturity: float,
        recovery: Optional[float] = None,
        discount_curve_fn: Optional[Callable] = None,
        payment_freq: int = 4,
    ) -> dict:
        """
        CDS mark-to-market value.

        Premium Leg PV = spread × Σ δ_i × DF(T_i) × Q(T_i)
        Protection Leg PV = (1-R) × Σ DF(T_mid) × [Q(T_{i-1}) - Q(T_i)]

        NPV (protection buyer) = Protection - Premium

        Returns:
            {
                'npv': float,
                'premium_leg_pv': float,
                'protection_leg_pv': float,
                'risky_annuity': float,
                'dv01': float,
                'cs01': float,
                'jump_to_default': float,
            }
        """
        R = recovery if recovery is not None else self.recovery
        if discount_curve_fn is None:
            discount_curve_fn = lambda t: np.exp(-0.05 * t)

        n_pay = max(1, int(round(maturity * payment_freq)))
        pay_times = np.array([(j + 1) / payment_freq for j in range(n_pay)
                               if (j + 1) / payment_freq <= maturity + 1e-8])

        premium_pv = 0.0
        protection_pv = 0.0
        risky_annuity = 0.0

        q_prev = 1.0
        t_prev = 0.0

        for k, t in enumerate(pay_times):
            df = float(discount_curve_fn(t))
            q = self._hrm.survival_probability(t, hazard_rates)
            delta = t - t_prev
            premium_pv += spread * notional * delta * df * q
            risky_annuity += delta * df * q

            # Accrual on default (mid-period approximation)
            t_mid = 0.5 * (t_prev + t)
            df_mid = float(discount_curve_fn(t_mid))
            protection_pv += (1 - R) * notional * df_mid * (q_prev - q)

            q_prev = q
            t_prev = t

        npv = protection_pv - premium_pv

        # DV01 / CS01: bump spread 1bp
        bump = 0.0001
        hr_bumped = {k: v + bump for k, v in hazard_rates.items()}
        result_bumped = self.price(notional, spread, hr_bumped, maturity, R,
                                    discount_curve_fn, payment_freq)
        dv01 = result_bumped["npv"] - npv
        cs01 = abs(dv01)  # convention: CS01 is the absolute change per 1bp

        # Jump-to-default: loss if default happens immediately
        jtd = (1 - R) * notional

        return {
            "npv": float(npv),
            "premium_leg_pv": float(premium_pv),
            "protection_leg_pv": float(protection_pv),
            "risky_annuity": float(risky_annuity),
            "dv01": float(dv01),
            "cs01": float(cs01),
            "jump_to_default": float(jtd),
        }

    def par_spread(
        self,
        hazard_rates: dict,
        maturity: float,
        recovery: Optional[float] = None,
        discount_curve_fn: Optional[Callable] = None,
        payment_freq: int = 4,
    ) -> float:
        """
        Fair CDS spread (par spread) = Protection Leg PV / Risky Annuity.

        This is the spread that makes NPV = 0 at inception.
        """
        R = recovery if recovery is not None else self.recovery
        if discount_curve_fn is None:
            discount_curve_fn = lambda t: np.exp(-0.05 * t)

        n_pay = max(1, int(round(maturity * payment_freq)))
        pay_times = np.array([(j + 1) / payment_freq for j in range(n_pay)
                               if (j + 1) / payment_freq <= maturity + 1e-8])

        protection_pv = 0.0
        risky_annuity = 0.0
        q_prev = 1.0
        t_prev = 0.0

        for k, t in enumerate(pay_times):
            df = float(discount_curve_fn(t))
            q = self._hrm.survival_probability(t, hazard_rates)
            delta = t - t_prev
            risky_annuity += delta * df * q
            t_mid = 0.5 * (t_prev + t)
            df_mid = float(discount_curve_fn(t_mid))
            protection_pv += (1 - R) * df_mid * (q_prev - q)
            q_prev = q
            t_prev = t

        if risky_annuity < 1e-10:
            return 0.0
        return float(protection_pv / risky_annuity)
