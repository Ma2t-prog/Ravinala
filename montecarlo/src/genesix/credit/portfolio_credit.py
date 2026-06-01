"""
Portfolio credit risk — loss distribution and economic capital.

A credit portfolio's loss distribution has a long right tail:
most of the time losses are small (diversification works),
but in crisis periods many firms default together (correlation spikes).

Economic Capital = VaR_99.9% - Expected Loss
This is what banks must hold to survive a 1-in-1000 year credit event.
"""

from __future__ import annotations

import numpy as np
from typing import Optional
from .copulas import GaussianCopula


class PortfolioCreditRisk:
    """Portfolio loss distribution and credit risk metrics."""

    def __init__(self, seed: int = 42):
        self.copula = GaussianCopula(seed=seed)

    def loss_distribution(
        self,
        notionals: np.ndarray,
        default_probs: np.ndarray,
        correlation_matrix: np.ndarray,
        recovery: float = 0.40,
        n_simulations: int = 100_000,
    ) -> dict:
        """
        Simulate full portfolio loss distribution.

        Returns loss distribution percentiles and risk metrics.
        """
        N = len(notionals)
        lgd = (1 - recovery) * np.asarray(notionals, dtype=float)

        # Simulate defaults via Gaussian copula
        result = self.copula.simulate_defaults(
            list(default_probs), correlation_matrix, n_simulations
        )

        # Need detailed path information — re-simulate with individual firm results
        PDs = np.asarray(default_probs, dtype=float)
        rho = np.asarray(correlation_matrix, dtype=float)

        try:
            L = np.linalg.cholesky(rho)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(rho)
            eigvals = np.maximum(eigvals, 1e-6)
            L = np.linalg.cholesky(eigvecs @ np.diag(eigvals) @ eigvecs.T)

        from scipy.stats import norm
        thresholds = norm.ppf(PDs)

        batch = min(n_simulations, 10_000)
        n_batches = (n_simulations + batch - 1) // batch
        portfolio_losses = np.zeros(n_simulations)

        rng = self.copula.rng

        for b in range(n_batches):
            start = b * batch
            end = min(start + batch, n_simulations)
            n = end - start
            Z_ind = rng.standard_normal((N, n))
            Z_corr = L @ Z_ind
            defaults = Z_corr < thresholds[:, np.newaxis]
            portfolio_losses[start:end] = (lgd[:, np.newaxis] * defaults).sum(axis=0)

        total_notional = float(np.sum(notionals))
        EL = float(np.mean(portfolio_losses))
        UL_std = float(np.std(portfolio_losses))
        var_95 = float(np.percentile(portfolio_losses, 95))
        var_99 = float(np.percentile(portfolio_losses, 99))
        var_999 = float(np.percentile(portfolio_losses, 99.9))
        cvar_99 = float(np.mean(portfolio_losses[portfolio_losses >= var_99]))

        return {
            "portfolio_losses": portfolio_losses,
            "expected_loss": EL,
            "unexpected_loss_std": UL_std,
            "var_95": var_95,
            "var_99": var_99,
            "var_99_9": var_999,
            "cvar_99": cvar_99,
            "economic_capital_99_9": float(var_999 - EL),
            "el_as_pct_notional": float(EL / total_notional * 100),
            "var_99_as_pct_notional": float(var_99 / total_notional * 100),
            "total_notional": total_notional,
            "n_assets": N,
        }

    def contribution_to_var(
        self,
        notionals: np.ndarray,
        default_probs: np.ndarray,
        correlation_matrix: np.ndarray,
        recovery: float = 0.40,
        var_confidence: float = 0.99,
        n_simulations: int = 50_000,
    ) -> dict:
        """
        Each asset's marginal contribution to portfolio VaR.

        Uses Euler decomposition: sum of contributions = total VaR.
        """
        N = len(notionals)
        lgd = (1 - recovery) * np.asarray(notionals, dtype=float)
        PDs = np.asarray(default_probs, dtype=float)
        rho = np.asarray(correlation_matrix, dtype=float)

        try:
            L = np.linalg.cholesky(rho)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(rho)
            eigvals = np.maximum(eigvals, 1e-6)
            L = np.linalg.cholesky(eigvecs @ np.diag(eigvals) @ eigvecs.T)

        from scipy.stats import norm
        thresholds = norm.ppf(PDs)
        rng = self.copula.rng

        batch = min(n_simulations, 10_000)
        n_batches = (n_simulations + batch - 1) // batch

        all_losses = np.zeros((n_simulations, N))
        for b in range(n_batches):
            start = b * batch
            end = min(start + batch, n_simulations)
            n = end - start
            Z_ind = rng.standard_normal((N, n))
            Z_corr = L @ Z_ind
            defaults = Z_corr < thresholds[:, np.newaxis]
            all_losses[start:end, :] = (lgd[:, np.newaxis] * defaults).T

        port_losses = all_losses.sum(axis=1)
        var_level = float(np.percentile(port_losses, var_confidence * 100))

        # Conditional contributions: E[loss_i | total loss >= VaR]
        tail_mask = port_losses >= var_level * 0.99
        if tail_mask.sum() < 10:
            tail_mask = port_losses >= np.percentile(port_losses, 95)

        tail_contributions = np.mean(all_losses[tail_mask, :], axis=0)
        total_tail = tail_contributions.sum()

        pct_contributions = (
            (tail_contributions / total_tail * 100) if total_tail > 0
            else np.zeros(N)
        )

        return {
            "var": float(var_level),
            "tail_contributions": {i: float(v) for i, v in enumerate(tail_contributions)},
            "pct_contributions": {i: float(v) for i, v in enumerate(pct_contributions)},
            "interpretation": (
                f"At {var_confidence*100:.0f}% VaR = {var_level:,.0f}, "
                f"the top 3 contributors account for "
                f"{float(np.sort(pct_contributions)[-3:].sum()):.1f}% of tail risk."
            ),
        }
