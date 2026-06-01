"""
Ravinala Advanced Exotics Module
Cliquet, Variance Swaps, Credit-linked Products, etc.
"""

import numpy as np
from typing import Dict
import warnings

warnings.filterwarnings('ignore')


class CliquerProducts:
    """Cliquet options — resetting strike, ratchet structures."""

    @staticmethod
    def european_cliquet(paths: np.ndarray, coupon_dates: np.ndarray,
                         floor: float = 0.0, cap: float = float('inf')) -> np.ndarray:
        """
        European Cliquet: coupon locked at each reset date.

        Payoff = 100 * (1 + sum of capped/floored period returns).

        paths: MC paths, shape (n_sims, n_steps).
        coupon_dates: column indices of observation/reset dates.
        """
        n_sims = paths.shape[0]
        valid_dates = np.array([int(d) for d in coupon_dates if d < paths.shape[1]], dtype=int)
        if valid_dates.size == 0:
            return np.full(n_sims, 100.0)
        obs_indices = np.concatenate([[0], valid_dates])
        obs_spots = paths[:, obs_indices]                             # (n_sims, n_obs+1)
        period_returns = obs_spots[:, 1:] / obs_spots[:, :-1] - 1   # (n_sims, n_dates)
        return 100.0 * (1.0 + np.clip(period_returns, floor, cap).sum(axis=1))

    @staticmethod
    def memory_cliquet(paths: np.ndarray, coupon_dates: np.ndarray,
                       floor: float = 0.0, cap: float = float('inf')) -> np.ndarray:
        """
        Memory Cliquet: negative period coupons carry forward (like a Phoenix with memory).
        """
        n_sims = paths.shape[0]
        valid_dates = np.array([int(d) for d in coupon_dates if d < paths.shape[1]], dtype=int)
        if valid_dates.size == 0:
            return np.full(n_sims, 100.0)
        obs_indices = np.concatenate([[0], valid_dates])
        obs_spots = paths[:, obs_indices]
        period_returns = obs_spots[:, 1:] / obs_spots[:, :-1] - 1
        period_coupons = np.clip(period_returns, floor, cap)
        # Positive coupons contribute directly; negative coupons as absolute value (memory recall)
        total = np.where(period_coupons > 0, period_coupons, np.abs(period_coupons)).sum(axis=1)
        return 100.0 * (1.0 + total)

    @staticmethod
    def ratchet_option(paths: np.ndarray, coupon_dates: np.ndarray,
                       step_size: float = 0.01) -> np.ndarray:
        """
        Ratchet: participation rate increases each period starting from 50%.

        Each period adds step_size to the participation rate.
        """
        n_sims = paths.shape[0]
        valid_dates = np.array([int(d) for d in coupon_dates if d < paths.shape[1]], dtype=int)
        if valid_dates.size == 0:
            return np.full(n_sims, 100.0)
        obs_indices = np.concatenate([[0], valid_dates])
        obs_spots = paths[:, obs_indices]
        period_returns = obs_spots[:, 1:] / obs_spots[:, :-1] - 1
        n_dates = period_returns.shape[1]
        participations = 0.5 + step_size * np.arange(1, n_dates + 1)  # (n_dates,)
        return 100.0 * (1.0 + (period_returns * participations).sum(axis=1))


class VarianceSwaps:
    """Variance and volatility derivatives."""

    @staticmethod
    def variance_swap_payoff(realized_var: float, strike_var: float,
                             variance_notional: float = 1_000_000) -> float:
        """
        Variance Swap payoff.

        Payoff = Notional * (sqrt(Realized_Var) - sqrt(Strike_Var))
        """
        return variance_notional * (np.sqrt(realized_var) - np.sqrt(strike_var))

    @staticmethod
    def realized_variance(paths: np.ndarray) -> float:
        """
        Compute realized variance from MC paths.

        RVar = mean of squared log-returns across all paths and time steps.
        """
        returns = np.diff(np.log(paths), axis=1)
        return np.mean(returns ** 2)

    @staticmethod
    def variance_swap_fair_strike(paths: np.ndarray) -> float:
        """Fair strike (break-even vol) for a variance swap."""
        return np.sqrt(VarianceSwaps.realized_variance(paths))

    @staticmethod
    def volatility_swap_pricing(implied_vol_curve: np.ndarray, realized_vol: float) -> float:
        """
        Volatility swap payoff (in vol %, not variance).

        Strike = mean of implied vol curve. Notional scaled by 10 000.
        """
        strike_vol = np.mean(implied_vol_curve)
        return 10000 * (realized_vol - strike_vol)


