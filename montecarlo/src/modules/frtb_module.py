"""Ravinala by TSIVAHINY Matthias — FRTB & Regulatory Capital Module (Simplified Basel IV)."""

import numpy as np


class SBMCapitalCalculator:
    """
    Sensitivities-Based Method (SBM) capital calculator under FRTB / Basel IV.

    Computes delta, vega, and curvature risk charges for equity portfolios.
    """

    SECTOR_RISK_WEIGHTS = {
        "Technology": 0.55,
        "Telecom": 0.55,
        "Finance": 0.60,
        "Energy": 0.65,
        "Healthcare": 0.45,
        "Consumer": 0.50,
        "Utilities": 0.60,
        "Materials": 0.65,
        "Other": 0.70,
    }

    BASEL_RISK_WEIGHTS = {
        # Equity bucket → risk weight (FRTB Table 8)
        1: 0.55,   # Large-cap, EM
        2: 0.60,   # Large-cap, EM — Finance
        3: 0.45,   # Large-cap, Advanced economies
        4: 0.55,   # Large-cap, Advanced economies — Finance
        5: 0.70,   # Small-cap, EM
        6: 0.75,   # Small-cap, EM — Finance
        7: 0.65,   # Small-cap, Advanced economies
        8: 0.70,   # Small-cap, Advanced economies — Finance
        9: 0.55,   # Indices, volatility
        10: 0.60,  # Other
        11: 0.70,  # Residual
    }

    # Intra-bucket correlation
    RHO = 0.75
    # Cross-bucket correlation
    GAMMA = 0.25

    def __init__(self):
        pass

    def _assign_sector(self, ticker: str) -> str:
        """Heuristic sector assignment. Overridable via subclass or external mapping."""
        tech_tickers = {"AAPL", "MSFT", "GOOGL", "GOOG", "META", "NVDA", "AMD", "INTC", "TSM"}
        finance_tickers = {"JPM", "BAC", "GS", "MS", "C", "WFC", "BRK.B", "AXP"}
        energy_tickers = {"XOM", "CVX", "BP", "SHEL", "COP", "EOG", "SLB"}
        health_tickers = {"JNJ", "PFE", "MRK", "ABBV", "UNH", "BMY", "AMGN"}

        t = ticker.upper()
        if t in tech_tickers:
            return "Technology"
        if t in finance_tickers:
            return "Finance"
        if t in energy_tickers:
            return "Energy"
        if t in health_tickers:
            return "Healthcare"
        return "Other"

    def calculate_delta_charge(self, greeks_by_asset: dict) -> dict:
        """
        Compute FRTB SBM delta risk charge for equity positions.

        Parameters
        ----------
        greeks_by_asset : dict
            Keys are ticker strings. Values are dicts with:
              - "delta"    : option delta (0 to 1 for calls, -1 to 0 for puts)
              - "spot"     : current spot price
              - "notional" : notional value of the position

        Returns dict with delta_charge, by_sector, total_capital.
        """
        try:
            # Group weighted sensitivities by sector
            sector_ws = {}  # sector -> list of WS_i

            for ticker, greeks in greeks_by_asset.items():
                delta = float(greeks.get("delta", 0.0))
                spot = float(greeks.get("spot", 0.0))
                notional = float(greeks.get("notional", 0.0))

                net_sensitivity = delta * spot * notional
                sector = self._assign_sector(ticker)
                rw = self.SECTOR_RISK_WEIGHTS.get(sector, 0.70)
                ws = rw * net_sensitivity

                if sector not in sector_ws:
                    sector_ws[sector] = []
                sector_ws[sector].append(ws)

            by_sector = {}
            K_b_values = []
            S_b_values = []

            for sector, ws_list in sector_ws.items():
                ws_arr = np.array(ws_list)
                n = len(ws_arr)

                # Intra-bucket aggregation with correlation rho
                sum_sq = np.sum(ws_arr ** 2)
                sum_cross = 0.0
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            sum_cross += self.RHO * ws_arr[i] * ws_arr[j]

                K_b = float(np.sqrt(max(sum_sq + sum_cross, 0.0)))
                S_b = float(np.sum(ws_arr))

                K_b_values.append(K_b)
                S_b_values.append(S_b)

                by_sector[sector] = {
                    "K_b": round(K_b, 2),
                    "S_b": round(S_b, 2),
                    "n_positions": n,
                }

            # Cross-bucket aggregation
            K_b_arr = np.array(K_b_values)
            S_b_arr = np.array(S_b_values)

            sum_kb_sq = np.sum(K_b_arr ** 2)
            m = len(S_b_arr)
            sum_cross_bc = 0.0
            for b in range(m):
                for c in range(m):
                    if b != c:
                        sum_cross_bc += self.GAMMA * S_b_arr[b] * S_b_arr[c]

            delta_charge = float(np.sqrt(max(sum_kb_sq + sum_cross_bc, 0.0)))
            total_capital = delta_charge  # SBM delta is a capital charge

            return {
                "delta_charge": round(delta_charge, 2),
                "by_sector": by_sector,
                "total_capital": round(total_capital, 2),
            }

        except Exception as e:
            return {
                "delta_charge": 0.0,
                "by_sector": {},
                "total_capital": 0.0,
                "error": str(e),
            }

    def calculate_vega_charge(self, vega_by_asset: dict) -> dict:
        """
        Compute FRTB SBM vega risk charge.

        Parameters
        ----------
        vega_by_asset : dict
            Keys are ticker strings. Values are dicts with:
              - "vega"     : option vega (dV/dσ)
              - "notional" : notional of the position

        Returns dict with vega_charge.
        """
        try:
            VEGA_RW = 0.55  # Equity vega risk weight

            total_vega_charge = 0.0
            for ticker, data in vega_by_asset.items():
                vega = float(data.get("vega", 0.0))
                notional = float(data.get("notional", 0.0))
                vega_sensitivity = vega * notional
                vega_charge_i = VEGA_RW * abs(vega_sensitivity)
                total_vega_charge += vega_charge_i

            return {"vega_charge": round(total_vega_charge, 2)}

        except Exception as e:
            return {"vega_charge": 0.0, "error": str(e)}

    def calculate_curvature_charge(self, gamma_by_asset: dict) -> dict:
        """
        Compute FRTB SBM curvature risk charge.

        For each position, compute CVR+ and CVR- using up/down shocks,
        then take max and aggregate.

        Parameters
        ----------
        gamma_by_asset : dict
            Keys are ticker strings. Values are dicts with:
              - "delta"   : net delta sensitivity
              - "gamma"   : option gamma
              - "spot"    : current spot price
              - "notional": notional

        Returns dict with curvature_charge.
        """
        try:
            total_curvature = 0.0

            for ticker, data in gamma_by_asset.items():
                delta_i = float(data.get("delta", 0.0))
                gamma_i = float(data.get("gamma", 0.0))
                spot = float(data.get("spot", 0.0))
                notional = float(data.get("notional", 0.0))

                sector = self._assign_sector(ticker)
                rw = self.SECTOR_RISK_WEIGHTS.get(sector, 0.70)

                s_i = spot * notional  # scaled sensitivity base
                shock = s_i * rw

                # CVR+ (upward shock)
                cvr_plus = max(
                    -delta_i * shock + 0.5 * gamma_i * shock ** 2,
                    0.0,
                )
                # CVR- (downward shock)
                cvr_minus = max(
                    -delta_i * (-shock) + 0.5 * gamma_i * (-shock) ** 2,
                    0.0,
                )

                curvature_i = max(cvr_plus, cvr_minus)
                total_curvature += curvature_i

            return {"curvature_charge": round(total_curvature, 2)}

        except Exception as e:
            return {"curvature_charge": 0.0, "error": str(e)}


