"""
Ravinala Backtesting Module
Test pricing models against historical data and validate accuracy
"""

import numpy as np
from typing import Dict
import warnings

warnings.filterwarnings('ignore')


class BacktestEngine:
    """Historical pricing validation and backtesting."""

    @staticmethod
    def generate_historical_paths(initial_spot: float, T: float, n_steps: int,
                                  annual_return: float = 0.08, annual_vol: float = 0.20,
                                  n_paths: int = 252) -> np.ndarray:
        """
        Generate synthetic historical paths via GBM.

        Returns array of shape (n_paths, n_steps).
        """
        dt = T / n_steps
        paths = np.zeros((n_paths, n_steps))
        paths[:, 0] = initial_spot

        Z = np.random.standard_normal((n_paths, n_steps - 1))
        drift = (annual_return - 0.5 * annual_vol ** 2) * dt
        diffusion = annual_vol * np.sqrt(dt) * Z
        log_increments = drift + diffusion
        paths[:, 1:] = initial_spot * np.exp(np.cumsum(log_increments, axis=1))

        return paths

    @staticmethod
    def compare_model_vs_realized(model_prices: np.ndarray, realized_prices: np.ndarray) -> Dict:
        """Compare model-predicted prices vs actual market prices."""
        errors = model_prices - realized_prices
        abs_errors = np.abs(errors)
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((realized_prices - np.mean(realized_prices)) ** 2)

        return {
            'mean_error': np.mean(errors),
            'rmse': np.sqrt(np.mean(errors ** 2)),
            'mae': np.mean(abs_errors),
            'max_error': np.max(abs_errors),
            'error_std': np.std(errors),
            'r_squared': 1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
            'pct_within_1bps': np.mean(abs_errors < 0.0001) * 100,
        }

    @staticmethod
    def rolling_greeks_backtest(spot_history: np.ndarray, strike: float, T_initial: float,
                                r: float, carry: float, vol_history: np.ndarray,
                                option_type: str = 'call', rehedge_freq: int = 5) -> Dict:
        """
        Simulate delta hedging over time.

        rehedge_freq: Rehedge every N days.
        Returns hedging P&L analysis.
        """
        from engine import BlackScholesGreeks

        bs = BlackScholesGreeks()
        n_days = len(spot_history)

        option_pnl = []
        hedge_pnl = []
        net_pnl = []
        deltas = []

        for i in range(n_days - 1):
            T_remaining = T_initial - (i / 252)
            if T_remaining <= 0:
                break

            spot = spot_history[i]
            vol = vol_history[i] if i < len(vol_history) else vol_history[-1]

            delta = bs.delta(spot, strike, T_remaining, r, carry, vol, option_type)
            deltas.append(delta)

            if option_type == 'call':
                option_price_before = bs.call_price(spot, strike, T_remaining, r, carry, vol)
                option_price_after = bs.call_price(spot_history[i + 1], strike, T_remaining - 1 / 252, r, carry, vol)
            else:
                option_price_before = bs.put_price(spot, strike, T_remaining, r, carry, vol)
                option_price_after = bs.put_price(spot_history[i + 1], strike, T_remaining - 1 / 252, r, carry, vol)

            option_pnl_day = option_price_after - option_price_before
            option_pnl.append(option_pnl_day)

            spot_move = spot_history[i + 1] - spot
            hedge_pnl_day = -delta * spot_move
            hedge_pnl.append(hedge_pnl_day)

            net_pnl.append(option_pnl_day + hedge_pnl_day)

        net_pnl_arr = np.array(net_pnl)
        return {
            'option_pnl': np.array(option_pnl),
            'hedge_pnl': np.array(hedge_pnl),
            'net_pnl': net_pnl_arr,
            'cumulative_pnl': np.cumsum(net_pnl_arr),
            'total_pnl': np.sum(net_pnl_arr),
            'pnl_std': np.std(net_pnl_arr),
            'sharpe_ratio': np.mean(net_pnl_arr) / (np.std(net_pnl_arr) + 1e-6),
            'deltas': np.array(deltas),
        }

    @staticmethod
    def backteststructured_product(payoff_function, spot_history: np.ndarray,
                                   strike: float, barrier: float, coupon: float,
                                   T: float) -> Dict:
        """
        Backtest a structured product's pricing over time.

        Simulates: if the product was priced on day 0, how would it have evolved?
        """
        n_days = len(spot_history)
        pricing_results = []
        payoff = np.nan

        for i in range(n_days - 1):
            path_so_far = spot_history[:i + 1]
            final_spot = path_so_far[-1]
            worst_spot = np.min(path_so_far)
            try:
                payoff = payoff_function(final_spot, strike, worst_spot, barrier, coupon)
                pricing_results.append(payoff)
            except Exception:
                pricing_results.append(np.nan)

        return {
            'pricing_path': np.array(pricing_results),
            'realized_payoff': payoff,
            'pricing_std': np.nanstd(pricing_results),
        }

    @staticmethod
    def monte_carlo_backtest_accuracy(mc_prices: np.ndarray, realized_prices: np.ndarray,
                                      confidence: float = 0.95) -> Dict:
        """
        Test if MC prices are statistically unbiased vs realized (H0: no bias).
        """
        errors = mc_prices - realized_prices
        mean_error = np.mean(errors)
        se = np.std(errors) / np.sqrt(len(errors))
        t_stat = mean_error / se if se > 0 else 0

        return {
            'mean_error': mean_error,
            'std_error': se,
            't_statistic': t_stat,
            'rmse': np.sqrt(np.mean(errors ** 2)),
            'mae': np.mean(np.abs(errors)),
            'pct_within_1std': np.mean(np.abs(errors) < se) * 100,
        }

    @staticmethod
    def volatility_forecast_accuracy(realized_vol: np.ndarray, forecasted_vol: np.ndarray) -> Dict:
        """Measure accuracy of a volatility forecast against realized vol."""
        errors = forecasted_vol - realized_vol

        return {
            'bias': np.mean(errors),
            'rmse': np.sqrt(np.mean(errors ** 2)),
            'mae': np.mean(np.abs(errors)),
            'correlation': np.corrcoef(realized_vol, forecasted_vol)[0, 1],
        }