class CreditLinkedNotes:
    """Credit-linked structured products."""

    @staticmethod
    def credit_linked_note_payoff(equity_path: np.ndarray, credit_spread: float,
                                  maturity_years: float, default_trigger: float = 0.3) -> np.ndarray:
        """
        Credit-Linked Note: par + 50% equity participation + fixed coupon.

        If issuer credit spread exceeds default_trigger, a haircut is applied
        proportional to the spread.

        equity_path: shape (n_sims, n_steps).
        """
        n_sims = equity_path.shape[0]

        final_equity_return = (equity_path[:, -1] / equity_path[:, 0]) - 1
        note_value = 100 + final_equity_return * 50 + 5.0 * maturity_years

        if credit_spread > default_trigger:
            note_value *= (1 - credit_spread / 10)

        return note_value


class ConvertibleBonds:
    """Convertible bonds — hybrid debt/equity instruments."""

    @staticmethod
    def convertible_bond_payoff(equity_paths: np.ndarray, coupon: float,
                                conversion_ratio: float, issuer_spread: float,
                                maturity_years: float) -> np.ndarray:
        """
        Convertible Bond payoff.

        Payoff = max(Bond_PV, Equity_Value) * distress_haircut

        Bond value includes par + accrued coupons. Distress factor = exp(-spread * T).
        """
        final_equity = equity_paths[:, -1]
        equity_conversion_value = final_equity * conversion_ratio
        bond_value = 100 + coupon * maturity_years * 100
        distress_haircut = np.exp(-issuer_spread * maturity_years)
        return np.maximum(bond_value, equity_conversion_value) * distress_haircut


class RegressionStructures:
    """Range-accrual and corridor products."""

    @staticmethod
    def range_accrual_payoff(paths: np.ndarray, lower_bound: float,
                             upper_bound: float) -> np.ndarray:
        """
        Range Accrual: 5% annual coupon accrues only on days when spot is in [lower, upper].

        Common in FX and commodities.
        """
        in_range = (paths >= lower_bound) & (paths <= upper_bound)
        days_in_range = in_range.sum(axis=1)
        total_days = paths.shape[1]
        coupon_accrual = (days_in_range / total_days) * 0.05
        return 100 * (1 + coupon_accrual)

    @staticmethod
    def worst_of_corridor(paths: np.ndarray, lower_barrier: float,
                          upper_barrier: float) -> np.ndarray:
        """
        Worst-of Corridor: pays 100 if ALL observations stay within barriers, else 70.
        """
        breached = np.any((paths < lower_barrier) | (paths > upper_barrier), axis=1)
        return np.where(breached, 70.0, 100.0)


class EmbeddedOptions:
    """Products with embedded options (callable, putable, etc.)."""

    @staticmethod
    def callable_bond(coupon_paths: np.ndarray, call_price: float = 101,
                      call_dates: np.ndarray = None) -> np.ndarray:
        """
        Callable Bond: issuer can redeem at call_price.

        Investor receives min(bond_value, call_price).
        """
        bond_values = np.full(coupon_paths.shape[0], 100 + np.mean(coupon_paths))
        return np.minimum(bond_values, call_price)

    @staticmethod
    def putable_bond(coupon_paths: np.ndarray, put_price: float = 100,
                     put_dates: np.ndarray = None) -> np.ndarray:
        """
        Putable Bond: investor can force redemption at put_price.

        Investor receives max(bond_value, put_price).
        """
        bond_values = np.full(coupon_paths.shape[0], 100 + np.mean(coupon_paths))
        return np.maximum(bond_values, put_price)


