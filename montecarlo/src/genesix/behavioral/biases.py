"""
Cognitive biases in finance — quantitative analysis.

Key biases with measurable impact on asset prices and portfolio performance:

1. Overconfidence: investors overestimate precision of their information
   → excessive trading, underdiversification, systematic losses (Barber & Odean 2000)

2. Disposition effect: sell winners too soon, hold losers too long
   → Shefrin & Statman (1985); tax-inefficient, return-drag ~3-4% annually

3. Anchoring: price forecasts anchored to recent prices or arbitrary reference
   → price drift, insufficient adjustment from anchors

4. Herding: investors follow crowd, abandon private information
   → momentum, bubbles, crashes (correlation cascade)

5. Home bias: overweight domestic assets relative to CAPM benchmark
   → suboptimal diversification, excess domestic equity premium

Reference: Shiller (2000), Thaler (1999), Barber & Odean (2000)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class BehavioralBiasAnalyzer:
    """Quantify and analyze cognitive biases in financial decision-making."""

    # ------------------------------------------------------------------ #
    # Overconfidence                                                      #
    # ------------------------------------------------------------------ #

    def overconfidence_calibration(
        self,
        forecasts: np.ndarray,
        actuals: np.ndarray,
        confidence_intervals: Optional[tuple] = None,
    ) -> dict:
        """
        Measure overconfidence via calibration of confidence intervals.

        A well-calibrated forecaster's 90% CI should contain the true value 90% of the time.
        Overconfidence: 90% CI contains ~50% of actuals (intervals too narrow).

        Also compute:
        - Mean squared error vs variance of forecasts
        - Excessive precision ratio: (forecast variance) / (actual variance)
        """
        forecasts = np.asarray(forecasts, dtype=float)
        actuals = np.asarray(actuals, dtype=float)
        errors = actuals - forecasts

        mse = float(np.mean(errors ** 2))
        bias = float(np.mean(errors))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(errors)))

        forecast_std = float(np.std(forecasts))
        actual_std = float(np.std(actuals))
        excess_precision = (forecast_std / actual_std) if actual_std > 0 else 1.0

        result = {
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "bias": bias,
            "forecast_std": forecast_std,
            "actual_std": actual_std,
            "excess_precision_ratio": float(excess_precision),
            "overconfident": bool(excess_precision > 1.2),
        }

        if confidence_intervals is not None:
            lower, upper = confidence_intervals
            lower = np.asarray(lower, dtype=float)
            upper = np.asarray(upper, dtype=float)
            coverage = float(np.mean((actuals >= lower) & (actuals <= upper)))
            result["ci_coverage_actual"] = coverage
            result["ci_coverage_stated"] = 0.90  # assumed 90% CI
            result["calibration_gap"] = float(0.90 - coverage)
            result["overconfidence_ratio"] = float(coverage / 0.90) if coverage > 0 else 0.0

        return result

    def excessive_trading_loss(
        self,
        turnover_annual: float,
        transaction_cost_bps: float = 10.0,
        alpha: float = 0.0,
    ) -> dict:
        """
        Performance drag from overconfidence-driven excessive trading.

        Barber & Odean (2000): men trade 45% more than women,
        earning 2.65% less per year (net of transaction costs).

        Performance drag ≈ turnover × 2 × transaction_cost

        Args:
            turnover_annual: annual portfolio turnover (1.0 = full turnover)
            transaction_cost_bps: one-way transaction cost in basis points
            alpha: gross alpha before costs (0 = no skill)
        """
        tc_pct = transaction_cost_bps / 10_000
        two_way_cost = turnover_annual * 2 * tc_pct
        net_alpha = alpha - two_way_cost

        # Barber-Odean reference: average active fund turnover ~80%, net alpha ≈ -1.5%
        benchmark_turnover = 0.80
        excess_turnover = max(0.0, turnover_annual - benchmark_turnover)
        excess_drag = excess_turnover * 2 * tc_pct

        return {
            "gross_alpha": float(alpha),
            "transaction_costs_annual": float(two_way_cost),
            "net_alpha": float(net_alpha),
            "excess_turnover_vs_benchmark": float(excess_turnover),
            "excess_drag_bps": float(excess_drag * 10_000),
            "interpretation": (
                f"At {turnover_annual:.0%} turnover and {transaction_cost_bps:.0f}bps costs, "
                f"annual performance drag = {two_way_cost*10000:.0f}bps. "
                f"Net alpha = {net_alpha*100:.2f}%."
            ),
        }

    # ------------------------------------------------------------------ #
    # Disposition effect                                                  #
    # ------------------------------------------------------------------ #

    def disposition_effect(
        self,
        purchase_prices: np.ndarray,
        current_prices: np.ndarray,
        sold: np.ndarray,
    ) -> dict:
        """
        Measure the disposition effect in a portfolio.

        Disposition Effect = PGR / PLR
        where:
        - PGR = proportion of gains realized = realized gains / (realized gains + unrealized gains)
        - PLR = proportion of losses realized = realized losses / (realized losses + unrealized losses)

        DE > 1: selling winners, holding losers (disposition effect present)
        DE < 1: selling losers, holding winners (tax loss harvesting behavior)

        Args:
            purchase_prices: array of purchase prices
            current_prices: array of current prices
            sold: boolean array, True if position was sold
        """
        purchase_prices = np.asarray(purchase_prices, dtype=float)
        current_prices = np.asarray(current_prices, dtype=float)
        sold = np.asarray(sold, dtype=bool)

        gains = current_prices > purchase_prices
        losses = current_prices < purchase_prices

        realized_gains = int(np.sum(sold & gains))
        unrealized_gains = int(np.sum(~sold & gains))
        realized_losses = int(np.sum(sold & losses))
        unrealized_losses = int(np.sum(~sold & losses))

        pgr = realized_gains / (realized_gains + unrealized_gains) if (realized_gains + unrealized_gains) > 0 else 0.0
        plr = realized_losses / (realized_losses + unrealized_losses) if (realized_losses + unrealized_losses) > 0 else 0.0

        de = pgr / plr if plr > 0 else float("inf")

        return {
            "pgr": float(pgr),
            "plr": float(plr),
            "disposition_effect_ratio": float(de),
            "realized_gains": realized_gains,
            "unrealized_gains": unrealized_gains,
            "realized_losses": realized_losses,
            "unrealized_losses": unrealized_losses,
            "disposition_effect_present": bool(de > 1.0),
            "interpretation": (
                f"PGR={pgr:.2%}, PLR={plr:.2%}, DE={de:.2f}. "
                + ("Investors sell winners too quickly and hold losers too long."
                   if de > 1.0 else "No disposition effect detected.")
            ),
        }

    # ------------------------------------------------------------------ #
    # Anchoring                                                           #
    # ------------------------------------------------------------------ #

    def anchoring_bias(
        self,
        anchors: np.ndarray,
        forecasts: np.ndarray,
        actuals: np.ndarray,
    ) -> dict:
        """
        Measure anchoring: how much do forecasts reflect the anchor vs true value?

        Anchoring coefficient: regress (forecast - actual) on (anchor - actual).
        If coefficient ≈ 1: forecast = anchor (complete anchoring)
        If coefficient ≈ 0: forecast = actual (no anchoring)

        Northcraft & Neale (1987): real estate appraisers anchored to list price
        even when told it was arbitrary.
        """
        anchors = np.asarray(anchors, dtype=float)
        forecasts = np.asarray(forecasts, dtype=float)
        actuals = np.asarray(actuals, dtype=float)

        # OLS: (forecast - actual) = a + b × (anchor - actual)
        y = forecasts - actuals
        x = anchors - actuals

        # Remove cases where anchor = actual (trivial)
        valid = np.abs(x) > 1e-10
        if valid.sum() < 2:
            return {"anchoring_coefficient": 0.0, "r_squared": 0.0}

        x_v, y_v = x[valid], y[valid]
        X = np.column_stack([np.ones(len(x_v)), x_v])
        try:
            beta = np.linalg.lstsq(X, y_v, rcond=None)[0]
            y_hat = X @ beta
            ss_res = float(np.sum((y_v - y_hat) ** 2))
            ss_tot = float(np.sum((y_v - y_v.mean()) ** 2))
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        except Exception:
            beta = [0.0, 0.0]
            r2 = 0.0

        anchoring_coef = float(beta[1])

        return {
            "anchoring_coefficient": anchoring_coef,
            "r_squared": float(r2),
            "anchor_intercept": float(beta[0]),
            "anchoring_present": bool(anchoring_coef > 0.3),
            "interpretation": (
                f"Anchoring coefficient = {anchoring_coef:.3f} "
                f"(0=no anchor, 1=full anchor). "
                + (f"Significant anchoring detected (>{0.3:.1f})."
                   if anchoring_coef > 0.3 else "Minimal anchoring.")
            ),
        }

    # ------------------------------------------------------------------ #
    # Herding                                                             #
    # ------------------------------------------------------------------ #

    def herding_measure(
        self,
        returns: np.ndarray,
        market_return: Optional[np.ndarray] = None,
    ) -> dict:
        """
        Cross-sectional absolute deviation (CSAD) measure of herding.

        Christie & Huang (1995): under rational asset pricing, cross-sectional
        dispersion (CSAD) increases with market moves. Herding → CSAD decreases
        when market makes large moves (everyone follows the herd).

        CSAD_t = (1/N) Σ |R_{i,t} - R_{m,t}|

        Regress: CSAD = a + b₁|R_m| + b₂R_m²
        Herding if b₂ < 0 (dispersion decreases non-linearly in large moves).

        Args:
            returns: (T, N) matrix of asset returns
            market_return: (T,) array (if None, use cross-sectional mean)
        """
        returns = np.asarray(returns, dtype=float)
        T, N = returns.shape

        if market_return is None:
            rm = returns.mean(axis=1)
        else:
            rm = np.asarray(market_return, dtype=float)

        csad = np.mean(np.abs(returns - rm[:, np.newaxis]), axis=1)

        abs_rm = np.abs(rm)
        rm2 = rm ** 2

        X = np.column_stack([np.ones(T), abs_rm, rm2])
        try:
            beta = np.linalg.lstsq(X, csad, rcond=None)[0]
        except Exception:
            beta = [0.0, 0.0, 0.0]

        herding_detected = bool(beta[2] < -1e-6)
        avg_csad = float(np.mean(csad))

        return {
            "avg_csad": avg_csad,
            "beta_abs_rm": float(beta[1]),
            "beta_rm_squared": float(beta[2]),
            "herding_coefficient": float(beta[2]),
            "herding_detected": herding_detected,
            "interpretation": (
                f"CSAD avg={avg_csad:.4f}. b₂={beta[2]:.6f}. "
                + ("Herding detected: dispersion collapses in large market moves."
                   if herding_detected
                   else "No significant herding detected.")
            ),
        }

    # ------------------------------------------------------------------ #
    # Home bias                                                           #
    # ------------------------------------------------------------------ #

    def home_bias_measure(
        self,
        portfolio_weight_domestic: float,
        market_cap_weight_domestic: float,
        domestic_return: float,
        foreign_return: float,
        domestic_vol: float,
        foreign_vol: float,
        correlation: float,
    ) -> dict:
        """
        Quantify home bias and its diversification cost.

        Home bias index = (portfolio_weight - market_weight) / (1 - market_weight)
        Range: 0 (no home bias) to 1 (fully domestic)

        Optimal weight (mean-variance): computed via simple 2-asset MVO.
        Diversification cost: Sharpe ratio loss from over-concentration.

        Reference: French & Poterba (1991): investors hold ~93% domestic equity
        despite US = ~30% of world market cap.
        """
        pw = portfolio_weight_domestic
        mw = market_cap_weight_domestic

        home_bias_index = (pw - mw) / (1 - mw) if mw < 1 else 0.0

        # Mean-variance optimal domestic weight (2-asset)
        mu_d, mu_f = domestic_return, foreign_return
        var_d = domestic_vol ** 2
        var_f = foreign_vol ** 2
        cov_df = correlation * domestic_vol * foreign_vol

        # w* = (mu_d - mu_f + var_f - cov_df) / (var_d + var_f - 2*cov_df)
        denom = var_d + var_f - 2 * cov_df
        if abs(denom) < 1e-12:
            w_optimal = 0.5
        else:
            w_optimal = float(np.clip(
                (mu_d - mu_f + var_f - cov_df) / denom, 0.0, 1.0
            ))

        # Sharpe ratios
        def portfolio_sharpe(w_d):
            ret = w_d * mu_d + (1 - w_d) * mu_f
            vol = np.sqrt(
                w_d**2 * var_d + (1-w_d)**2 * var_f + 2*w_d*(1-w_d)*cov_df
            )
            return ret / vol if vol > 0 else 0.0

        sharpe_portfolio = portfolio_sharpe(pw)
        sharpe_optimal = portfolio_sharpe(w_optimal)
        sharpe_domestic_only = portfolio_sharpe(1.0)
        diversification_gain = sharpe_optimal - sharpe_domestic_only
        diversification_loss = sharpe_optimal - sharpe_portfolio

        return {
            "home_bias_index": float(home_bias_index),
            "portfolio_domestic_weight": float(pw),
            "market_cap_domestic_weight": float(mw),
            "optimal_domestic_weight": float(w_optimal),
            "sharpe_current": float(sharpe_portfolio),
            "sharpe_optimal": float(sharpe_optimal),
            "sharpe_loss_from_bias": float(diversification_loss),
            "diversification_gain_available": float(diversification_gain),
            "interpretation": (
                f"Home bias index = {home_bias_index:.2f} "
                f"(0=none, 1=extreme). "
                f"Optimal weight = {w_optimal:.1%} vs actual {pw:.1%}. "
                f"Sharpe loss from bias: {diversification_loss:.3f}."
            ),
        }