class SACCRCalculator:
    """
    Standardised Approach for Counterparty Credit Risk (SA-CCR) under Basel IV.

    Computes Exposure at Default (EAD) for OTC derivative trades.
    """

    # Supervisory factors (SF) by asset class (BCBS SA-CCR)
    SUPERVISORY_FACTORS = {
        "equity": 0.32,
        "interest_rate": 0.005,
        "credit": 0.05,
        "fx": 0.04,
        "commodity": 0.18,
        "other": 0.32,
    }

    def __init__(self):
        pass

    def calculate_ead(self, trades: list) -> dict:
        """
        Calculate EAD for a list of derivative trades using SA-CCR.

        Parameters
        ----------
        trades : list of dict
            Each trade dict should contain:
              - "type"        : instrument type (e.g. "option", "forward", "swap")
              - "notional"    : notional amount
              - "delta"       : effective delta (signed, for options; 1.0 for linear)
              - "mtm"         : current mark-to-market value
              - "collateral"  : collateral posted/received (positive = received)
              - "asset_class" : "equity", "interest_rate", "credit", "fx", "commodity"

        Returns dict with ead, rc, addon, capital_charge.
        """
        try:
            total_rc = 0.0
            total_addon = 0.0

            for trade in trades:
                notional = float(trade.get("notional", 0.0))
                delta = float(trade.get("delta", 1.0))
                mtm = float(trade.get("mtm", 0.0))
                collateral = float(trade.get("collateral", 0.0))
                asset_class = str(trade.get("asset_class", "equity")).lower()

                # Replacement Cost
                rc = max(mtm - collateral, 0.0)
                total_rc += rc

                # PFE multiplier (simplified floor at 5% utilisation)
                utilisation = mtm / notional if (mtm > 0 and notional != 0) else 0.05
                utilisation = max(utilisation, 0.05)
                pfe_multiplier = 1.0 + 0.4 * utilisation

                # Supervisory factor
                sf = self.SUPERVISORY_FACTORS.get(asset_class, 0.32)

                # Adjusted notional
                adjusted_notional = notional * abs(delta)

                # AddOn
                addon = sf * adjusted_notional
                total_addon += pfe_multiplier * addon

            ead = 1.4 * (total_rc + total_addon)
            capital_charge = ead * 0.08  # 8% capital ratio

            return {
                "ead": round(ead, 2),
                "rc": round(total_rc, 2),
                "addon": round(total_addon, 2),
                "capital_charge": round(capital_charge, 2),
            }

        except Exception as e:
            return {
                "ead": 0.0,
                "rc": 0.0,
                "addon": 0.0,
                "capital_charge": 0.0,
                "error": str(e),
            }


