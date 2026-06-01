"""
Core risk quantification engine.

This is the analytical backbone of GenesiX. Every number shown on the
dashboard traces back to a method in this class.

Convention:
- All returns are simple returns (not log), expressed as decimals (0.01 = 1%)
- VaR is reported as a POSITIVE number representing the loss
  (i.e. VaR 95% = 0.03 means "5% chance of losing more than 3%")
- Confidence levels: 0.95 and 0.99 are standard
- Horizons: 1 (1 day), 5 (1 week), 21 (1 month), 63 (3 months), 252 (1 year)
"""

import logging
from typing import Union

import pandas as pd
import numpy as np
from scipy import stats

from ..utils.config import Config
from ..utils.constants import HISTORICAL_STRESS_EVENTS

logger = logging.getLogger(__name__)


class GenesiXRiskEngine:
    """
    Comprehensive risk measurement engine.
    
    All methods support horizon scaling (1d → 1w → 1m).
    Returns are simple returns (decimals), VaR is positive (loss magnitude).
    """
    
    def __init__(self, n_simulations: int = 10000, random_seed: int | None = 42):
        """
        Initialize risk engine.
        
        Args:
            n_simulations: Number of Monte Carlo simulations
            random_seed: Random seed for reproducibility
        """
        self.n_simulations = n_simulations
        self.rng = np.random.default_rng(random_seed)
        logger.info(f"GenesiXRiskEngine initialized (sims={n_simulations})")

    # ============================================================
    # VALUE AT RISK
    # ============================================================

    def var_historical(
        self,
        returns: Union[pd.Series, np.ndarray],
        confidence: float = 0.95,
        horizon: int = 1,
    ) -> float:
        """
        Historical simulation VaR.
        
        For horizon > 1: use overlapping returns of length=horizon.
        
        Args:
            returns: daily return series (decimals, e.g. 0.01 = 1%)
            confidence: 0.95 or 0.99
            horizon: holding period in trading days (1=1d, 5=1w, 21=1m)
        
        Returns:
            VaR as positive float (loss magnitude at given confidence)
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if len(returns) < 10:
            logger.warning(f"Insufficient data for historical VaR ({len(returns)} points)")
            return np.nan
        
        # For horizon > 1, compute overlapping returns
        if horizon > 1:
            horizon_returns = []
            for i in range(len(returns) - horizon + 1):
                h_ret = (1 + returns.iloc[i:i+horizon]).prod() - 1
                horizon_returns.append(h_ret)
            returns = pd.Series(horizon_returns)
        
        # VaR = percentile of losses (positive value)
        alpha = 1 - confidence
        var = -np.percentile(returns, alpha * 100)
        
        return float(max(var, 0.0))

    def var_parametric(
        self,
        returns: Union[pd.Series, np.ndarray],
        confidence: float = 0.95,
        horizon: int = 1,
    ) -> float:
        """
        Parametric (Gaussian) VaR.
        
        VaR = μ·h + z·σ·√h
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if len(returns) < 10:
            return np.nan
        
        mu = returns.mean()
        sigma = returns.std()
        
        if sigma == 0:
            return 0.0
        
        z = stats.norm.ppf(1 - confidence)
        horizon_sqrt = np.sqrt(horizon)
        var = -(mu * horizon + z * sigma * horizon_sqrt)
        
        return float(max(var, 0.0))

    def var_cornish_fisher(
        self,
        returns: Union[pd.Series, np.ndarray],
        confidence: float = 0.95,
        horizon: int = 1,
    ) -> float:
        """
        Cornish-Fisher VaR — adjusts for skewness and kurtosis.
        
        Better than parametric for assets with fat tails.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if len(returns) < 10:
            return np.nan
        
        mu = returns.mean()
        sigma = returns.std()
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)  # excess kurtosis
        
        if sigma == 0:
            return 0.0
        
        z = stats.norm.ppf(1 - confidence)
        
        # Cornish-Fisher adjustment
        z_cf = (
            z
            + (z**2 - 1) * skew / 6
            + (z**3 - 3*z) * kurt / 24
            - (2*z**3 - 5*z) * skew**2 / 36
        )
        
        horizon_sqrt = np.sqrt(horizon)
        var = -(mu * horizon + z_cf * sigma * horizon_sqrt)
        
        return float(max(var, 0.0))

    def var_monte_carlo(
        self,
        returns: Union[pd.Series, np.ndarray],
        confidence: float = 0.95,
        horizon: int = 1,
        model: str = 'normal',
        investment: float | None = None,
    ) -> float:
        """
        Monte Carlo VaR.
        
        Args:
            model: 'normal' (GBM), 't-student' (fat tails), 'historical_bootstrap'
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if len(returns) < 10:
            return np.nan
        
        mu = returns.mean()
        sigma = returns.std()
        
        if sigma == 0:
            return 0.0
        
        simulated = np.zeros(self.n_simulations)
        
        for i in range(self.n_simulations):
            if model == 'normal':
                path_returns = self.rng.normal(mu, sigma, horizon)
            elif model == 't-student':
                df, loc, scale = stats.t.fit(returns)
                path_returns = stats.t.rvs(df, loc=loc, scale=scale, size=horizon)
            elif model == 'historical_bootstrap':
                path_returns = self.rng.choice(returns.values, size=horizon, replace=True)
            else:
                raise ValueError(f"Unknown MC model: {model}")
            
            simulated[i] = (1 + path_returns).prod() - 1
        
        alpha = 1 - confidence
        var = -np.percentile(simulated, alpha * 100)
        
        return float(max(var, 0.0))

    def cvar(
        self,
        returns: Union[pd.Series, np.ndarray],
        confidence: float = 0.95,
        horizon: int = 1,
        method: str = 'historical',
    ) -> float:
        """
        Conditional VaR (Expected Shortfall).
        
        CVaR is always >= VaR. Average loss beyond VaR.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if len(returns) < 10:
            return np.nan
        
        if method == 'historical':
            var = self.var_historical(returns, confidence, horizon=1)
            
            if horizon > 1:
                horizon_returns = []
                for i in range(len(returns) - horizon + 1):
                    h_ret = (1 + returns.iloc[i:i+horizon]).prod() - 1
                    horizon_returns.append(h_ret)
                horizon_returns = np.array(horizon_returns)
            else:
                horizon_returns = returns.values
            
            tail_returns = horizon_returns[horizon_returns <= -var]
            cvar = -tail_returns.mean() if len(tail_returns) > 0 else var * 1.25
            
            return float(max(cvar, 0.0))
        
        elif method == 'parametric':
            z = stats.norm.ppf(1 - confidence)
            mu = returns.mean()
            sigma = returns.std()
            pdf_z = stats.norm.pdf(z)
            
            if pdf_z > 0 and sigma > 0:
                cvar = -(mu + sigma * pdf_z / (1 - confidence)) * np.sqrt(horizon)
            else:
                cvar = self.var_parametric(returns, confidence, horizon) * 1.25
            
            return float(max(cvar, 0.0))
        
        elif method == 'monte_carlo':
            simulated = []
            for _ in range(self.n_simulations):
                path = self.rng.normal(returns.mean(), returns.std(), horizon)
                simulated.append((1 + path).prod() - 1)
            
            simulated = np.array(simulated)
            alpha = 1 - confidence
            threshold = np.percentile(simulated, alpha * 100)
            tail = simulated[simulated <= threshold]
            
            cvar = -tail.mean() if len(tail) > 0 else -threshold
            return float(max(cvar, 0.0))
        
        else:
            raise ValueError(f"Unknown CVaR method: {method}")

    def var_summary(
        self,
        returns: Union[pd.Series, np.ndarray],
        horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        Complete VaR report across methods and horizons.
        """
        if horizons is None:
            horizons = [1, 5, 21]
        
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        results = []
        
        for h in horizons:
            row = {
                'Horizon': f"{h}d" if h == 1 else f"{h//5}w" if h % 5 == 0 else f"{h}d",
                'Historical': self.var_historical(returns, 0.95, h),
                'Parametric': self.var_parametric(returns, 0.95, h),
                'Cornish-Fisher': self.var_cornish_fisher(returns, 0.95, h),
                'Monte Carlo': self.var_monte_carlo(returns, 0.95, h),
                'CVaR 95%': self.cvar(returns, 0.95, h),
            }
            results.append(row)
        
        return pd.DataFrame(results).set_index('Horizon')

    # ============================================================
    # DISTRIBUTION ANALYSIS
    # ============================================================

    def return_distribution(
        self,
        returns: Union[pd.Series, np.ndarray],
        horizon: int = 1,
    ) -> dict:
        """
        Full statistical profile of the return distribution.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        if horizon > 1:
            horizon_returns = []
            for i in range(len(returns) - horizon + 1):
                h_ret = (1 + returns.iloc[i:i+horizon]).prod() - 1
                horizon_returns.append(h_ret)
            returns = pd.Series(horizon_returns)
        
        jb_stat, jb_pval = stats.jarque_bera(returns)
        
        return {
            'mean': float(returns.mean()),
            'median': float(returns.median()),
            'std': float(returns.std()),
            'skewness': float(stats.skew(returns)),
            'kurtosis': float(stats.kurtosis(returns)),
            'min': float(returns.min()),
            'max': float(returns.max()),
            'percentiles': {
                '1': float(returns.quantile(0.01)),
                '5': float(returns.quantile(0.05)),
                '10': float(returns.quantile(0.10)),
                '25': float(returns.quantile(0.25)),
                '50': float(returns.quantile(0.50)),
                '75': float(returns.quantile(0.75)),
                '90': float(returns.quantile(0.90)),
                '95': float(returns.quantile(0.95)),
                '99': float(returns.quantile(0.99)),
            },
            'normality_test': {
                'jarque_bera_stat': float(jb_stat),
                'jarque_bera_pval': float(jb_pval),
                'is_normal': bool(jb_pval > 0.05),
            },
            'annualized_return': float(returns.mean() * 252),
            'annualized_volatility': float(returns.std() * np.sqrt(252)),
        }

    def simulate_return_scenarios(
        self,
        returns: Union[pd.Series, np.ndarray],
        horizon: int = 5,
        investment: float = 100.0,
        n_scenarios: int | None = None,
    ) -> dict:
        """
        THE core output method for scenario analysis.
        
        Uses Monte Carlo simulation for distribution analysis.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        mu = returns.mean()
        sigma = returns.std()
        
        simulations = self.n_simulations if n_scenarios is None else max(int(n_scenarios), 1) * 200
        simulated = []
        for _ in range(simulations):
            path = self.rng.normal(mu, sigma, horizon)
            total_ret = (1 + path).prod() - 1
            simulated.append(total_ret)
        
        simulated = np.array(simulated)
        
        # Scenario breakpoints
        crash_level = np.percentile(simulated, 5)
        bear_level = np.percentile(simulated, 25)
        bull_level = np.percentile(simulated, 75)
        extreme_level = np.percentile(simulated, 95)
        
        # Mean returns within each band
        crash_ret = simulated[simulated <= crash_level].mean()
        bear_ret = simulated[(simulated > crash_level) & (simulated <= bear_level)].mean()
        base_ret = simulated[(simulated > bear_level) & (simulated <= bull_level)].mean()
        bull_ret = simulated[(simulated > bull_level) & (simulated <= extreme_level)].mean()
        extreme_ret = simulated[simulated > extreme_level].mean()
        
        scenarios = [
            {
                'name': 'Crash',
                'probability': 0.05,
                'return_pct': crash_ret * 100,
                'final_value': investment * (1 + crash_ret),
            },
            {
                'name': 'Bear',
                'probability': 0.20,
                'return_pct': bear_ret * 100,
                'final_value': investment * (1 + bear_ret),
            },
            {
                'name': 'Base',
                'probability': 0.50,
                'return_pct': base_ret * 100,
                'final_value': investment * (1 + base_ret),
            },
            {
                'name': 'Bull',
                'probability': 0.20,
                'return_pct': bull_ret * 100,
                'final_value': investment * (1 + bull_ret),
            },
            {
                'name': 'Extreme Bull',
                'probability': 0.05,
                'return_pct': extreme_ret * 100,
                'final_value': investment * (1 + extreme_ret),
            },
        ]
        
        return {
            'investment': investment,
            'horizon_days': horizon,
            'simulated_returns': simulated,
            'scenarios': scenarios,
            'summary': {
                'expected_value': float(investment * (1 + simulated.mean())),
                'best_case_95': float(investment * (1 + np.percentile(simulated, 95))),
                'worst_case_5': float(investment * (1 + np.percentile(simulated, 5))),
                'probability_profit': float((simulated > 0).mean()),
                'probability_loss_gt_5pct': float((simulated < -0.05).mean()),
                'var_95': float(self.var_historical(returns, 0.95, horizon)),
                'cvar_95': float(self.cvar(returns, 0.95, horizon)),
                'max_simulated_gain': float(simulated.max() * 100),
                'max_simulated_loss': float(simulated.min() * 100),
            },
            'distribution_stats': {
                'mean_return': float(simulated.mean()),
                'std_return': float(simulated.std()),
                'skew': float(stats.skew(simulated)),
                'kurtosis': float(stats.kurtosis(simulated)),
            }
        }

    # ============================================================
    # DRAWDOWN ANALYSIS
    # ============================================================

    def max_drawdown(self, prices: pd.Series) -> float:
        """Maximum peak-to-trough decline. Returns positive float."""
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)
        
        prices = prices.dropna()
        if len(prices) < 2:
            return np.nan
        
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        
        return float(-drawdown.min())

    def drawdown_series(self, prices: pd.Series) -> pd.Series:
        """Underwater equity curve. Values are negative."""
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)
        
        prices = prices.dropna()
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        
        return drawdown

    def drawdown_table(self, prices: pd.Series, top_n: int = 10) -> pd.DataFrame:
        """
        Top N drawdowns with recovery details.
        """
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)
        
        prices = prices.dropna()
        
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        
        drawdowns = []
        i = 0
        while i < len(drawdown):
            if drawdown.iloc[i] < 0:
                start_idx = i
                start_date = prices.index[i]
                
                trough_idx = i
                trough_val = drawdown.iloc[i]
                
                while i < len(drawdown) and drawdown.iloc[i] < 0:
                    if drawdown.iloc[i] < trough_val:
                        trough_val = drawdown.iloc[i]
                        trough_idx = i
                    i += 1
                
                trough_date = prices.index[trough_idx]
                depth = -trough_val
                peak_price = cummax.iloc[start_idx]
                
                recovery_idx = None
                recovery_date = None
                recovery_days = None
                
                for j in range(trough_idx, len(prices)):
                    if prices.iloc[j] >= peak_price:
                        recovery_idx = j
                        recovery_date = prices.index[j]
                        recovery_days = (recovery_date - trough_date).days
                        break
                
                duration = (trough_date - start_date).days
                
                drawdowns.append({
                    'start_date': start_date,
                    'trough_date': trough_date,
                    'end_date': recovery_date,
                    'depth_pct': depth,
                    'duration_days': duration,
                    'recovery_days': recovery_days,
                })
            else:
                i += 1
        
        df = pd.DataFrame(drawdowns).sort_values('depth_pct', ascending=False)
        return df.head(top_n)

    def expected_recovery_time(
        self,
        returns: Union[pd.Series, np.ndarray],
        drawdown_pct: float,
    ) -> int:
        """
        Expected recovery time for a given drawdown magnitude.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        prices = (1 + returns).cumprod()
        dd_table = self.drawdown_table(prices, top_n=100)
        
        similar = dd_table[dd_table['depth_pct'] >= drawdown_pct * 0.9]
        
        if len(similar) == 0:
            return -1
        
        recovery_times = similar['recovery_days'].dropna()
        
        if len(recovery_times) == 0:
            return -1
        
        return int(recovery_times.median())

    # ============================================================
    # STRESS TESTING
    # ============================================================

    def stress_test_historical(
        self,
        portfolio_weights: dict[str, float],
        scenario: str,
        portfolio_value: float = 100.0,
    ) -> dict:
        """
        Apply historical crisis scenario to portfolio.
        """
        if scenario not in HISTORICAL_STRESS_EVENTS:
            available = list(HISTORICAL_STRESS_EVENTS.keys())
            raise ValueError(f"Unknown scenario '{scenario}'. Available: {available}")
        
        scenario_data = HISTORICAL_STRESS_EVENTS[scenario]
        
        # Extract shocks from scenario data (everything except 'date' and 'description')
        shocks = {k: v for k, v in scenario_data.items() if k not in ['date', 'description']}
        
        return self.stress_test_custom(portfolio_weights, shocks, portfolio_value)

    def stress_test_custom(
        self,
        portfolio_weights: dict[str, float],
        shocks: dict[str, float],
        portfolio_value: float = 100.0,
    ) -> dict:
        """
        Apply custom user-defined shocks.
        """
        portfolio_impact = 0.0
        asset_impacts = {}
        
        for asset, weight in portfolio_weights.items():
            shock = shocks.get(asset, 0.0)
            impact = weight * shock
            asset_impacts[asset] = {
                'weight': weight,
                'shock': shock,
                'contribution': impact,
            }
            portfolio_impact += impact
        
        worst = min(asset_impacts.items(), key=lambda x: x[1]['contribution']) if asset_impacts else (None, {})
        best = max(asset_impacts.items(), key=lambda x: x[1]['contribution']) if asset_impacts else (None, {})
        
        return {
            'portfolio_impact_pct': float(portfolio_impact),
            'portfolio_impact_value': float(portfolio_value * portfolio_impact),
            'asset_impacts': asset_impacts,
            'worst_asset': worst[0],
            'best_asset': best[0],
        }

    def stress_test_all_scenarios(
        self,
        portfolio_weights: dict[str, float],
        portfolio_value: float = 100.0,
    ) -> pd.DataFrame:
        """
        Run ALL historical scenarios.
        """
        results = []
        
        for scenario_name in HISTORICAL_STRESS_EVENTS.keys():
            try:
                impact = self.stress_test_historical(portfolio_weights, scenario_name, portfolio_value)
                results.append({
                    'Scenario': scenario_name,
                    'Impact %': impact['portfolio_impact_pct'] * 100,
                    'Impact Value': impact['portfolio_impact_value'],
                    'Worst Asset': impact['worst_asset'],
                })
            except Exception as e:
                logger.warning(f"Error computing stress test for {scenario_name}: {e}")
        
        df = pd.DataFrame(results).sort_values('Impact %')
        return df

    # ============================================================
    # VOLATILITY ANALYSIS
    # ============================================================

    def realized_volatility(
        self,
        returns: Union[pd.Series, np.ndarray],
        window: int = 20,
        annualize: bool = True,
    ) -> pd.Series:
        """
        Rolling realized volatility.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        rolling_vol = returns.rolling(window=window).std()
        
        if annualize:
            rolling_vol = rolling_vol * np.sqrt(252)
        
        return rolling_vol

    def volatility_cone(
        self,
        returns: Union[pd.Series, np.ndarray],
        horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        Volatility cone across horizons.
        """
        if horizons is None:
            horizons = [5, 10, 21, 63, 126, 252]
        
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        cone = {}
        
        for h in horizons:
            if h >= len(returns):
                continue
            
            rolling_vol = self.realized_volatility(returns, window=h, annualize=True)
            rolling_vol = rolling_vol.dropna()
            
            if len(rolling_vol) == 0:
                continue
            
            cone[h] = {
                'min': rolling_vol.min(),
                'p25': rolling_vol.quantile(0.25),
                'median': rolling_vol.median(),
                'p75': rolling_vol.quantile(0.75),
                'max': rolling_vol.max(),
                'current': rolling_vol.iloc[-1],
            }
        
        return pd.DataFrame(cone).T

    def volatility_regime(self, returns: Union[pd.Series, np.ndarray]) -> dict:
        """
        Current volatility regime classification.
        """
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
        
        returns = returns.dropna()
        
        current_vol = returns.std() * np.sqrt(252)
        vol_1y = self.realized_volatility(returns, window=252, annualize=True)
        vol_1y_values = vol_1y.dropna()
        
        if len(vol_1y_values) > 0:
            percentile = float(stats.percentileofscore(vol_1y_values, current_vol))
            vol_short = returns.iloc[-5:].std() * np.sqrt(252) if len(returns) >= 5 else 0
            vol_long = returns.iloc[-20:].std() * np.sqrt(252) if len(returns) >= 20 else 0
            
            if vol_short > vol_long * 1.1:
                trend = 'rising'
            elif vol_short < vol_long * 0.9:
                trend = 'falling'
            else:
                trend = 'stable'
        else:
            percentile = 50.0
            trend = 'stable'
        
        # Classification
        if current_vol < 0.10:
            regime = 'low'
        elif current_vol < 0.18:
            regime = 'normal'
        elif current_vol < 0.25:
            regime = 'elevated'
        elif current_vol < 0.40:
            regime = 'high'
        else:
            regime = 'extreme'
        
        return {
            'current_vol_annualized': float(current_vol),
            'percentile_1y': percentile,
            'regime': regime,
            'regime_thresholds': {
                'low': '<10%',
                'normal': '10-18%',
                'elevated': '18-25%',
                'high': '25-40%',
                'extreme': '>40%',
            },
            'vol_trend': trend,
        }