class GreeksCalculator:
    """
    Greeks Engine: Computes Delta, Gamma, Vega, Theta, Rho using finite differences.
    Works for any pricing function.
    """

    @staticmethod
    def delta(pricing_func, spot: float, shift: float = 0.01) -> float:
        """
        Delta = dPrice/dSpot
        Approximated using central differences.
        """
        price_up = pricing_func(spot * (1 + shift))
        price_down = pricing_func(spot * (1 - shift))
        return (price_up - price_down) / (2 * spot * shift)

    @staticmethod
    def gamma(pricing_func, spot: float, shift: float = 0.01) -> float:
        """
        Gamma = d²Price/dSpot²
        Second derivative of price w.r.t. spot.
        """
        price_up = pricing_func(spot * (1 + shift))
        price_mid = pricing_func(spot)
        price_down = pricing_func(spot * (1 - shift))
        return (price_up - 2 * price_mid + price_down) / ((spot * shift) ** 2)

    @staticmethod
    def vega(pricing_func, spot: float, vol: float, shift: float = 0.0001) -> float:
        """
        Vega = dPrice/dVol
        Sensitivity to 1% change in volatility.
        """
        # Helper to compute price with different vol
        def price_with_vol(new_vol):
            return pricing_func(spot, vol=new_vol)

        price_up = price_with_vol(vol + shift)
        price_down = price_with_vol(vol - shift)
        return (price_up - price_down) / (2 * shift) / 100  # Per 1% vol

    @staticmethod
    def theta(pricing_func, spot: float, time_remaining: float, shift_days: float = 1) -> float:
        """
        Theta = -dPrice/dTime
        Daily decay. Shift in days.
        """
        shift_years = shift_days / 365.25
        price_now = pricing_func(spot, time=time_remaining)
        price_later = pricing_func(spot, time=max(0, time_remaining - shift_years))
        return -(price_later - price_now) / shift_days  # Per day

    @staticmethod
    def rho(pricing_func, spot: float, rate: float, shift: float = 0.0001) -> float:
        """
        Rho = dPrice/dRate
        Sensitivity to 1% change in risk-free rate.
        """
        def price_with_rate(new_rate):
            return pricing_func(spot, rate=new_rate)

        price_up = price_with_rate(rate + shift)
        price_down = price_with_rate(rate - shift)
        return (price_up - price_down) / (2 * shift) / 100  # Per 1% rate

    @staticmethod
    def compute_all_greeks(pricing_func, spot: float, vol: float = 0.20,
                           rate: float = 0.03, time_remaining: float = 1.0) -> Dict:
        """
        Compute all Greeks in one go.
        Returns dict with Delta, Gamma, Vega, Theta, Rho.
        """
        return {
            "Delta": GreeksCalculator.delta(
                lambda s: pricing_func(s, vol=vol, rate=rate, time=time_remaining),
                spot
            ),
            "Gamma": GreeksCalculator.gamma(
                lambda s: pricing_func(s, vol=vol, rate=rate, time=time_remaining),
                spot
            ),
            "Vega": GreeksCalculator.vega(
                lambda s: pricing_func(s, spot=spot, rate=rate, time=time_remaining),
                spot, vol
            ),
            "Theta": GreeksCalculator.theta(
                lambda s: pricing_func(s, spot=s, vol=vol, rate=rate),
                spot, time_remaining
            ),
            "Rho": GreeksCalculator.rho(
                lambda s: pricing_func(s, spot=spot, vol=vol, time=time_remaining),
                spot, rate
            ),
        }

    @staticmethod
    def sensitivity_grid(pricing_func, spot: float, vol: float,
                         spot_range: tuple = (-0.2, 0.2),
                         vol_range: tuple = (-0.1, 0.1),
                         grid_points: int = 15) -> np.ndarray:
        """
        Create a 2D sensitivity grid: Spot vs Vol.
        Returns matrix of prices for visualization heatmaps.
        """
        spots = np.linspace(spot * (1 + spot_range[0]), spot * (1 + spot_range[1]), grid_points)
        vols = np.linspace(vol + vol_range[0], vol + vol_range[1], grid_points)

        grid = np.zeros((len(vols), len(spots)))
        for i, v in enumerate(vols):
            for j, s in enumerate(spots):
                try:
                    grid[i, j] = pricing_func(s, vol=v)
                except:
                    grid[i, j] = np.nan

        return grid, spots, vols

    @staticmethod
    def pnl_attribution(price_now: float, price_yst: float, delta: float,
                        gamma: float, vega: float, spot_move: float,
                        vol_move: float) -> Dict:
        """
        Break down P&L into components: Delta, Gamma, Vega contributions.
        """
        pnl_delta = delta * spot_move * price_yst
        pnl_gamma = 0.5 * gamma * (spot_move ** 2) * (price_yst ** 2)
        pnl_vega = vega * vol_move * price_yst

        total_pnl = price_now - price_yst
        explained_pnl = pnl_delta + pnl_gamma + pnl_vega

        return {
            "Total_PnL": total_pnl,
            "Delta_PnL": pnl_delta,
            "Gamma_PnL": pnl_gamma,
            "Vega_PnL": pnl_vega,
            "Unexplained": total_pnl - explained_pnl,
            "PnL_Explanation_%": (explained_pnl / abs(total_pnl) * 100) if total_pnl != 0 else 0,
        }
