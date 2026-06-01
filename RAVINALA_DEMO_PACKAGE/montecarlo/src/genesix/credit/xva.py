"""
XVA framework — Credit/Debit/Funding Value Adjustments.

Total Price = Risk-Free Price - CVA + DVA - FVA

CVA: cost of counterparty default risk (always negative for buyer)
DVA: benefit from own default risk (controversial, but IFRS 13 requires it)
FVA: funding cost of posting collateral

Post-2008 these adjustments are mandatory. CVA desks at major banks
manage portfolios of trillions in notional.

Reference: Gregory (2012), Brigo & Morini (2011)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class XVACalculator:
    """Compute CVA, DVA, FVA for derivative portfolios."""

    def cva(
        self,
        expected_exposures: np.ndarray,
        default_probs: np.ndarray,
        recovery: float = 0.40,
        discount_factors: Optional[np.ndarray] = None,
    ) -> float:
        """
        Credit Value Adjustment.

        CVA = (1-R) × Σ EE(t_i) × PD(t_{i-1}, t_i) × DF(t_i)

        Args:
            expected_exposures: array of expected positive exposures at each time step
            default_probs: array of marginal default probabilities per period
            recovery: recovery rate
            discount_factors: array of risk-free discount factors (default: all ones)

        Returns: CVA (positive number = cost to you)
        """
        EE = np.asarray(expected_exposures, dtype=float)
        PD = np.asarray(default_probs, dtype=float)
        if discount_factors is None:
            DF = np.ones_like(EE)
        else:
            DF = np.asarray(discount_factors, dtype=float)

        n = min(len(EE), len(PD), len(DF))
        return float((1 - recovery) * np.sum(EE[:n] * PD[:n] * DF[:n]))

    def dva(
        self,
        expected_negative_exposures: np.ndarray,
        own_default_probs: np.ndarray,
        recovery: float = 0.40,
        discount_factors: Optional[np.ndarray] = None,
    ) -> float:
        """
        Debit Value Adjustment — benefit from own default.

        DVA = (1-R_own) × Σ ENE(t_i) × PD_own(t_i) × DF(t_i)

        ENE = Expected Negative Exposure (from your counterparty's perspective)
        """
        ENE = np.asarray(expected_negative_exposures, dtype=float)
        PD = np.asarray(own_default_probs, dtype=float)
        if discount_factors is None:
            DF = np.ones_like(ENE)
        else:
            DF = np.asarray(discount_factors, dtype=float)

        n = min(len(ENE), len(PD), len(DF))
        return float((1 - recovery) * np.sum(ENE[:n] * PD[:n] * DF[:n]))

    def fva(
        self,
        expected_funding_exposures: np.ndarray,
        funding_spread: float,
        time_steps: Optional[np.ndarray] = None,
    ) -> float:
        """
        Funding Value Adjustment.

        FVA = funding_spread × Σ EFE(t_i) × Δt_i

        EFE = Expected Funding Exposure (positive when you need to post collateral)
        """
        EFE = np.asarray(expected_funding_exposures, dtype=float)
        n = len(EFE)
        if time_steps is None:
            dt = np.ones(n)
        else:
            ts = np.asarray(time_steps, dtype=float)
            dt = np.diff(ts, prepend=0.0)[:n]
        return float(funding_spread * np.sum(EFE * dt))

    def simulate_exposure_profile(
        self,
        trade_type: str,
        notional: float,
        maturity: float,
        n_steps: int = 52,
        sigma: float = 0.20,
        seed: int = 42,
    ) -> dict:
        """
        Simulate simplified expected exposure profile.

        Uses a GBM-like model for the underlying market risk factor.

        Returns:
            {
                'time_grid': np.ndarray,
                'expected_exposure': np.ndarray,
                'expected_negative_exposure': np.ndarray,
                'peak_exposure_95': float,
                'potential_future_exposure_95': np.ndarray,
            }
        """
        rng = np.random.default_rng(seed)
        n_paths = 5000
        dt = maturity / n_steps
        t_grid = np.linspace(0, maturity, n_steps + 1)

        # Simulate MtM paths using geometric Brownian motion for underlying
        Z = rng.standard_normal((n_steps, n_paths))
        log_returns = (-0.5 * sigma**2 * dt + sigma * np.sqrt(dt) * Z)
        MtM = np.zeros((n_steps + 1, n_paths))
        MtM[0] = 0.0  # at inception, NPV = 0

        for k in range(n_steps):
            # Simplified: MtM evolves as random walk
            MtM[k + 1] = MtM[k] * np.exp(log_returns[k]) + notional * sigma * np.sqrt(dt) * Z[k]

        EE = np.mean(np.maximum(MtM, 0), axis=1)
        ENE = np.mean(np.minimum(MtM, 0), axis=1)
        PFE_95 = np.percentile(np.maximum(MtM, 0), 95, axis=1)

        return {
            "time_grid": t_grid,
            "expected_exposure": EE,
            "expected_negative_exposure": np.abs(ENE),
            "peak_exposure_95": float(np.max(PFE_95)),
            "potential_future_exposure_95": PFE_95,
        }

    def xva_report(
        self,
        expected_exposures: np.ndarray,
        cpty_hazard_rates: dict,
        own_hazard_rates: dict,
        funding_spread: float,
        recovery: float = 0.40,
        time_steps: Optional[np.ndarray] = None,
        risk_free_price: float = 0.0,
    ) -> dict:
        """
        Complete XVA breakdown.
        """
        from .reduced_form import HazardRateModel
        hrm = HazardRateModel()

        n = len(expected_exposures)
        if time_steps is None:
            time_steps = np.linspace(0, 1, n + 1)[1:]

        # Marginal default probabilities
        def _marginal_pds(hazard_rates, times):
            pds = []
            q_prev = 1.0
            for t in times:
                q = hrm.survival_probability(float(t), hazard_rates)
                pds.append(max(q_prev - q, 0.0))
                q_prev = q
            return np.array(pds)

        cpty_pds = _marginal_pds(cpty_hazard_rates, time_steps)
        own_pds = _marginal_pds(own_hazard_rates, time_steps)
        dfs = np.exp(-0.05 * time_steps)  # flat 5% discount

        EE = np.asarray(expected_exposures[:n])
        ENE = EE  # simplified: assume symmetric exposure

        cva_val = self.cva(EE, cpty_pds, recovery, dfs)
        dva_val = self.dva(ENE, own_pds, recovery, dfs)
        fva_val = self.fva(EE, funding_spread, time_steps)
        total_xva = cva_val - dva_val + fva_val
        adjusted_price = risk_free_price - total_xva

        notional = float(np.max(EE)) if len(EE) > 0 else 1.0

        return {
            "risk_free_price": float(risk_free_price),
            "cva": float(-cva_val),  # negative (cost)
            "dva": float(dva_val),   # positive (benefit)
            "fva": float(-fva_val),  # negative (cost)
            "total_xva": float(-total_xva),
            "adjusted_price": float(adjusted_price),
            "cva_as_pct_notional": float(cva_val / notional * 100) if notional > 0 else 0.0,
        }
