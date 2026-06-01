"""
Ravinala Hedging Analytics & PnL Attribution
Delta hedging simulations, hedging costs, P&L explain
"""

import numpy as np
from typing import Dict, List
import warnings

warnings.filterwarnings('ignore')


class HedgingAnalytics:
    """Delta hedging and hedging cost analysis."""

    @staticmethod
    def delta_hedge_pnl(spot_history: np.ndarray, strike: float, T_initial: float,
                        rate: float, carry: float, vol_history: np.ndarray,
                        option_type: str = 'call', rehedge_freq: int = 5,
                        transaction_cost_bps: float = 1.0) -> Dict:
        """
        Simulate delta hedging over time with transaction costs.

        rehedge_freq: Rehedge every N days.
        transaction_cost_bps: Transaction cost in basis points (1.0 = 0.01%).
        """
        from engine import BlackScholesGreeks

        bs = BlackScholesGreeks()
        n_days = len(spot_history)

        option_pnl = []
        hedge_pnl = []
        transaction_costs = []
        net_pnl = []
        delta_positions = []
        rehedge_count = 0
        current_hedge = 0.0

        for i in range(n_days - 1):
            T_remaining = T_initial - (i / 252)
            if T_remaining <= 0:
                break

            spot = spot_history[i]
            vol = vol_history[i] if i < len(vol_history) else vol_history[-1]

            delta = bs.delta(spot, strike, T_remaining, rate, carry, vol, option_type)

            cost = 0.0
            if i % rehedge_freq == 0 and i > 0:
                hedge_change = abs(delta - current_hedge)
                cost = hedge_change * spot * (transaction_cost_bps / 10000)
                transaction_costs.append(cost)
                current_hedge = delta
                rehedge_count += 1

            if option_type == 'call':
                opt_before = bs.call_price(spot, strike, T_remaining, rate, carry, vol)
                opt_after = bs.call_price(spot_history[i + 1], strike, T_remaining - 1 / 252, rate, carry, vol)
            else:
                opt_before = bs.put_price(spot, strike, T_remaining, rate, carry, vol)
                opt_after = bs.put_price(spot_history[i + 1], strike, T_remaining - 1 / 252, rate, carry, vol)

            option_pnl_day = opt_after - opt_before
            option_pnl.append(option_pnl_day)

            spot_move = spot_history[i + 1] - spot
            hedge_pnl_day = -current_hedge * spot_move
            hedge_pnl.append(hedge_pnl_day)

            net_pnl.append(option_pnl_day + hedge_pnl_day - cost)
            delta_positions.append(current_hedge)

        net_pnl_arr = np.array(net_pnl)
        total_costs = sum(transaction_costs)

        return {
            'option_pnl': np.array(option_pnl),
            'hedge_pnl': np.array(hedge_pnl),
            'transaction_costs': np.array(transaction_costs),
            'net_pnl': net_pnl_arr,
            'cumulative_net_pnl': np.cumsum(net_pnl_arr),
            'total_pnl': np.sum(net_pnl_arr),
            'total_transaction_costs': total_costs,
            'pnl_std': np.std(net_pnl_arr),
            'sharpe_ratio': np.mean(net_pnl_arr) / (np.std(net_pnl_arr) + 1e-6),
            'max_drawdown': np.min(np.cumsum(net_pnl_arr)),
            'rehedge_count': rehedge_count,
            'avg_delta_position': np.mean(delta_positions),
        }

    @staticmethod
    def optimal_rehedge_frequency(spot_history: np.ndarray, strike: float,
                                  T_initial: float, rate: float, carry: float,
                                  vol_history: np.ndarray, option_type: str = 'call',
                                  transaction_cost_bps: float = 1.0) -> Dict:
        """
        Find optimal rehedging frequency to minimise total costs.

        Trade-off: more frequent hedging = lower gamma risk but higher transaction costs.
        """
        freqs = [1, 2, 5, 10, 20, 50]
        results = {}

        for freq in freqs:
            result = HedgingAnalytics.delta_hedge_pnl(
                spot_history, strike, T_initial, rate, carry, vol_history,
                option_type, rehedge_freq=freq, transaction_cost_bps=transaction_cost_bps
            )
            results[f'Every_{freq}_days'] = {
                'total_pnl': result['total_pnl'],
                'transaction_costs': result['total_transaction_costs'],
                'pnl_std': result['pnl_std'],
                'net_return': result['total_pnl'] - result['total_transaction_costs'],
            }

        return results

    @staticmethod
    def gamma_cost_estimate(gamma: float, realized_vol: float, spot: float, T: float) -> float:
        """
        Estimate daily gamma (convexity) cost from realized moves.

        Approximate daily cost ≈ 0.5 * Gamma * (Daily_Realized_Vol)^2
        """
        daily_realized_vol = realized_vol / np.sqrt(252)
        daily_move = spot * daily_realized_vol
        return 0.5 * gamma * daily_move ** 2

    @staticmethod
    def vega_hedge_analysis(vega: float, short_vol: float, long_vol: float) -> Dict:
        """
        Analyse vega hedging: buying volatility to offset a short vega position.

        vega: position vega (sensitivity to 1% vol change).
        short_vol / long_vol: vol strikes in decimal (e.g. 0.20 = 20%).
        """
        vol_difference = long_vol - short_vol
        hedge_effectiveness = vol_difference / (short_vol + 1e-6)

        return {
            'position_vega': vega,
            'vol_difference': vol_difference * 100,
            'hedge_effectiveness': hedge_effectiveness * 100,
            'cost_if_vol_rises_1pct': vega * 0.01,
            'pnl_if_vol_stays': 0.0,
        }


