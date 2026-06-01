"""
Ravinala Volatility Calibration & Smile Module
Calibrate volatility surfaces, SABR model, smile/skew effects
"""

import numpy as np
from scipy.optimize import minimize
from typing import Tuple, Dict
import warnings

warnings.filterwarnings('ignore')


class VolatilitySurface:
    """Build and calibrate volatility surfaces."""

    @staticmethod
    def sabr_volatility(F: float, K: float, T: float, alpha: float, beta: float,
                        rho: float, nu: float) -> float:
        """
        SABR model (Hagan 2002) — captures smile/skew.

        Parameters:
            F: Forward price
            K: Strike
            T: Time to expiry
            alpha: ATM volatility level
            beta: CEV exponent (0=normal, 1=lognormal)
            rho: Spot-vol correlation
            nu: Vol of vol
        """
        log_fk = np.log(F / K) if F != K else 0.0
        fk_mid = (F * K) ** ((1 - beta) / 2)

        # Series expansion factor A (reduces to 1 when F == K)
        A = (1
             + ((1 - beta) ** 2 / 24) * log_fk ** 2
             + ((1 - beta) ** 4 / 1920) * log_fk ** 4)

        # z/χ(z) factor: forward displacement term
        if abs(log_fk) > 1e-8:
            z = (nu / alpha) * fk_mid * log_fk
            disc = np.sqrt(1 - 2 * rho * z + z ** 2)
            chi = np.log((disc + z - rho) / (1 - rho))
            zx_ratio = z / chi if abs(chi) > 1e-10 else 1.0
        else:
            zx_ratio = 1.0

        # Maturity correction term (T-dependent)
        corr = (
            ((1 - beta) * alpha) ** 2 / (24 * fk_mid ** 2)
            + rho * beta * nu * alpha / (4 * fk_mid)
            + (2 - 3 * rho ** 2) * nu ** 2 / 24
        )

        vol = (alpha / (fk_mid * A)) * zx_ratio * (1 + corr * T)
        return max(vol, 0.01)

    @staticmethod
    def fit_sabr_to_volatility_smile(strikes: np.ndarray, market_vols: np.ndarray,
                                     forward: float, T: float) -> Dict[str, float]:
        """
        Calibrate SABR parameters to market volatility smile via Nelder-Mead.

        Returns fitted parameters: {alpha, beta, rho, nu, fit_error}.
        """
        x0 = [market_vols[len(strikes) // 2], 1.0, 0.0, 0.3]

        def objective(params):
            alpha, beta, rho, nu = params
            rho = np.clip(rho, -0.99, 0.99)
            model_vols = np.array([
                VolatilitySurface.sabr_volatility(forward, K, T, alpha, beta, rho, nu)
                for K in strikes
            ])
            return np.sum((model_vols - market_vols) ** 2)

        result = minimize(objective, x0, method='Nelder-Mead',
                          options={'maxiter': 500, 'xatol': 1e-6})

        alpha, beta, rho, nu = result.x
        rho = np.clip(rho, -0.99, 0.99)

        return {
            'alpha': alpha,
            'beta': beta,
            'rho': rho,
            'nu': nu,
            'fit_error': result.fun,
        }

    @staticmethod
    def volatility_smile(strikes: np.ndarray, atm_spot: float, atm_vol: float,
                         smile_curvature: float = 0.1) -> np.ndarray:
        """
        Quadratic smile model.

        Vol(K) = ATM_Vol * (1 + smile_curvature * (K/S - 1)^2)
        """
        moneyness = strikes / atm_spot
        return atm_vol * (1 + smile_curvature * (moneyness - 1) ** 2)

    @staticmethod
    def volatility_skew(strikes: np.ndarray, atm_spot: float, atm_vol: float,
                        skew_slope: float = 0.02) -> np.ndarray:
        """
        Linear skew model.

        Vol(K) = ATM_Vol + skew_slope * (K/S - 1)

        Negative slope = negative skew (puts more expensive — equity crash protection).
        """
        moneyness = strikes / atm_spot
        skew = atm_vol + skew_slope * (moneyness - 1)
        return np.maximum(skew, 0.01)

    @staticmethod
    def model_volatility_term_structure(times: np.ndarray, long_run_vol: float,
                                        mean_reversion: float = 0.1,
                                        vol_of_vol: float = 0.3) -> np.ndarray:
        """
        Mean-reverting volatility term structure.

        Vol(T) = LongRunVol + (InitialVol - LongRunVol) * exp(-k * T)
        Current vol is assumed elevated at 1.2x long-run.
        """
        initial_vol = long_run_vol * 1.2
        return long_run_vol + (initial_vol - long_run_vol) * np.exp(-mean_reversion * times)

    @staticmethod
    def calculate_implied_vol_surface(spot: float, forward: float, T: float,
                                      rate: float, dividends: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Build 2D implied vol surface: (Strike, Time) → Implied Vol."""
        strikes = np.linspace(spot * 0.8, spot * 1.2, 21)
        times = np.linspace(0.1, T, 5)

        surface = np.zeros((len(times), len(strikes)))
        for i, t in enumerate(times):
            atm_vol = 0.20 * np.sqrt(T / t)
            surface[i, :] = VolatilitySurface.volatility_smile(strikes, spot, atm_vol, 0.08)

        return strikes, times, surface


class CalibratedPricer:
    """Price using calibrated volatility surfaces."""

    @staticmethod
    def price_with_smile(spot: float, strike: float, T: float, rate: float,
                         carry: float, atm_vol: float, smileclass_type: str = 'smile') -> float:
        """
        Price an option using smile-adjusted volatility.

        smileclass_type: 'smile' (quadratic) or 'skew' (linear).
        """
        from engine import BlackScholesGreeks

        bs = BlackScholesGreeks()
        moneyness = strike / spot

        if smileclass_type == 'smile':
            adjusted_vol = atm_vol * (1 + 0.10 * (moneyness - 1) ** 2)
        else:
            adjusted_vol = atm_vol + 0.02 * (moneyness - 1)

        adjusted_vol = max(adjusted_vol, 0.01)
        return bs.call_price(spot, strike, T, rate, carry, adjusted_vol)


class VolatilityForecasting:
    """Forecast future volatilities."""

    @staticmethod
    def ewma_volatility(returns: np.ndarray, lambda_param: float = 0.94) -> np.ndarray:
        """
        Exponentially-Weighted Moving Average volatility.

        RiskMetrics standard: lambda = 0.94 (daily).
        """
        squared_returns = returns ** 2
        variance = np.zeros(len(returns))
        variance[0] = np.var(returns)

        for t in range(1, len(returns)):
            variance[t] = lambda_param * variance[t - 1] + (1 - lambda_param) * squared_returns[t - 1]

        return np.sqrt(variance)

    @staticmethod
    def garch_volatility(returns: np.ndarray, p: int = 1, q: int = 1,
                         n_forecast: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simple GARCH(1,1) volatility model.

        Variance_t = omega + alpha * epsilon^2_{t-1} + beta * Variance_{t-1}
        Parameters are fixed (simplified, not MLE-fitted).
        """
        mean_return = np.mean(returns)
        residuals = returns - mean_return

        omega = 0.00001
        alpha = 0.1
        beta = 0.85

        variance = np.zeros(len(returns))
        variance[0] = np.var(returns)

        for t in range(1, len(returns)):
            variance[t] = omega + alpha * residuals[t - 1] ** 2 + beta * variance[t - 1]

        forecast_variance = np.zeros(n_forecast)
        forecast_variance[0] = variance[-1]

        for t in range(1, n_forecast):
            forecast_variance[t] = omega + (alpha + beta) * forecast_variance[t - 1]

        return np.sqrt(variance), np.sqrt(forecast_variance)

    @staticmethod
    def realized_volatility(price_series: np.ndarray, frequency: str = 'daily') -> float:
        """
        Compute annualized realized volatility from a price series.

        frequency: 'daily' (annualizes by sqrt(252)) or 'minute' (sqrt(252 * 390)).
        """
        returns = np.diff(np.log(price_series))

        if frequency == 'daily':
            return np.std(returns) * np.sqrt(252)
        elif frequency == 'minute':
            return np.std(returns) * np.sqrt(252 * 390)
        else:
            return np.std(returns)
