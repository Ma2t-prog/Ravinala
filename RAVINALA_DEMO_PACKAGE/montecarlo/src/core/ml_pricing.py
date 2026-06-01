"""
Ravinala Machine Learning Pricing Module
ML models for price prediction and anomaly detection
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from typing import Dict, List
import warnings

warnings.filterwarnings('ignore')


class MLPricingPredictor:
    """Machine learning-based pricing and prediction."""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None

    @staticmethod
    def extract_features(spot: float, strike: float, T: float, rate: float,
                         vol: float, carry: float, moneyness: float = None,
                         time_decay: float = None, vol_skew: float = None) -> np.ndarray:
        """
        Extract features for ML model.

        Features: moneyness, T, vol, rate, carry, vega proxy, theta proxy,
        gamma proxy, log-moneyness, vol^2, drift, skew.
        """
        mon = moneyness if moneyness is not None else strike / spot
        skew = vol_skew if vol_skew is not None else 0.0

        features = [
            mon,
            T,
            vol,
            rate,
            carry,
            spot * vol * np.sqrt(T),
            vol / np.sqrt(T + 1e-6),
            1 / (spot * vol * np.sqrt(T) + 1e-6),
            np.log(strike / spot),
            vol * vol,
            rate * T,
            skew,
        ]

        return np.array(features).reshape(1, -1)

    @staticmethod
    def _features_from_arrays(spots: np.ndarray, strikes: np.ndarray, Ts: np.ndarray,
                               rates: np.ndarray, vols: np.ndarray, carries: np.ndarray,
                               skews: np.ndarray = None) -> np.ndarray:
        """Vectorized batch feature extraction from numpy arrays."""
        if skews is None:
            skews = np.zeros(len(spots))
        sqrt_T = np.sqrt(Ts)
        return np.column_stack([
            strikes / spots,                          # moneyness
            Ts,
            vols,
            rates,
            carries,
            spots * vols * sqrt_T,                   # vega proxy
            vols / np.sqrt(Ts + 1e-6),               # theta proxy
            1.0 / (spots * vols * sqrt_T + 1e-6),    # gamma proxy
            np.log(strikes / spots),                  # log-moneyness
            vols ** 2,
            rates * Ts,                               # drift
            skews,
        ])

    def train_on_synthetic_data(self, n_samples: int = 10000, test_split: float = 0.2,
                                random_seed: int = 42):
        """
        Train ML model on synthetic Black-Scholes data.

        Useful as baseline before real data is available.
        Returns performance metrics.
        """
        from scipy.stats import norm as _norm

        np.random.seed(random_seed)

        spots = np.random.uniform(90, 110, n_samples)
        strikes = np.random.uniform(80, 120, n_samples)
        Ts = np.random.uniform(0.1, 2.0, n_samples)
        rates = np.random.uniform(0.01, 0.08, n_samples)
        vols = np.random.uniform(0.10, 0.50, n_samples)
        carries = rates - np.random.uniform(0, 0.05, n_samples)

        # Vectorized feature extraction (avoids n_samples Python function calls)
        X = self._features_from_arrays(spots, strikes, Ts, rates, vols, carries)

        # Vectorized Black-Scholes call prices (avoids n_samples Python loops)
        sqrt_T = np.sqrt(Ts)
        d1 = (np.log(spots / strikes) + (carries + 0.5 * vols ** 2) * Ts) / (vols * sqrt_T)
        d2 = d1 - vols * sqrt_T
        y = spots * np.exp((carries - rates) * Ts) * _norm.cdf(d1) - strikes * np.exp(-rates * Ts) * _norm.cdf(d2)

        train_size = int(n_samples * (1 - test_split))
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model = GradientBoostingRegressor(n_estimators=100, max_depth=7,
                                               learning_rate=0.1, random_state=random_seed)
        self.model.fit(X_train_scaled, y_train)
        self.feature_importance = self.model.feature_importances_

        train_pred = self.model.predict(X_train_scaled)
        test_pred = self.model.predict(X_test_scaled)

        train_r2 = 1 - np.sum((y_train - train_pred) ** 2) / np.sum((y_train - np.mean(y_train)) ** 2)
        test_r2 = 1 - np.sum((y_test - test_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)
        test_rmse = np.sqrt(np.mean((y_test - test_pred) ** 2))

        return {
            'model': self.model,
            'train_r2': train_r2,
            'test_r2': test_r2,
            'test_rmse': test_rmse,
        }

    def predict_price(self, spot: float, strike: float, T: float, rate: float,
                      vol: float, carry: float) -> float:
        """Predict option price using ML model (trains on synthetic data if needed)."""
        if self.model is None:
            self.train_on_synthetic_data()

        X = self.extract_features(spot, strike, T, rate, vol, carry)
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)[0]

    def predict_batch(self, params_list: List[Dict]) -> np.ndarray:
        """Batch predict prices for multiple options."""
        if self.model is None:
            self.train_on_synthetic_data()

        spots    = np.array([p['spot']   for p in params_list])
        strikes  = np.array([p['strike'] for p in params_list])
        Ts       = np.array([p['T']      for p in params_list])
        rates    = np.array([p['rate']   for p in params_list])
        vols     = np.array([p['vol']    for p in params_list])
        carries  = np.array([p['carry']  for p in params_list])

        X = self._features_from_arrays(spots, strikes, Ts, rates, vols, carries)
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importances from the trained model."""
        feature_names = [
            'Moneyness', 'Time', 'Volatility', 'Rate', 'Carry',
            'Vega_Proxy', 'Theta_Proxy', 'Gamma_Proxy', 'Log_Moneyness',
            'Vol_Squared', 'Drift', 'Skew'
        ]

        if self.feature_importance is None:
            return {}

        return dict(zip(feature_names, self.feature_importance))