class PerfDecayAnalysis:
    """Analyze P&L decay over time (option value decay)."""

    @staticmethod
    def theta_decay_accuracy(actual_pnl: np.ndarray, predicted_theta: np.ndarray) -> Dict:
        """Measure how accurately Theta predicts daily decay."""
        days = np.arange(len(actual_pnl))
        expected_pnl = predicted_theta * days

        return {
            'theta_rmse': np.sqrt(np.mean((actual_pnl - expected_pnl) ** 2)),
            'actual_total_decay': np.sum(actual_pnl),
            'expected_total_decay': np.sum(expected_pnl),
        }


class VaRBacktest:
    """VaR model validation (Kupiec POF test)."""

    @staticmethod
    def kupiec_pof_test(returns: np.ndarray, var_estimates: np.ndarray,
                        confidence: float = 0.95) -> Dict:
        """
        Kupiec Proportion of Failures test.

        At 95% VaR, we expect ~5% breach rate. Fail to reject H0 = valid VaR model.
        """
        breaches = (returns < var_estimates).sum()
        n = len(returns)
        observed_rate = breaches / n
        expected_rate = 1 - confidence

        from scipy.stats import binomtest
        p_value = binomtest(breaches, n, expected_rate, alternative='two-sided').pvalue

        return {
            'expected_breaches': n * expected_rate,
            'observed_breaches': breaches,
            'expected_breach_rate': expected_rate * 100,
            'observed_breach_rate': observed_rate * 100,
            'p_value': p_value,
            'is_valid': p_value > 0.05,
        }
