"""
Market microstructure — bid-ask spread decomposition and price impact.

Market microstructure studies how prices are formed and how trade mechanics
affect price discovery. Key components:

1. Bid-ask spread decomposition (Glosten-Milgrom 1985):
   Spread = Adverse selection component + Inventory cost + Order processing cost
   - Adverse selection: cost of trading with informed traders
   - Inventory: dealers require compensation for holding risky positions
   - Processing: fixed costs of running a market

2. Price impact (Almgren-Chriss 2001, Kyle 1985):
   Temporary impact: decays after trade
   Permanent impact: price-discovery component, does not decay
   Square-root law: impact ∝ √(trade size / ADV)

3. Market quality measures:
   - Effective spread vs quoted spread
   - Amihud illiquidity ratio
   - Kyle's lambda (price impact coefficient)

Reference: O'Hara (1995), Hasbrouck (2007), Glosten & Milgrom (1985)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class MarketMicrostructure:
    """Market microstructure analysis: spread, impact, liquidity."""

    # ------------------------------------------------------------------ #
    # Bid-ask spread measures                                             #
    # ------------------------------------------------------------------ #

    def effective_spread(
        self,
        prices: np.ndarray,
        midpoints: np.ndarray,
        directions: Optional[np.ndarray] = None,
    ) -> dict:
        """
        Effective bid-ask spread from transaction data.

        Effective spread = 2 × |price - midpoint|
        (captures actual transaction cost vs. quoted spread)

        Quoted spread = ask - bid (what's on the order book)
        Effective spread ≤ quoted spread (price improvement, internalization)

        Args:
            prices: transaction prices
            midpoints: bid-ask midpoints at time of trade
            directions: +1 for buys, -1 for sells (optional; auto-detected via Lee-Ready)
        """
        prices = np.asarray(prices, dtype=float)
        midpoints = np.asarray(midpoints, dtype=float)

        if directions is None:
            # Lee-Ready algorithm: buy if price > midpoint, sell if price < midpoint
            directions = np.sign(prices - midpoints)
            directions[directions == 0] = 1  # treat trades at mid as buys

        directions = np.asarray(directions, dtype=float)
        eff_half_spread = directions * (prices - midpoints)
        eff_spread = 2 * eff_half_spread

        return {
            "effective_spread_mean": float(np.mean(eff_spread)),
            "effective_spread_median": float(np.median(eff_spread)),
            "effective_half_spread_mean": float(np.mean(eff_half_spread)),
            "n_trades": len(prices),
            "pct_buys": float(np.mean(directions > 0)),
        }

    def roll_spread(self, prices: np.ndarray) -> dict:
        """
        Roll (1984) spread estimator from transaction prices only.

        s = 2 × √(-Cov(ΔP_t, ΔP_{t-1}))

        The covariance of consecutive price changes is negative due to bid-ask
        bounce (prices bounce between bid and ask), allowing spread estimation
        without order book data.
        """
        prices = np.asarray(prices, dtype=float)
        dp = np.diff(prices)
        cov = float(np.cov(dp[:-1], dp[1:])[0, 1])

        if cov < 0:
            spread = 2 * np.sqrt(-cov)
        else:
            spread = 0.0  # no bounce detected (continuous markets / trending)

        return {
            "roll_spread": float(spread),
            "autocovariance": float(cov),
            "bounce_detected": cov < 0,
        }

    def amihud_illiquidity(
        self,
        returns: np.ndarray,
        volumes: np.ndarray,
        scale: float = 1e6,
    ) -> dict:
        """
        Amihud (2002) illiquidity ratio.

        ILLIQ = (1/T) Σ |R_t| / Volume_t

        Measures price impact per dollar of trading volume.
        Higher value = more illiquid (prices move more per dollar traded).
        Widely used in cross-sectional return predictability research.
        """
        returns = np.asarray(returns, dtype=float)
        volumes = np.asarray(volumes, dtype=float)

        valid = volumes > 0
        illiq_daily = np.abs(returns[valid]) / (volumes[valid] / scale)

        amihud = float(np.mean(illiq_daily))
        amihud_annual = amihud * 252

        return {
            "amihud_illiquidity": amihud,
            "amihud_illiquidity_annual": amihud_annual,
            "avg_abs_return": float(np.mean(np.abs(returns[valid]))),
            "avg_volume_scaled": float(np.mean(volumes[valid] / scale)),
            "interpretation": (
                f"Amihud ratio = {amihud:.6f}. "
                f"Each $1M traded moves price by {amihud*100:.4f}% on average."
            ),
        }

    # ------------------------------------------------------------------ #
    # Price impact models                                                 #
    # ------------------------------------------------------------------ #

    def kyle_lambda(
        self,
        price_changes: np.ndarray,
        order_flow_imbalance: np.ndarray,
    ) -> dict:
        """
        Kyle's lambda — price impact coefficient.

        Kyle (1985): ΔP = λ × Q  (order flow imbalance)
        λ = Cov(ΔP, Q) / Var(Q)

        Higher λ → more price impact per unit of order flow (less liquid).
        Market maker sets λ to break even against informed traders.
        λ = (σ_v) / (2 × σ_u) where σ_v = information volatility, σ_u = noise trade volume.
        """
        dp = np.asarray(price_changes, dtype=float)
        q = np.asarray(order_flow_imbalance, dtype=float)

        cov = np.cov(dp, q)[0, 1]
        var_q = float(np.var(q))
        lam = cov / var_q if var_q > 0 else 0.0

        # R² of the regression ΔP = λQ
        dp_hat = lam * q
        ss_res = float(np.sum((dp - dp_hat) ** 2))
        ss_tot = float(np.sum((dp - dp.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        return {
            "kyle_lambda": float(lam),
            "r_squared": float(r2),
            "covariance_dp_q": float(cov),
            "var_order_flow": float(var_q),
            "interpretation": (
                f"λ = {lam:.6f}: each unit of order flow imbalance "
                f"moves price by {lam:.6f}."
            ),
        }

    def almgren_chriss_impact(
        self,
        trade_size: float,
        adv: float,
        volatility: float,
        bid_ask_spread: float,
        eta: float = 0.1,
        gamma: float = 0.1,
    ) -> dict:
        """
        Almgren-Chriss (2001) price impact model.

        Total impact = Temporary impact + Permanent impact

        Temporary: decays after trade (execution cost only)
          I_temp = η × σ × √(X / ADV)

        Permanent: price-discovery, does not reverse
          I_perm = γ × σ × (X / ADV)

        Square-root law: empirically, impact ~ √(participation rate)

        Args:
            trade_size: shares/units to execute
            adv: average daily volume
            volatility: daily price volatility (%)
            bid_ask_spread: spread as fraction of price
            eta: temporary impact coefficient (typically 0.1)
            gamma: permanent impact coefficient (typically 0.1)
        """
        participation = trade_size / adv if adv > 0 else 0.0

        # Square-root impact components
        i_temp = eta * volatility * np.sqrt(participation)
        i_perm = gamma * volatility * participation
        i_total = i_temp + i_perm

        # Half spread component
        spread_cost = bid_ask_spread / 2

        # Market impact cost as fraction of trade value
        total_cost = i_total + spread_cost

        return {
            "participation_rate": float(participation),
            "temporary_impact_pct": float(i_temp * 100),
            "permanent_impact_pct": float(i_perm * 100),
            "total_market_impact_pct": float(i_total * 100),
            "spread_cost_pct": float(spread_cost * 100),
            "all_in_cost_pct": float(total_cost * 100),
            "interpretation": (
                f"Trading {participation:.1%} of ADV. "
                f"Total impact = {i_total*100:.3f}% "
                f"(temp={i_temp*100:.3f}%, perm={i_perm*100:.3f}%). "
                f"All-in cost = {total_cost*100:.3f}%."
            ),
        }

    def optimal_execution(
        self,
        shares_to_sell: float,
        T_hours: float,
        adv_hourly: float,
        volatility_hourly: float,
        risk_aversion: float = 1e-6,
        n_steps: int = 10,
    ) -> dict:
        """
        Almgren-Chriss optimal execution schedule.

        Balance market impact cost vs. timing risk:
        - Fast execution: high impact, low risk of adverse price moves
        - Slow execution: low impact, high exposure to price moves

        Optimal strategy: TWAP-like schedule adjusted for risk aversion.
        τ = (1/κ) × sinh(κ×T) / sinh(κ×T)  -- hyperbolic decay

        κ = √(λ × η̃ / Σ²)
        where λ = risk aversion, η̃ = temporary impact, Σ = vol
        """
        # Simplified: compute VWAP-optimal trajectory
        times = np.linspace(0, T_hours, n_steps + 1)
        dt = T_hours / n_steps

        # Risk-impact tradeoff parameter
        eta_tilde = 0.1 * volatility_hourly
        kappa = np.sqrt(risk_aversion * eta_tilde / (volatility_hourly ** 2 + 1e-12))

        # Optimal remaining shares at each time step
        if kappa > 1e-10:
            x_t = shares_to_sell * np.sinh(kappa * (T_hours - times)) / np.sinh(kappa * T_hours)
        else:
            x_t = shares_to_sell * (1 - times / T_hours)

        x_t = np.maximum(x_t, 0.0)

        # Trade sizes each period
        trade_sizes = np.diff(x_t)  # negative (selling)

        # Compute costs
        total_impact = 0.0
        for dq in trade_sizes:
            rate = abs(dq) / (adv_hourly * dt + 1e-10)
            total_impact += 0.1 * volatility_hourly * np.sqrt(rate) * abs(dq)

        return {
            "time_grid": times.tolist(),
            "remaining_shares": x_t.tolist(),
            "trade_schedule": (-trade_sizes).tolist(),
            "total_shares": float(shares_to_sell),
            "estimated_impact_cost": float(total_impact),
            "execution_rate_pct_adv": float(np.mean(np.abs(trade_sizes)) / (adv_hourly * dt + 1e-10) * 100),
            "kappa": float(kappa),
            "interpretation": (
                "Optimal execution schedule. "
                f"κ={kappa:.4f} (higher = execute faster). "
                f"Estimated impact cost = {total_impact:.2f} shares equivalent."
            ),
        }

    # ------------------------------------------------------------------ #
    # Glosten-Milgrom spread decomposition                                #
    # ------------------------------------------------------------------ #

    def glosten_milgrom_decomposition(
        self,
        bid_ask_spread: float,
        probability_informed: float,
        asset_value_std: float,
        inventory_cost_pct: float = 0.10,
    ) -> dict:
        """
        Glosten-Milgrom (1985) spread decomposition.

        Spread = Adverse selection + Inventory holding + Processing

        Adverse selection = 2 × μ × (V_ask - E[V|bid])
        where μ = proportion of informed traders.

        Simplification: adverse selection ∝ 2 × prob_informed × σ_V

        The model explains:
        - Why spreads widen before earnings (more informed trading)
        - Why spreads narrow after news (uncertainty resolved)
        - Why small-cap stocks have wider spreads (more information asymmetry)
        """
        adverse_selection = 2 * probability_informed * asset_value_std
        processing = bid_ask_spread * 0.05  # assume 5% is processing
        inventory = bid_ask_spread * inventory_cost_pct
        residual = max(0.0, bid_ask_spread - adverse_selection - inventory - processing)

        # Cap adverse selection at total spread
        adverse_selection = min(adverse_selection, bid_ask_spread * 0.9)
        inventory_adj = min(inventory, bid_ask_spread - adverse_selection - processing)
        processing_adj = min(processing, bid_ask_spread - adverse_selection - inventory_adj)
        residual = bid_ask_spread - adverse_selection - inventory_adj - processing_adj

        return {
            "total_spread": float(bid_ask_spread),
            "adverse_selection_component": float(adverse_selection),
            "inventory_component": float(inventory_adj),
            "processing_component": float(processing_adj),
            "adverse_selection_pct": float(adverse_selection / bid_ask_spread * 100) if bid_ask_spread > 0 else 0.0,
            "inventory_pct": float(inventory_adj / bid_ask_spread * 100) if bid_ask_spread > 0 else 0.0,
            "probability_informed": float(probability_informed),
            "interpretation": (
                f"Spread = {bid_ask_spread:.4f}. "
                f"Adverse selection = {adverse_selection:.4f} "
                f"({adverse_selection/bid_ask_spread*100:.1f}%). "
                f"Informed trader prob = {probability_informed:.1%}."
            ),
        }
