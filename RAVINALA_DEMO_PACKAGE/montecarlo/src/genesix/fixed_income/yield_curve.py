"""
Yield curve construction and analysis.

The yield curve is the MOST IMPORTANT object in fixed income.
It tells you the price of money at every maturity.

Construction methods:
1. Bootstrap: extract zero rates from bond prices (exact fit)
2. Nelson-Siegel: parametric model (4 parameters, smooth)
3. Nelson-Siegel-Svensson: extended (6 parameters)
4. Cubic spline: interpolation between known points
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize, brentq
from scipy.interpolate import CubicSpline
from typing import Callable, Optional


class YieldCurveBuilder:
    """Build and analyze yield curves from market instruments."""

    def bootstrap(self, instruments: list[dict]) -> dict:
        """
        Bootstrap zero-coupon curve from market instruments.

        Instruments can be:
        - deposit: {'type': 'deposit', 'maturity': 0.25, 'rate': 0.053}
        - swap: {'type': 'swap', 'maturity': 2.0, 'rate': 0.045}
        - bond: {'type': 'bond', 'maturity': 5.0, 'coupon': 0.04, 'price': 99.5}

        Method: iteratively solve for discount factors that reprice each instrument.
        Between points: log-linear interpolation on discount factors.
        """
        # Sort by maturity
        instr = sorted(instruments, key=lambda x: x["maturity"])
        maturities = []
        discount_factors = []

        # Start: DF(0) = 1
        maturities.append(0.0)
        discount_factors.append(1.0)

        for inst in instr:
            T = inst["maturity"]
            itype = inst["type"]

            if itype == "deposit":
                # Simple interest: DF = 1 / (1 + r * T)
                r = inst["rate"]
                df = 1.0 / (1 + r * T)
                maturities.append(T)
                discount_factors.append(df)

            elif itype == "swap":
                # Swap rate: fixed_rate × Σ DF(T_i) × δ_i = 1 - DF(T)
                # For simplicity: semi-annual coupon frequency
                r = inst["rate"]
                freq = inst.get("frequency", 2)
                n = int(round(T * freq))
                payment_times = np.array([(i + 1) / freq for i in range(n)])

                def interp_df(t):
                    return float(np.exp(np.interp(t, maturities, np.log(np.array(discount_factors) + 1e-300))))

                # Known DFs for all but last payment date
                coupon = r / freq
                pv_known = sum(coupon * interp_df(ti) for ti in payment_times[:-1])

                # Solve for DF at T: coupon * DF_T + DF_T = 1 - pv_known
                df_T = (1.0 - pv_known) / (1.0 + coupon)
                maturities.append(T)
                discount_factors.append(float(df_T))

            elif itype == "bond":
                # Bond: Σ C × DF(T_i) + F × DF(T) = price
                coupon_rate = inst["coupon"]
                price = inst["price"]
                face = inst.get("face", 100.0)
                freq = inst.get("frequency", 2)
                n = int(round(T * freq))
                payment_times = np.array([(i + 1) / freq for i in range(n)])
                coupon = face * coupon_rate / freq

                def interp_df(t):
                    return float(np.exp(np.interp(t, maturities, np.log(np.array(discount_factors) + 1e-300))))

                # Sum known coupon PVs (all but final)
                pv_known = sum(coupon * interp_df(ti) for ti in payment_times[:-1])

                # Solve: coupon * DF_T + face * DF_T = price - pv_known
                df_T = (price - pv_known) / (face + coupon)
                maturities.append(T)
                discount_factors.append(float(max(df_T, 1e-8)))

        maturities = np.array(maturities)
        discount_factors = np.array(discount_factors)

        # Sort (in case of duplicate/out-of-order)
        idx = np.argsort(maturities)
        maturities = maturities[idx]
        discount_factors = discount_factors[idx]

        # Zero rates from discount factors
        log_dfs = np.log(discount_factors + 1e-300)
        zero_rates = np.where(
            maturities > 0,
            -log_dfs / maturities,
            0.0,
        )

        # Forward rates (instantaneous): d(-ln P)/dT
        forward_rates = np.gradient(-log_dfs, maturities)
        forward_rates = np.clip(forward_rates, 0.0, 1.0)

        def interpolator(T_query):
            log_df = np.interp(T_query, maturities, log_dfs)
            if np.ndim(T_query) == 0:
                t = float(T_query)
                return float(-log_df / t) if t > 0 else float(zero_rates[0])
            arr = np.asarray(T_query, dtype=float)
            return np.where(arr > 0, -log_df / arr, zero_rates[0])

        return {
            "maturities": maturities,
            "zero_rates": zero_rates,
            "discount_factors": discount_factors,
            "forward_rates": forward_rates,
            "interpolator": interpolator,
        }

    def nelson_siegel(
        self,
        maturities: np.ndarray,
        zero_rates: np.ndarray,
    ) -> dict:
        """
        Fit Nelson-Siegel model to observed zero rates.

        r(T) = β₀ + β₁(1-e^{-T/τ})/(T/τ) + β₂((1-e^{-T/τ})/(T/τ) - e^{-T/τ})

        β₀ = long-term level (asymptote)
        β₁ = short-term slope (positive=normal curve, negative=inverted)
        β₂ = medium-term curvature/hump
        τ  = decay factor
        """
        maturities = np.asarray(maturities, dtype=float)
        zero_rates = np.asarray(zero_rates, dtype=float)

        def _ns_rate(T, b0, b1, b2, tau):
            x = T / tau
            f1 = (1 - np.exp(-x)) / x
            f2 = f1 - np.exp(-x)
            return b0 + b1 * f1 + b2 * f2

        def _objective(params):
            b0, b1, b2, tau = params
            if tau <= 0 or b0 <= 0:
                return 1e10
            fitted = _ns_rate(maturities, b0, b1, b2, tau)
            return float(np.sum((fitted - zero_rates) ** 2))

        # Initial guess
        b0_init = float(zero_rates[-1])
        b1_init = float(zero_rates[0] - zero_rates[-1])
        b2_init = 0.0
        tau_init = 2.0
        x0 = [b0_init, b1_init, b2_init, tau_init]

        result = minimize(_objective, x0, method="Nelder-Mead",
                          options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 10000})

        b0, b1, b2, tau = result.x
        fitted_rates = _ns_rate(maturities, b0, b1, b2, tau)
        residuals = zero_rates - fitted_rates
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        def curve_fn(T):
            T = np.asarray(T, dtype=float)
            T = np.maximum(T, 1e-6)
            return _ns_rate(T, b0, b1, b2, tau)

        return {
            "beta0": float(b0),
            "beta1": float(b1),
            "beta2": float(b2),
            "tau": float(tau),
            "fitted_rates": fitted_rates,
            "residuals": residuals,
            "rmse": float(rmse),
            "level": float(b0),
            "slope": float(-b1),
            "curvature": float(b2),
            "curve_fn": curve_fn,
        }

    def nelson_siegel_svensson(
        self,
        maturities: np.ndarray,
        zero_rates: np.ndarray,
    ) -> dict:
        """
        Extended Nelson-Siegel (Svensson 1994) with 2 humps (6 parameters).

        r(T) = β₀ + β₁×f₁(T,τ₁) + β₂×f₂(T,τ₁) + β₃×f₂(T,τ₂)
        """
        maturities = np.asarray(maturities, dtype=float)
        zero_rates = np.asarray(zero_rates, dtype=float)

        def _nss_rate(T, b0, b1, b2, b3, tau1, tau2):
            x1 = T / tau1
            x2 = T / tau2
            f1 = (1 - np.exp(-x1)) / x1
            f2 = f1 - np.exp(-x1)
            f3 = (1 - np.exp(-x2)) / x2 - np.exp(-x2)
            return b0 + b1 * f1 + b2 * f2 + b3 * f3

        def _objective(params):
            b0, b1, b2, b3, tau1, tau2 = params
            if tau1 <= 0 or tau2 <= 0 or b0 <= 0:
                return 1e10
            fitted = _nss_rate(maturities, b0, b1, b2, b3, tau1, tau2)
            return float(np.sum((fitted - zero_rates) ** 2))

        # NS fit as starting point
        ns = self.nelson_siegel(maturities, zero_rates)
        x0 = [ns["beta0"], ns["beta1"], ns["beta2"], 0.0, ns["tau"], ns["tau"] * 2]

        result = minimize(_objective, x0, method="Nelder-Mead",
                          options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 20000})

        b0, b1, b2, b3, tau1, tau2 = result.x
        fitted_rates = _nss_rate(maturities, b0, b1, b2, b3, tau1, tau2)
        residuals = zero_rates - fitted_rates
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        def curve_fn(T):
            T = np.asarray(T, dtype=float)
            T = np.maximum(T, 1e-6)
            return _nss_rate(T, b0, b1, b2, b3, tau1, tau2)

        return {
            "beta0": float(b0), "beta1": float(b1), "beta2": float(b2),
            "beta3": float(b3), "tau1": float(tau1), "tau2": float(tau2),
            "fitted_rates": fitted_rates,
            "residuals": residuals,
            "rmse": float(rmse),
            "curve_fn": curve_fn,
        }

    def forward_rate(self, T1: float, T2: float, curve_fn: Callable) -> float:
        """
        Forward rate between T1 and T2.

        f(T1,T2) = [r(T2)*T2 - r(T1)*T1] / (T2 - T1)

        The rate locked in today for borrowing between T1 and T2.
        """
        r1 = float(curve_fn(T1))
        r2 = float(curve_fn(T2))
        return float((r2 * T2 - r1 * T1) / (T2 - T1))

    def curve_analysis(
        self,
        maturities: np.ndarray,
        zero_rates: np.ndarray,
    ) -> dict:
        """
        Full yield curve analysis: shape, slope, curvature, recession signal.
        """
        maturities = np.asarray(maturities, dtype=float)
        zero_rates = np.asarray(zero_rates, dtype=float)

        def _get_rate(T):
            return float(np.interp(T, maturities, zero_rates))

        level = float(np.mean(zero_rates))
        slope = _get_rate(10.0) - _get_rate(2.0)  # 10Y - 2Y
        curvature = 2 * _get_rate(5.0) - _get_rate(2.0) - _get_rate(10.0)

        if slope > 0.005:
            shape = "normal"
        elif slope < -0.005:
            shape = "inverted"
        elif abs(slope) <= 0.005 and curvature > 0.002:
            shape = "humped"
        else:
            shape = "flat"

        # Inversion points (where forward rate < 0 or curve inverts locally)
        inversion_points = []
        for i in range(len(maturities) - 1):
            if zero_rates[i] > zero_rates[i + 1]:
                inversion_points.append(float(maturities[i]))

        recession_signal = slope < 0.0

        # Approximate recession probability from 10Y-2Y spread (probit-like)
        # Based on historical Fed research: P(recession) ≈ Φ(-0.53 - 0.7 * spread * 100)
        from scipy.stats import norm
        recession_prob = float(norm.cdf(-0.53 - 0.7 * slope * 100))

        # Nelson-Siegel for parameters
        try:
            ns = self.nelson_siegel(maturities, zero_rates)
            ns_params = {"beta0": ns["beta0"], "beta1": ns["beta1"],
                         "beta2": ns["beta2"], "tau": ns["tau"]}
        except Exception:
            ns_params = {}

        return {
            "level": float(level),
            "slope": float(slope),
            "curvature": float(curvature),
            "shape": shape,
            "inversion_points": inversion_points,
            "recession_signal": recession_signal,
            "recession_probability": float(recession_prob),
            "nelson_siegel_params": ns_params,
        }