class AnomalyDetection:
    """Detect unusual prices or market conditions."""

    @staticmethod
    def detect_price_anomaly(actual_price: float, expected_price: float,
                             expected_std: float, threshold_std: float = 3.0) -> Dict:
        """
        Detect if a price is anomalously different from expectation.

        Uses the 3-sigma rule: |z-score| > threshold_std flags the price as unusual.
        """
        z_score = (actual_price - expected_price) / (expected_std + 1e-6)
        is_anomaly = abs(z_score) > threshold_std

        return {
            'z_score': z_score,
            'is_anomaly': is_anomaly,
            'expected_price': expected_price,
            'actual_price': actual_price,
            'confidence': min(abs(z_score) / threshold_std * 100, 100),
        }

    @staticmethod
    def detect_volatility_spike(vol_history: np.ndarray, current_vol: float,
                                threshold: float = 2.0) -> bool:
        """Alert if current vol exceeds mean + threshold * std of the last 30 observations."""
        recent_vol = vol_history[-30:]
        mean_vol = np.mean(recent_vol)
        std_vol = np.std(recent_vol)
        return current_vol > mean_vol + threshold * std_vol

    @staticmethod
    def detect_correlation_breakdown(correlation: float, historical_corr: np.ndarray,
                                     threshold: float = 2.0) -> bool:
        """Flag if correlation deviates beyond threshold sigmas from historical norm (tail risk)."""
        mean_corr = np.mean(historical_corr)
        std_corr = np.std(historical_corr)
        z_score = (correlation - mean_corr) / (std_corr + 1e-6)
        return abs(z_score) > threshold

    @staticmethod
    def detect_greeks_inconsistency(delta: float, gamma: float, vega: float,
                                    spot: float, vol: float, T: float) -> Dict:
        """Check if Greeks are internally consistent for a long vanilla call."""
        issues = []

        if abs(delta) > 1.0 or delta < 0:
            issues.append("Delta out of reasonable range for call")
        if gamma < 0:
            issues.append("Gamma negative (short option detected)")
        if vega < 0:
            issues.append("Vega negative (unusual for vanilla options)")
        if T > 0.1 and vega < 0.1:
            issues.append("Vega too low for long-dated option")

        return {
            'is_consistent': len(issues) == 0,
            'issues': issues,
            'number_of_issues': len(issues),
        }


class ModelComparisonEngine:
    """Compare different pricing models on the same input."""

    @staticmethod
    def compare_models(spot: float, strike: float, T: float, rate: float,
                       vol: float, carry: float, option_type: str = 'call') -> Dict:
        """
        Price using Black-Scholes, ML, and Monte Carlo, then compare.
        """
        from engine import BlackScholesGreeks, MultiAssetPricer

        bs = BlackScholesGreeks()

        if option_type == 'call':
            bs_price = bs.call_price(spot, strike, T, rate, carry, vol)
        else:
            bs_price = bs.put_price(spot, strike, T, rate, carry, vol)

        ml_predictor = MLPricingPredictor()
        ml_price = ml_predictor.predict_price(spot, strike, T, rate, vol, carry)

        mc = MultiAssetPricer(n_simulations=5000, random_seed=42)
        spots_array = np.array([spot])
        vols_array = np.array([vol])
        carries_array = np.array([carry])
        corr_matrix = np.array([[1.0]])

        paths = mc.simulate_paths(spots_array, carries_array, vols_array, T, 252, corr_matrix)
        payoffs = np.maximum(paths[:, -1, 0] - strike, 0)
        mc_price = np.mean(payoffs) * np.exp(-rate * T)

        return {
            'black_scholes': bs_price,
            'ml_prediction': ml_price,
            'monte_carlo': mc_price,
            'bs_vs_ml_diff': abs(bs_price - ml_price) / (bs_price + 1e-6) * 100,
            'bs_vs_mc_diff': abs(bs_price - mc_price) / (bs_price + 1e-6) * 100,
            'all_agree': abs(bs_price - ml_price) < 0.01 and abs(bs_price - mc_price) < 0.01,
        }