class KVACalculator:
    """
    Capital Valuation Adjustment (KVA) calculator.

    KVA represents the cost of holding regulatory capital over the life of a trade.
    """

    def __init__(self):
        pass

    def calculate_kva(
        self,
        trades: list,
        cost_of_capital: float = 0.10,
        n_sims: int = 2000,
    ) -> dict:
        """
        Compute KVA using a simplified Monte Carlo simulation of future EAD.

        Uses a linear amortisation approximation:
            KVA ≈ cost_of_capital × EAD_0 × maturity × 0.5

        Parameters
        ----------
        trades : list of dict
            Same format as SACCRCalculator.calculate_ead. Must include "maturity" key
            (in years) for each trade.
        cost_of_capital : float
            Hurdle rate / cost of equity capital (default 10%).
        n_sims : int
            Number of Monte Carlo simulations (used for stochastic EAD evolution).

        Returns dict with kva, cost_of_capital, regulatory_roe.
        """
        try:
            sacr = SACCRCalculator()

            # Compute initial EAD
            ead_result = sacr.calculate_ead(trades)
            ead_0 = ead_result["ead"]

            # Determine max maturity
            maturities = [float(t.get("maturity", 1.0)) for t in trades]
            max_maturity = max(maturities) if maturities else 1.0

            # Monte Carlo simulation of EAD path
            rng = np.random.default_rng(42)
            dt = 0.25  # quarterly steps
            n_steps = max(1, int(max_maturity / dt))
            time_grid = np.linspace(dt, max_maturity, n_steps)

            # Simulate stochastic EAD via GBM-like process (mean-reverting decay)
            ead_paths = np.zeros((n_sims, n_steps))
            ead_paths[:, 0] = ead_0

            vol_ead = 0.15  # assumed EAD volatility
            mean_reversion = 0.3

            for step in range(1, n_steps):
                z = rng.standard_normal(n_sims)
                ead_paths[:, step] = np.maximum(
                    ead_paths[:, step - 1]
                    * np.exp(
                        (-mean_reversion * dt)
                        + vol_ead * np.sqrt(dt) * z
                    ),
                    0.0,
                )

            # Compute KVA as integral of expected EAD discounted
            r = 0.04  # risk-free rate for discounting
            discount_factors = np.exp(-r * time_grid)
            expected_ead = np.mean(ead_paths, axis=0)
            kva_mc = cost_of_capital * np.trapz(expected_ead * discount_factors, time_grid)

            # Simplified approximation for comparison
            kva_simple = cost_of_capital * ead_0 * max_maturity * 0.5

            # Use Monte Carlo result, fallback to simple if unreasonable
            kva = kva_mc if (kva_mc > 0 and not np.isnan(kva_mc)) else kva_simple

            # Regulatory ROE: ratio of KVA-adjusted return to capital
            total_capital = ead_0 * 0.08
            regulatory_roe = (
                (cost_of_capital * total_capital - kva / max_maturity) / total_capital
                if total_capital > 0
                else 0.0
            )

            return {
                "kva": round(float(kva), 2),
                "cost_of_capital": cost_of_capital,
                "regulatory_roe": round(float(regulatory_roe), 4),
            }

        except Exception as e:
            return {
                "kva": 0.0,
                "cost_of_capital": cost_of_capital,
                "regulatory_roe": 0.0,
                "error": str(e),
            }


