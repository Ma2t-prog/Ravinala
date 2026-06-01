"""
Reduced-form credit models — default arrives as a Poisson surprise.

Unlike structural models (default when V < D), reduced-form models
treat default as an unpredictable Poisson event with intensity λ(t).

P(default in [t, t+dt] | survival to t) = λ(t) × dt
Survival probability: Q(T) = exp(-∫₀ᵀ λ(t) dt)

The hazard rate λ(t) is calibrated directly to market CDS spreads.
Simple approximation: λ ≈ spread / (1 - R).

Reference: Jarrow & Turnbull (1995), Duffie & Singleton (1999)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class HazardRateModel:
    """
    Piecewise-constant hazard rate credit model.

    Calibrated to CDS spread term structure.
    """

    def survival_probability(
        self,
        T: float,
        hazard_rates: dict,
    ) -> float:
        """
        Q(T) = exp(-Σ λ_i × Δt_i) over each piecewise interval.

        hazard_rates: {maturity_years: annualized_hazard_rate}
                      e.g. {1.0: 0.02, 3.0: 0.025, 5.0: 0.03}
        """
        tenors = sorted(hazard_rates.keys())
        rates = [hazard_rates[t] for t in tenors]

        # Add t=0 as boundary
        boundaries = [0.0] + tenors
        log_surv = 0.0
        t_prev = 0.0
        lam_prev = rates[0]

        for i, t_next in enumerate(tenors):
            lam = rates[i]
            dt = min(t_next, T) - t_prev
            if dt <= 0:
                break
            log_surv -= lam * dt
            t_prev = t_next
            if t_prev >= T:
                break

        # If T beyond last tenor, use last hazard rate
        if t_prev < T:
            lam_last = rates[-1]
            log_surv -= lam_last * (T - t_prev)

        return float(np.exp(log_surv))

    def default_probability(
        self,
        T1: float,
        T2: float,
        hazard_rates: dict,
    ) -> float:
        """P(default between T1 and T2) = Q(T1) - Q(T2)."""
        return float(self.survival_probability(T1, hazard_rates)
                     - self.survival_probability(T2, hazard_rates))

    def hazard_rate_from_spread(
        self,
        spread: float,
        recovery: float = 0.40,
    ) -> float:
        """
        Approximate constant hazard rate from CDS spread.

        λ ≈ spread / (1 - R)

        Exact under flat hazard rate curve with continuous payment.
        Widely used as a first approximation.
        """
        return float(spread / (1 - recovery))

    def credit_curve_from_cds(
        self,
        cds_spreads: dict,
        recovery: float = 0.40,
        discount_curve_fn=None,
    ) -> dict:
        """
        Bootstrap piecewise-constant hazard rates from CDS spread term structure.

        cds_spreads: {maturity: spread_decimal}
                     e.g. {1.0: 0.005, 3.0: 0.0075, 5.0: 0.010, 10.0: 0.012}

        Method: iteratively solve for λ_i such that each CDS is at par
        (protection leg PV = premium leg PV).
        """
        tenors = sorted(cds_spreads.keys())
        spreads = [cds_spreads[t] for t in tenors]

        if discount_curve_fn is None:
            # Default: flat 5% discount curve
            def discount_curve_fn(t):
                return np.exp(-0.05 * t)

        hazard_rates = {}
        maturities_out = []
        hazard_out = []
        surv_out = []
        pd_cumulative = []

        t_prev = 0.0
        lam_prev = spreads[0] / (1 - recovery)

        for i, T in enumerate(tenors):
            s = spreads[i]
            # Build payment dates (quarterly)
            n_pay = max(1, int(round(T * 4)))
            pay_times = np.array([(j + 1) / 4 for j in range(n_pay) if (j + 1) / 4 <= T])
            if len(pay_times) == 0:
                pay_times = np.array([T])

            def _cds_npv(lam_new, t_prev=t_prev, lam_prev=lam_prev):
                # Build hazard rate dict with new segment
                hr = dict(hazard_rates)
                hr[T] = float(lam_new)

                premium_pv = 0.0
                protection_pv = 0.0
                q_prev = 1.0

                for k, t in enumerate(pay_times):
                    df = float(discount_curve_fn(t))
                    q = self.survival_probability(t, hr)
                    dt = pay_times[k] - (pay_times[k - 1] if k > 0 else 0.0)
                    premium_pv += s * df * q * dt
                    # Default in this period
                    q_t_prev = self.survival_probability(
                        pay_times[k - 1] if k > 0 else 0.0, hr
                    )
                    protection_pv += (1 - recovery) * df * (q_t_prev - q)

                return premium_pv - protection_pv

            # Solve for lam_new
            from scipy.optimize import brentq
            try:
                lam_new = brentq(
                    lambda l: _cds_npv(l),
                    max(spreads[i] / (1 - recovery) * 0.1, 1e-6),
                    spreads[i] / (1 - recovery) * 10,
                    xtol=1e-8,
                )
            except Exception:
                lam_new = spreads[i] / (1 - recovery)

            hazard_rates[T] = float(lam_new)
            maturities_out.append(float(T))
            hazard_out.append(float(lam_new))
            q_T = self.survival_probability(T, hazard_rates)
            surv_out.append(float(q_T))
            pd_cumulative.append(float(1 - q_T))
            t_prev = T
            lam_prev = lam_new

        # Marginal default probabilities
        pd_marginal = [
            pd_cumulative[0],
            *[pd_cumulative[i] - pd_cumulative[i - 1] for i in range(1, len(pd_cumulative))],
        ]

        return {
            "maturities": maturities_out,
            "hazard_rates": hazard_out,
            "survival_probabilities": surv_out,
            "default_probabilities": pd_marginal,
            "cumulative_default_probabilities": pd_cumulative,
            "recovery": float(recovery),
        }
