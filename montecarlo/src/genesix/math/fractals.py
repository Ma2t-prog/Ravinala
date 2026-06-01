"""
Fractal analysis and chaos theory applied to financial markets.

Benoît Mandelbrot (1963) showed financial returns are NOT Gaussian:
they have fat tails, long memory, and self-similar structure across time scales.

Hurst exponent (H):
  H > 0.5: persistent (trending) — momentum strategies work
  H = 0.5: random walk (no memory) — efficient market
  H < 0.5: anti-persistent (mean-reverting) — mean-reversion strategies work

Reference: Hurst (1951), Mandelbrot (1963, 1997), Peters (1994),
           Rosenstein et al. (1993)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional, Tuple


class FractalAnalyzer:
    """Fractal and chaos analysis for financial time series."""

    def hurst_exponent_rs(self, series: np.ndarray) -> dict:
        """
        Classical R/S (Rescaled Range) analysis for Hurst exponent.

        Steps:
        1. Divide series into sub-periods of increasing length n
        2. For each n: compute R(n) = max(cum.dev.) - min(cum.dev.), S(n) = std
        3. R/S(n) = R(n) / S(n), averaged over all sub-periods of length n
        4. Regress log(R/S) on log(n) → slope = H

        E[R/S] ~ C × n^H
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        n = len(series)

        ns = []
        rs_means = []

        min_n = 10
        max_n = n // 2

        for sub_len in range(min_n, max_n + 1, max(1, (max_n - min_n) // 20)):
            n_subs = n // sub_len
            if n_subs < 2:
                continue

            rs_list = []
            for i in range(n_subs):
                chunk = series[i * sub_len : (i + 1) * sub_len]
                mean_c = np.mean(chunk)
                cum_dev = np.cumsum(chunk - mean_c)
                R = np.max(cum_dev) - np.min(cum_dev)
                S = np.std(chunk, ddof=1)
                if S > 0:
                    rs_list.append(R / S)

            if rs_list:
                ns.append(sub_len)
                rs_means.append(np.mean(rs_list))

        if len(ns) < 4:
            return {"hurst_exponent": 0.5, "error": "insufficient data"}

        log_n = np.log(ns)
        log_rs = np.log(rs_means)
        coeffs = np.polyfit(log_n, log_rs, 1)
        H = float(coeffs[0])
        r2 = float(np.corrcoef(log_n, log_rs)[0, 1] ** 2)

        return {
            "hurst_exponent": H,
            "interpretation": self._interpret_hurst(H),
            "regression_r2": r2,
            "log_n_values": [float(x) for x in log_n],
            "log_rs_values": [float(x) for x in log_rs],
            "strategy_implication": self._strategy_implication(H),
        }

    def hurst_exponent_dfa(self, series: np.ndarray) -> dict:
        """
        Detrended Fluctuation Analysis (DFA) — more robust than R/S.

        Steps:
        1. Cumulative sum: Y(k) = Σ(x_i - x̄)
        2. Divide into non-overlapping segments of length n
        3. Detrend each segment (linear fit)
        4. F(n) = RMS of residuals
        5. Regress log(F(n)) on log(n) → slope α ≈ H
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        N = len(series)

        Y = np.cumsum(series - np.mean(series))

        scales = np.unique(np.logspace(1, np.log10(N // 4), num=20, dtype=int))
        scales = scales[scales >= 4]

        F_vals = []
        valid_scales = []

        for scale in scales:
            n_segs = N // scale
            if n_segs < 2:
                continue

            fluctuations = []
            for seg in range(n_segs):
                y_seg = Y[seg * scale : (seg + 1) * scale]
                x_seg = np.arange(scale)
                coeffs = np.polyfit(x_seg, y_seg, 1)
                trend = np.polyval(coeffs, x_seg)
                fluctuations.append(np.mean((y_seg - trend) ** 2))

            F = np.sqrt(np.mean(fluctuations))
            if F > 0:
                F_vals.append(F)
                valid_scales.append(scale)

        if len(valid_scales) < 4:
            return {"hurst_exponent": 0.5, "error": "insufficient data for DFA"}

        log_s = np.log(valid_scales)
        log_F = np.log(F_vals)
        coeffs = np.polyfit(log_s, log_F, 1)
        H = float(coeffs[0])
        r2 = float(np.corrcoef(log_s, log_F)[0, 1] ** 2)

        # Check for crossover
        mid = len(valid_scales) // 2
        H_short = float(np.polyfit(log_s[:mid], log_F[:mid], 1)[0]) if mid > 2 else None
        H_long = float(np.polyfit(log_s[mid:], log_F[mid:], 1)[0]) if len(valid_scales) - mid > 2 else None
        crossover = (
            H_short is not None
            and H_long is not None
            and abs(H_short - H_long) > 0.1
        )

        return {
            "hurst_exponent": H,
            "interpretation": self._interpret_hurst(H),
            "regression_r2": r2,
            "crossover_detected": crossover,
            "short_range_hurst": H_short,
            "long_range_hurst": H_long,
            "strategy_implication": self._strategy_implication(H),
        }

    def fractal_dimension(self, series: np.ndarray) -> dict:
        """
        Fractal dimension D = 2 - H (for self-affine series).

        D = 1.0: smooth line (perfectly trending)
        D = 1.5: Brownian motion (random walk)
        D = 2.0: fills the plane (extremely noisy/chaotic)
        """
        h_result = self.hurst_exponent_dfa(series)
        H = h_result.get("hurst_exponent", 0.5)
        D = 2.0 - H

        if D < 1.2:
            roughness = "smooth"
        elif D < 1.5:
            roughness = "moderate"
        elif D < 1.8:
            roughness = "rough"
        else:
            roughness = "very_rough"

        return {
            "fractal_dimension": float(D),
            "hurst_exponent": float(H),
            "roughness": roughness,
        }

    def multifractal_spectrum(
        self,
        series: np.ndarray,
        q_range: Tuple[float, float] = (-5, 5),
        n_q: int = 21,
    ) -> dict:
        """
        Multi-fractal Detrended Fluctuation Analysis (MF-DFA).

        For each moment order q, compute generalised Hurst exponent H(q):
        F_q(n) = [mean of F(n,s)^q]^{1/q} ~ n^{H(q)}

        Wide spectrum of H(q) → strong multifractality.
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        N = len(series)
        Y = np.cumsum(series - np.mean(series))

        q_values = np.linspace(q_range[0], q_range[1], n_q)
        scales = np.unique(np.logspace(1, np.log10(N // 4), num=15, dtype=int))
        scales = scales[scales >= 4]

        h_q = []

        for q in q_values:
            F_q_vals = []
            for scale in scales:
                n_segs = N // scale
                if n_segs < 2:
                    continue

                flucts = []
                for seg in range(n_segs):
                    y_seg = Y[seg * scale : (seg + 1) * scale]
                    x_seg = np.arange(scale)
                    coeffs = np.polyfit(x_seg, y_seg, 1)
                    residual = y_seg - np.polyval(coeffs, x_seg)
                    f2 = np.mean(residual**2)
                    flucts.append(max(f2, 1e-300))

                if q == 0:
                    Fq = np.exp(0.5 * np.mean(np.log(flucts)))
                else:
                    Fq = np.mean(np.array(flucts) ** (q / 2)) ** (1 / q)

                F_q_vals.append(Fq)

            if len(F_q_vals) >= 3 and len(scales[: len(F_q_vals)]) >= 3:
                log_s = np.log(scales[: len(F_q_vals)])
                log_Fq = np.log(np.array(F_q_vals))
                slope = np.polyfit(log_s, log_Fq, 1)[0]
                h_q.append(float(slope))
            else:
                h_q.append(0.5)

        # Multifractal spectrum via Legendre transform
        tau_q = [q * h_q[i] - 1 for i, q in enumerate(q_values)]
        q_arr = np.array(q_values)
        h_arr = np.array(h_q)
        tau_arr = np.array(tau_q)

        # α = dτ/dq, f(α) = qα - τ
        alpha_vals = np.gradient(tau_arr, q_arr).tolist()
        f_alpha = [float(q_arr[i] * alpha_vals[i] - tau_arr[i]) for i in range(len(q_arr))]

        spectrum_width = max(alpha_vals) - min(alpha_vals)

        return {
            "q_values": q_values.tolist(),
            "h_q": h_q,
            "tau_q": tau_q,
            "alpha_values": alpha_vals,
            "f_alpha": f_alpha,
            "spectrum_width": float(spectrum_width),
            "interpretation": (
                f"Spectrum width = {spectrum_width:.3f}. "
                + (
                    "Strong multifractality — extreme events have fundamentally "
                    "different dynamics than normal moves."
                    if spectrum_width > 0.3
                    else "Weak multifractality — close to monofractal (near-GBM behaviour)."
                )
            ),
        }

    def compare_to_gbm(self, returns: np.ndarray) -> dict:
        """
        Compare real return series against GBM predictions.

        Tests: Hurst, kurtosis, autocorrelation of |returns|, scaling.
        """
        if isinstance(returns, pd.Series):
            returns = returns.values
        returns = np.asarray(returns, dtype=float)

        violations = []

        # 1. Hurst exponent
        h_res = self.hurst_exponent_dfa(returns)
        H = h_res.get("hurst_exponent", 0.5)
        h_dev = abs(H - 0.5)
        violations.append({
            "test": "Hurst exponent",
            "expected": 0.5,
            "observed": round(H, 4),
            "violated": h_dev > 0.05,
            "implication": (
                f"Trend persistence detected (H={H:.3f})."
                if H > 0.55
                else f"Anti-persistence detected (H={H:.3f}) — mean-reversion present."
                if H < 0.45
                else "Consistent with random walk."
            ),
        })

        # 2. Kurtosis
        from scipy.stats import kurtosis as scipy_kurtosis
        kurt = float(scipy_kurtosis(returns, fisher=False))  # excess + 3
        violations.append({
            "test": "Kurtosis (fat tails)",
            "expected": 3.0,
            "observed": round(kurt, 2),
            "violated": kurt > 4.0,
            "implication": (
                f"Fat tails detected (kurtosis={kurt:.1f} vs 3.0 normal). "
                "Extreme events are more likely than GBM predicts."
                if kurt > 4.0
                else "Kurtosis consistent with GBM."
            ),
        })

        # 3. Volatility clustering (autocorrelation of |returns|)
        abs_returns = np.abs(returns)
        acf1 = float(np.corrcoef(abs_returns[:-1], abs_returns[1:])[0, 1])
        violations.append({
            "test": "Volatility clustering (ACF of |r|)",
            "expected": 0.0,
            "observed": round(acf1, 4),
            "violated": abs(acf1) > 0.05,
            "implication": (
                f"Volatility clustering present (ACF₁={acf1:.3f}). "
                "High-vol days follow high-vol days — GARCH/Heston models needed."
                if abs(acf1) > 0.05
                else "No significant volatility clustering."
            ),
        })

        # 4. Skewness
        from scipy.stats import skew as scipy_skew
        sk = float(scipy_skew(returns))
        violations.append({
            "test": "Skewness",
            "expected": 0.0,
            "observed": round(sk, 4),
            "violated": abs(sk) > 0.3,
            "implication": (
                f"Negative skew (sk={sk:.3f}) — crash risk dominates."
                if sk < -0.3
                else f"Positive skew (sk={sk:.3f})."
                if sk > 0.3
                else "Skewness consistent with GBM."
            ),
        })

        n_violated = sum(1 for v in violations if v["violated"])
        if n_violated >= 3:
            adequacy = "poor"
            recommendation = "Consider jump-diffusion or stochastic volatility models."
        elif n_violated == 2:
            adequacy = "fair"
            recommendation = "GBM is approximate; be cautious with tail risk estimates."
        else:
            adequacy = "good"
            recommendation = "GBM is a reasonable approximation for this asset."

        return {
            "gbm_assumption_violations": violations,
            "n_violations": n_violated,
            "overall_gbm_adequacy": adequacy,
            "recommended_model": recommendation,
        }

    @staticmethod
    def _interpret_hurst(H: float) -> str:
        if H > 0.55:
            return "persistent"
        elif H < 0.45:
            return "anti_persistent"
        else:
            return "random_walk"

    @staticmethod
    def _strategy_implication(H: float) -> str:
        if H > 0.55:
            return (
                f"Series shows persistence (H={H:.3f}) — "
                "momentum/trend-following strategies are favoured."
            )
        elif H < 0.45:
            return (
                f"Series is anti-persistent (H={H:.3f}) — "
                "mean-reversion strategies are favoured."
            )
        else:
            return (
                f"Series is close to random walk (H={H:.3f}) — "
                "no clear directional edge."
            )


class LyapunovExponent:
    """
    Lyapunov exponent — measures chaos in a dynamical system.

    λ > 0: nearby trajectories diverge exponentially → CHAOS
    λ = 0: nearby trajectories stay close → PERIODIC
    λ < 0: nearby trajectories converge → STABLE

    Applied to finance: positive λ gives an estimate of the
    prediction horizon: ~1/λ (beyond this, predictions are meaningless).

    Reference: Rosenstein, Collins & De Luca (1993).
    """

    def estimate(
        self,
        series: np.ndarray,
        embedding_dim: int = 5,
        delay: int = 1,
        max_iter: int = 50,
    ) -> dict:
        """
        Estimate largest Lyapunov exponent via Rosenstein et al. (1993).

        Steps:
        1. Reconstruct state space via time-delay embedding
        2. For each point, find nearest neighbor
        3. Track log-divergence over time
        4. Slope of mean log-divergence vs. time = λ
        """
        if isinstance(series, pd.Series):
            series = series.values
        series = np.asarray(series, dtype=float)
        N = len(series)

        # Build embedded state space: X[i] = [s[i], s[i+τ], ..., s[i+(m-1)τ]]
        M = N - (embedding_dim - 1) * delay
        if M < 20:
            return {"lyapunov_exponent": np.nan, "error": "Series too short for embedding"}

        embedded = np.array(
            [series[i : i + embedding_dim * delay : delay] for i in range(M)]
        )

        # Find nearest neighbors (excluding close temporal neighbors)
        min_sep = max(embedding_dim, 5)
        lyap_sum = np.zeros(max_iter)
        count = np.zeros(max_iter, dtype=int)

        for i in range(M):
            dists = np.sqrt(np.sum((embedded - embedded[i]) ** 2, axis=1))
            dists[max(0, i - min_sep) : min(M, i + min_sep + 1)] = np.inf
            j = int(np.argmin(dists))

            for k in range(max_iter):
                i_k = i + k
                j_k = j + k
                if i_k >= M or j_k >= M:
                    break
                d = np.linalg.norm(embedded[i_k] - embedded[j_k])
                if d > 0:
                    lyap_sum[k] += np.log(d)
                    count[k] += 1

        # Average log divergence
        valid = count > 0
        if not np.any(valid):
            return {"lyapunov_exponent": np.nan, "error": "Could not compute divergence"}

        mean_log_div = lyap_sum[valid] / count[valid]
        time_axis = np.where(valid)[0]

        if len(time_axis) < 3:
            return {"lyapunov_exponent": np.nan, "error": "Insufficient valid points"}

        # Fit slope to first half (before saturation)
        fit_len = max(3, len(time_axis) // 2)
        slope = float(np.polyfit(time_axis[:fit_len], mean_log_div[:fit_len], 1)[0])

        is_chaotic = slope > 0
        prediction_horizon = float(1 / slope) if slope > 0 else None

        return {
            "lyapunov_exponent": slope,
            "is_chaotic": is_chaotic,
            "prediction_horizon_steps": prediction_horizon,
            "interpretation": (
                f"Positive Lyapunov exponent ({slope:.4f}) — chaotic dynamics detected. "
                f"Prediction accuracy degrades significantly beyond ~{prediction_horizon:.0f} steps. "
                "Momentum strategies may work short-term but are unreliable long-term."
                if is_chaotic
                else f"Non-positive Lyapunov exponent ({slope:.4f}) — "
                "series is not chaotic; longer-range prediction may be feasible."
            ),
        }