class RegulatoryROESolver:
    """
    Solve for the minimum trading spread required to meet a target Return on Equity (ROE)
    after accounting for FRTB capital charges and KVA.
    """

    def solve_minimum_spread(
        self,
        notional: float,
        maturity: float,
        delta_charge: float,
        vega_charge: float,
        kva: float,
        target_roe: float = 0.12,
    ) -> dict:
        """
        Compute the minimum bid-offer spread (in bps) to meet a target regulatory ROE.

        Parameters
        ----------
        notional : float
            Trade notional (currency).
        maturity : float
            Trade maturity in years.
        delta_charge : float
            FRTB delta risk charge (from SBMCapitalCalculator).
        vega_charge : float
            FRTB vega risk charge.
        kva : float
            Capital Valuation Adjustment.
        target_roe : float
            Target annual return on regulatory capital (default 12%).

        Returns dict with min_spread_bps, total_capital, annual_cost, viable.
        """
        try:
            total_capital = delta_charge + vega_charge

            if maturity <= 0:
                raise ValueError("maturity must be positive.")
            if notional <= 0:
                raise ValueError("notional must be positive.")

            # Annual cost of capital + amortised KVA
            annual_cost = total_capital * target_roe + kva / maturity

            # Minimum spread in basis points
            min_spread_bps = (annual_cost / notional) * 10000

            # Viability threshold: spread must be below 500 bps (50 ticks)
            viable = bool(min_spread_bps < 500)

            return {
                "min_spread_bps": round(float(min_spread_bps), 2),
                "total_capital": round(float(total_capital), 2),
                "annual_cost": round(float(annual_cost), 2),
                "viable": viable,
            }

        except Exception as e:
            return {
                "min_spread_bps": 0.0,
                "total_capital": 0.0,
                "annual_cost": 0.0,
                "viable": False,
                "error": str(e),
            }
