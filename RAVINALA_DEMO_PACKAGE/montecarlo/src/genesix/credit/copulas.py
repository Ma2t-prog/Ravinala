"""
Copula models for default correlation.

The 2008 crisis: Gaussian copula (Li 2000) underestimated tail dependence
in CDO tranches. When one firm defaulted, many did — much more than
the Gaussian copula predicted. This caused catastrophic CDO losses.

Implemented:
1. Gaussian copula (Li 2000) — industry standard, thin tails
2. Student-t copula — fatter tails, better crisis behavior

Reference: Li (2000), Schonbucher & Schubert (2001)
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, t as t_dist
from typing import Optional


class GaussianCopula:
    """
    Gaussian copula for correlated defaults.

    For each firm i:
    1. Draw Z_i from correlated multivariate normal N(0, ρ)
    2. Firm i defaults if Z_i < Φ⁻¹(PD_i)

    Known flaw: Gaussian tails → underestimates crisis co-defaults.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def simulate_defaults(
        self,
        default_probs: list,
        correlation_matrix: np.ndarray,
        n_simulations: int = 100_000,
    ) -> dict:
        """
        Simulate correlated defaults via Gaussian copula.

        Returns default count distribution and loss statistics.
        """
        PDs = np.asarray(default_probs, dtype=float)
        N = len(PDs)
        rho = np.asarray(correlation_matrix, dtype=float)

        # Cholesky decomposition of correlation matrix
        try:
            L = np.linalg.cholesky(rho)
        except np.linalg.LinAlgError:
            # Nearest PSD
            eigvals, eigvecs = np.linalg.eigh(rho)
            eigvals = np.maximum(eigvals, 1e-6)
            rho_psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
            L = np.linalg.cholesky(rho_psd)

        # Default thresholds
        thresholds = norm.ppf(PDs)

        # Simulate
        batch = min(n_simulations, 10_000)
        n_batches = (n_simulations + batch - 1) // batch
        default_counts = np.zeros(n_simulations, dtype=int)

        for b in range(n_batches):
            start = b * batch
            end = min(start + batch, n_simulations)
            n = end - start
            Z_ind = self.rng.standard_normal((N, n))
            Z_corr = L @ Z_ind  # (N, n)
            defaults = Z_corr < thresholds[:, np.newaxis]  # (N, n)
            default_counts[start:end] = defaults.sum(axis=0)

        count_hist = np.bincount(default_counts, minlength=N + 1)
        p_0 = float(count_hist[0] / n_simulations)
        p_all = float(count_hist[N] / n_simulations)

        return {
            "default_counts": default_counts,
            "default_rate_distribution": {
                "bins": list(range(N + 1)),
                "counts": count_hist.tolist(),
                "probabilities": (count_hist / n_simulations).tolist(),
            },
            "expected_defaults": float(np.mean(default_counts)),
            "std_defaults": float(np.std(default_counts)),
            "p_0_defaults": p_0,
            "p_all_default": p_all,
            "expected_loss": float(np.sum(PDs)),
        }

    def tranche_loss(
        self,
        attachment: float,
        detachment: float,
        default_probs: list,
        correlation_matrix: np.ndarray,
        recovery: float = 0.40,
        n_simulations: int = 100_000,
    ) -> dict:
        """
        CDO tranche expected loss.

        Tranche absorbs losses between attachment A and detachment D:
        Tranche loss = max(0, min(L - A, D - A)) / (D - A)

        Tranches:
        Equity:       0%  -  3%  (first loss, highest risk)
        Mezzanine:    3%  -  7%
        Senior:       7%  - 15%
        Super Senior: 15% - 100% (last loss, "AAA")
        """
        PDs = np.asarray(default_probs, dtype=float)
        N = len(PDs)
        rho = np.asarray(correlation_matrix, dtype=float)
        A, D = attachment, detachment

        try:
            L = np.linalg.cholesky(rho)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(rho)
            eigvals = np.maximum(eigvals, 1e-6)
            L = np.linalg.cholesky(eigvecs @ np.diag(eigvals) @ eigvecs.T)

        thresholds = norm.ppf(PDs)
        lgd = 1 - recovery  # loss given default per unit

        batch = min(n_simulations, 10_000)
        n_batches = (n_simulations + batch - 1) // batch
        tranche_losses = np.zeros(n_simulations)

        for b in range(n_batches):
            start = b * batch
            end = min(start + batch, n_simulations)
            n = end - start
            Z_ind = self.rng.standard_normal((N, n))
            Z_corr = L @ Z_ind
            defaults = Z_corr < thresholds[:, np.newaxis]
            portfolio_loss = defaults.sum(axis=0) * lgd / N
            tranche_losses[start:end] = np.clip(
                (portfolio_loss - A) / (D - A), 0, 1
            )

        return {
            "expected_tranche_loss": float(np.mean(tranche_losses)),
            "std_tranche_loss": float(np.std(tranche_losses)),
            "attachment": A,
            "detachment": D,
            "tranche_width": D - A,
            "expected_portfolio_loss_pct": float(np.sum(PDs) * lgd / N * 100),
        }


