"""
Random Matrix Theory for correlation matrix cleaning.

Problem: estimated correlation matrices from finite samples contain NOISE.
With N assets and T observations, if N/T is not small, most eigenvalues
are pure noise and don't reflect true correlations.

Solution: Marchenko-Pastur law gives the eigenvalue distribution for a
RANDOM correlation matrix. Any eigenvalue within this distribution is
noise. Only eigenvalues ABOVE the upper MP bound carry real information.

Used at Renaissance, Two Sigma, and every serious quant fund to clean
correlation matrices before portfolio optimization. Without it, optimized
portfolios are dominated by noise.

Reference: Marchenko & Pastur (1967), Laloux et al. (1999), Plerou et al. (2002)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


class CorrelationCleaner:
    """Clean correlation matrices using Random Matrix Theory."""

    def marchenko_pastur_bounds(self, N: int, T: int) -> dict:
        """
        Compute Marchenko-Pastur eigenvalue bounds.

        For a random matrix with N assets and T observations:
        q = N / T  (must be ≤ 1 for meaningful results)

        λ_max = (1 + √q)²   ← upper bound: eigenvalues above this = SIGNAL
        λ_min = (1 - √q)²   ← lower bound

        The bulk of eigenvalues of a random N×T correlation matrix
        falls in [λ_min, λ_max]. These are NOISE.

        Returns:
            {
                'q_ratio': N/T,
                'lambda_min': float,
                'lambda_max': float,
                'theoretical_density': callable,
                'interpretation': str,
            }
        """
        q = N / T
        if q > 1:
            raise ValueError(f"q = N/T = {q:.2f} > 1. Need more observations than assets.")

        sqrt_q = np.sqrt(q)
        lam_max = (1 + sqrt_q) ** 2
        lam_min = (1 - sqrt_q) ** 2

        def mp_density(lam: np.ndarray) -> np.ndarray:
            """Marchenko-Pastur PDF."""
            lam = np.asarray(lam, dtype=float)
            in_support = (lam >= lam_min) & (lam <= lam_max)
            rho = np.zeros_like(lam)
            l = lam[in_support]
            rho[in_support] = (
                np.sqrt(np.maximum((lam_max - l) * (l - lam_min), 0))
                / (2 * np.pi * q * l)
            )
            return rho

        return {
            "q_ratio": float(q),
            "lambda_min": float(lam_min),
            "lambda_max": float(lam_max),
            "theoretical_density": mp_density,
            "interpretation": (
                f"With {N} assets and {T} observations (q={q:.2f}), "
                f"eigenvalues in [{lam_min:.3f}, {lam_max:.3f}] are "
                f"indistinguishable from noise. "
                f"Only eigenvalues > {lam_max:.3f} represent real market structure."
            ),
        }

    def clean_correlation_matrix(
        self,
        returns: pd.DataFrame,
        method: str = "clipping",
    ) -> dict:
        """
        Clean a correlation matrix by removing noise eigenvalues.

        Methods:
        - 'clipping': replace noise eigenvalues with their mean (preserve trace)
        - 'shrinkage': Ledoit-Wolf shrinkage toward identity
        - 'targeted': replace noise eigenvalues with constant-correlation target

        Returns full analysis including signal/noise decomposition.
        """
        N = returns.shape[1]
        T = returns.shape[0]

        C_raw = returns.corr()
        C_arr = C_raw.values

        eigenvalues, eigenvectors = np.linalg.eigh(C_arr)
        # eigh returns ascending order; reverse to descending
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        mp = self.marchenko_pastur_bounds(N, T)
        lam_max_noise = mp["lambda_max"]

        noise_mask = eigenvalues <= lam_max_noise
        signal_mask = ~noise_mask
        n_signal = int(np.sum(signal_mask))
        n_noise = int(np.sum(noise_mask))

        if method == "clipping":
            lam_clean = eigenvalues.copy()
            if n_noise > 0:
                # Replace noise eigenvalues with their mean (preserves trace)
                noise_mean = float(np.mean(eigenvalues[noise_mask]))
                lam_clean[noise_mask] = noise_mean
            C_clean_arr = eigenvectors @ np.diag(lam_clean) @ eigenvectors.T

        elif method == "shrinkage":
            # Ledoit-Wolf analytic shrinkage
            alpha = self._ledoit_wolf_alpha(C_arr, T)
            C_clean_arr = alpha * np.eye(N) + (1 - alpha) * C_arr
            lam_clean = np.linalg.eigvalsh(C_clean_arr)[::-1]

        elif method == "targeted":
            # Replace noise with constant-correlation target
            avg_corr = (np.sum(C_arr) - N) / (N * (N - 1))
            target = avg_corr * np.ones((N, N)) + (1 - avg_corr) * np.eye(N)
            lam_clean = eigenvalues.copy()
            if n_noise > 0:
                target_vals = np.linalg.eigvalsh(target)[::-1]
                lam_clean[noise_mask] = target_vals[noise_mask] if n_noise <= len(target_vals) else 0.0
            C_clean_arr = eigenvectors @ np.diag(lam_clean) @ eigenvectors.T

        else:
            raise ValueError(f"Unknown method: {method}. Use 'clipping', 'shrinkage', or 'targeted'.")

        # Rescale to unit diagonal
        diag_sqrt_inv = np.diag(1.0 / np.sqrt(np.diag(C_clean_arr)))
        C_clean_arr = diag_sqrt_inv @ C_clean_arr @ diag_sqrt_inv
        np.fill_diagonal(C_clean_arr, 1.0)
        C_clean_arr = 0.5 * (C_clean_arr + C_clean_arr.T)

        C_clean = pd.DataFrame(C_clean_arr, index=C_raw.index, columns=C_raw.columns)

        var_signal = float(np.sum(eigenvalues[signal_mask]) / np.sum(eigenvalues) * 100)
        cond_raw = float(np.max(eigenvalues) / max(np.min(eigenvalues), 1e-10))
        lam_clean_vals = np.linalg.eigvalsh(C_clean_arr)
        cond_clean = float(np.max(lam_clean_vals) / max(np.min(lam_clean_vals), 1e-10))

        return {
            "original_matrix": C_raw,
            "cleaned_matrix": C_clean,
            "n_signal_eigenvalues": n_signal,
            "n_noise_eigenvalues": n_noise,
            "eigenvalues_original": eigenvalues,
            "eigenvalues_cleaned": np.sort(lam_clean)[::-1],
            "mp_upper_bound": lam_max_noise,
            "explained_variance_signal_pct": var_signal,
            "condition_number_original": cond_raw,
            "condition_number_cleaned": cond_clean,
            "method": method,
            "interpretation": (
                f"Found {n_signal} signal eigenvalue(s) out of {N}. "
                f"The largest likely corresponds to the market factor. "
                f"Signal eigenvalues explain {var_signal:.1f}% of total variance. "
                f"Condition number: {cond_raw:.1f} → {cond_clean:.1f} "
                f"(lower is more stable for portfolio optimization)."
            ),
        }

    def compare_optimization(
        self,
        returns: pd.DataFrame,
        target_return: Optional[float] = None,
        test_frac: float = 0.3,
    ) -> dict:
        """
        Compare portfolio optimization: raw vs. cleaned correlation matrix.

        Shows that cleaned matrix produces:
        - More stable weights (less extreme positions)
        - Better out-of-sample Sharpe ratio
        - Lower turnover when re-estimated
        """
        N = len(returns.columns)
        split = int(len(returns) * (1 - test_frac))
        train = returns.iloc[:split]
        test = returns.iloc[split:]

        def _min_vol_weights(cov: np.ndarray) -> np.ndarray:
            """Minimum variance portfolio weights."""
            try:
                inv_cov = np.linalg.inv(cov + 1e-8 * np.eye(N))
                ones = np.ones(N)
                w = inv_cov @ ones / (ones @ inv_cov @ ones)
                return np.clip(w, 0, 1)  # long-only
            except Exception:
                return np.ones(N) / N

        # Raw covariance
        cov_raw = train.cov().values
        w_raw = _min_vol_weights(cov_raw)

        # Cleaned correlation → reconstruct covariance
        clean_result = self.clean_correlation_matrix(train)
        C_clean = clean_result["cleaned_matrix"].values
        std_arr = train.std().values
        cov_clean = C_clean * np.outer(std_arr, std_arr)
        w_clean = _min_vol_weights(cov_clean)

        # Out-of-sample evaluation
        test_arr = test.values

        def _sharpe(weights: np.ndarray) -> float:
            port_ret = test_arr @ weights
            return float(np.mean(port_ret) / (np.std(port_ret) + 1e-10) * np.sqrt(252))

        sharpe_raw = _sharpe(w_raw)
        sharpe_clean = _sharpe(w_clean)

        return {
            "raw_weights": dict(zip(returns.columns, w_raw.round(4))),
            "cleaned_weights": dict(zip(returns.columns, w_clean.round(4))),
            "raw_max_weight": float(np.max(np.abs(w_raw))),
            "cleaned_max_weight": float(np.max(np.abs(w_clean))),
            "raw_oos_sharpe": sharpe_raw,
            "cleaned_oos_sharpe": sharpe_clean,
            "improvement_pct": float((sharpe_clean - sharpe_raw) / (abs(sharpe_raw) + 1e-10) * 100),
        }

    def eigenvalue_analysis(self, returns: pd.DataFrame) -> dict:
        """
        Full eigenvalue analysis: signal vs. noise decomposition, factor interpretation.
        """
        N = returns.shape[1]
        T = returns.shape[0]

        C = returns.corr().values
        eigenvalues, eigenvectors = np.linalg.eigh(C)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        mp = self.marchenko_pastur_bounds(N, T)
        lam_max = mp["lambda_max"]
        signal_mask = eigenvalues > lam_max
        n_signal = int(np.sum(signal_mask))

        cumvar = np.cumsum(eigenvalues) / np.sum(eigenvalues) * 100

        # Top factors
        top_factors = []
        for k in range(min(n_signal, 5)):
            lam = float(eigenvalues[k])
            var_exp = float(lam / np.sum(eigenvalues) * 100)
            loadings = eigenvectors[:, k]
            top_idx = np.argsort(np.abs(loadings))[::-1][:5]
            top_load = {
                returns.columns[i]: round(float(loadings[i]), 4)
                for i in top_idx
            }

            if k == 0:
                sign_pct = np.mean(loadings > 0) * 100
                interp = (
                    f"Market factor — {sign_pct:.0f}% of assets load positively."
                )
            else:
                pos = [returns.columns[i] for i in np.where(loadings > 0.1)[0]][:3]
                neg = [returns.columns[i] for i in np.where(loadings < -0.1)[0]][:3]
                interp = (
                    f"Factor {k+1}: positive loading ({', '.join(pos) or 'none'}), "
                    f"negative loading ({', '.join(neg) or 'none'})."
                )

            top_factors.append({
                "eigenvalue": lam,
                "variance_explained_pct": var_exp,
                "top_loadings": top_load,
                "interpretation": interp,
            })

        return {
            "eigenvalues": eigenvalues,
            "eigenvectors": eigenvectors,
            "mp_bounds": mp,
            "n_signal": n_signal,
            "n_noise": N - n_signal,
            "signal_eigenvalues": eigenvalues[signal_mask],
            "cumulative_variance_explained_pct": cumvar.tolist(),
            "top_factors": top_factors,
        }

    @staticmethod
    def _ledoit_wolf_alpha(C: np.ndarray, T: int) -> float:
        """
        Analytical Ledoit-Wolf shrinkage intensity toward identity.
        Simplified Ledoit-Wolf (2004) constant-target estimator.
        """
        N = C.shape[0]
        mu = np.trace(C) / N
        delta = np.linalg.norm(C - mu * np.eye(N), "fro") ** 2 / N

        # Asymptotic formula: alpha* ≈ min(1, max(0, (N/T) / delta * trace_term))
        trace_sq = np.trace(C @ C) / N
        numerator = ((1 - 2 / N) * trace_sq + np.trace(C) ** 2 / N) / ((T + 1 - 2 / N) * (trace_sq - np.trace(C) ** 2 / N))
        alpha = float(np.clip(numerator, 0.0, 1.0))
        return alpha