class PnLAttribution:
    """Break down option P&L by Greeks (P&L explain)."""

    @staticmethod
    def daily_pnl_attribution(delta: float, gamma: float, vega: float, theta: float,
                              rho: float, spot_move: float, vol_change: float,
                              rate_change: float, days_passed: float = 1.0) -> Dict:
        """
        Decompose daily P&L into Greek contributions.

        P&L ≈ Delta*dS + 0.5*Gamma*dS^2 + Vega*dVol + Theta*dt + Rho*dr
        """
        delta_pnl = delta * spot_move
        gamma_pnl = 0.5 * gamma * spot_move ** 2
        vega_pnl = vega * vol_change
        theta_pnl = theta * days_passed
        rho_pnl = rho * rate_change
        total_pnl = delta_pnl + gamma_pnl + vega_pnl + theta_pnl + rho_pnl

        return {
            'delta_pnl': delta_pnl,
            'gamma_pnl': gamma_pnl,
            'vega_pnl': vega_pnl,
            'theta_pnl': theta_pnl,
            'rho_pnl': rho_pnl,
            'total_pnl': total_pnl,
            'greeks_pnl_total': total_pnl,
            'unexplained_pnl': 0.0,
        }

    @staticmethod
    def portfolio_pnl_attribution(positions: List[Dict], market_moves: Dict) -> Dict:
        """
        Aggregate P&L attribution across a portfolio.

        positions: list of {delta, gamma, vega, theta, rho, notional}
        market_moves: {spot_move, vol_change, rate_change}
        """
        total_greek_pnl = {'delta': 0.0, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0, 'rho': 0.0}

        for pos in positions:
            notional = pos.get('notional', 1.0)
            greek_pnl = PnLAttribution.daily_pnl_attribution(
                pos.get('delta', 0) * notional,
                pos.get('gamma', 0) * notional,
                pos.get('vega', 0) * notional,
                pos.get('theta', 0) * notional,
                pos.get('rho', 0) * notional,
                market_moves.get('spot_move', 0),
                market_moves.get('vol_change', 0),
                market_moves.get('rate_change', 0),
            )
            total_greek_pnl['delta'] += greek_pnl['delta_pnl']
            total_greek_pnl['gamma'] += greek_pnl['gamma_pnl']
            total_greek_pnl['vega'] += greek_pnl['vega_pnl']
            total_greek_pnl['theta'] += greek_pnl['theta_pnl']
            total_greek_pnl['rho'] += greek_pnl['rho_pnl']

        return {
            **total_greek_pnl,
            'total_pnl': sum(total_greek_pnl.values()),
        }

    @staticmethod
    def pnl_explain_vs_model(realized_pnl: float, greek_pnl: float,
                             transaction_costs: float = 0) -> Dict:
        """
        Compare realized P&L vs Greeks-predicted P&L to identify model errors or hidden risks.
        """
        unexplained = realized_pnl - greek_pnl - transaction_costs
        unexplained_pct = (unexplained / (abs(realized_pnl) + 1e-6)) * 100

        return {
            'realized_pnl': realized_pnl,
            'greek_pnl': greek_pnl,
            'transaction_costs': transaction_costs,
            'unexplained_pnl': unexplained,
            'unexplained_pct': unexplained_pct,
            'model_accuracy': 100 - abs(unexplained_pct),
        }