class StudentTCopula:
    """
    Student-t copula — fatter tails than Gaussian.

    Same structure as Gaussian copula but uses multivariate t-distribution.
    The ν (degrees of freedom) parameter controls tail thickness.

    ν → ∞: converges to Gaussian copula
    ν = 3-5: significant tail dependence (realistic for credit crises)
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def simulate_defaults(
        self,
        default_probs: list,
        correlation_matrix: np.ndarray,
        nu: int = 4,
        n_simulations: int = 100_000,
    ) -> dict:
        """
        Simulate correlated defaults via Student-t copula.

        Method:
        1. Draw Z from multivariate normal N(0, ρ)
        2. Draw χ² / ν independent of Z
        3. T = Z / √(χ²/ν) ~ multivariate t
        4. Firm i defaults if T_ν(T_i) < PD_i
        """
        PDs = np.asarray(default_probs, dtype=float)
        N = len(PDs)
        rho = np.asarray(correlation_matrix, dtype=float)

        try:
            L = np.linalg.cholesky(rho)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(rho)
            eigvals = np.maximum(eigvals, 1e-6)
            L = np.linalg.cholesky(eigvecs @ np.diag(eigvals) @ eigvecs.T)

        thresholds = t_dist.ppf(PDs, df=nu)

        batch = min(n_simulations, 10_000)
        n_batches = (n_simulations + batch - 1) // batch
        default_counts = np.zeros(n_simulations, dtype=int)

        for b in range(n_batches):
            start = b * batch
            end = min(start + batch, n_simulations)
            n = end - start
            Z_ind = self.rng.standard_normal((N, n))
            Z_corr = L @ Z_ind
            chi2 = self.rng.chisquare(nu, size=n)
            T_corr = Z_corr / np.sqrt(chi2 / nu)
            defaults = T_corr < thresholds[:, np.newaxis]
            default_counts[start:end] = defaults.sum(axis=0)

        count_hist = np.bincount(default_counts, minlength=N + 1)
        return {
            "default_counts": default_counts,
            "expected_defaults": float(np.mean(default_counts)),
            "std_defaults": float(np.std(default_counts)),
            "p_0_defaults": float(count_hist[0] / n_simulations),
            "p_all_default": float(count_hist[N] / n_simulations),
            "degrees_of_freedom": nu,
        }

    def compare_to_gaussian(
        self,
        default_probs: list,
        correlation_matrix: np.ndarray,
        nu: int = 4,
        n_simulations: int = 100_000,
        threshold_k: Optional[int] = None,
    ) -> dict:
        """
        Compare tail risk: Gaussian vs t-copula.

        Shows how much more tail risk the t-copula implies.
        """
        N = len(default_probs)
        if threshold_k is None:
            threshold_k = max(1, N // 4)

        gauss = GaussianCopula(seed=0)
        g_result = gauss.simulate_defaults(default_probs, correlation_matrix, n_simulations)

        t_cop = StudentTCopula(seed=0)
        t_result = self.simulate_defaults(default_probs, correlation_matrix, nu, n_simulations)

        g_counts = g_result["default_counts"]
        t_counts = t_result["default_counts"]

        p_gauss = float(np.mean(g_counts >= threshold_k))
        p_t = float(np.mean(t_counts >= threshold_k))
        ratio = p_t / p_gauss if p_gauss > 0 else float("inf")

        return {
            f"gaussian_p_{threshold_k}plus_defaults": p_gauss,
            f"t_copula_p_{threshold_k}plus_defaults": p_t,
            "tail_risk_ratio": float(ratio),
            "threshold_k": threshold_k,
            "nu": nu,
            "interpretation": (
                f"The t-copula (ν={nu}) predicts {ratio:.1f}× more probability of "
                f"{threshold_k}+ simultaneous defaults than the Gaussian copula. "
                f"This difference is exactly what caused CDO losses to far exceed "
                f"'AAA' expectations in 2008. The Gaussian copula said tail events "
                f"were practically impossible. The t-copula shows they are not."
            ),
        }
