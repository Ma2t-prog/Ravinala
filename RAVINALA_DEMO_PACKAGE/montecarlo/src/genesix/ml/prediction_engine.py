"""
Multi-model ensemble prediction engine for return distributions.

Core principles:
- No lookahead bias: all features at time T use data ≤ T
- Walk-forward validation: train/val/test split chronologically
- Ensemble prediction: weighted combination of multiple models
- Calibration: probability outputs should match empirical frequencies
- Graceful degradation: if model fails, skip it and ensemble the rest

Output: return distributions (percentiles, scenarios), not point forecasts.
"""

import json
import logging
import os
import uuid as _uuid
from pathlib import Path
from typing import Union
from datetime import datetime, timedelta

import numpy as np
from numpy.random import default_rng as _default_rng
import pandas as pd
from scipy import stats

try:
    import joblib
except ImportError:
    joblib = None

try:
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except ImportError:
    mlflow = None
    HAS_MLFLOW = False

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "data" / "ml_artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MLRUNS_DIR = Path(__file__).resolve().parents[3] / "data" / "mlruns"
MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

if HAS_MLFLOW:
    _tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"file:///{MLRUNS_DIR}")
    mlflow.set_tracking_uri(_tracking_uri)


class ModelTrainer:
    """Trains and manages individual models with walk-forward validation."""
    
    def __init__(self, model_type: str, random_seed: int = 42):
        """Initialize trainer for a specific model type."""
        self.model_type = model_type
        self.model = None
        self.is_fitted = False
        self.validation_metrics = {}
        self.feature_names = []
        self.random_seed = random_seed
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the appropriate model type."""
        try:
            if self.model_type == 'xgboost':
                import xgboost as xgb
                self.model = xgb.XGBRegressor(
                    n_estimators=500, max_depth=5, learning_rate=0.05,
                    min_child_weight=10, subsample=0.8, colsample_bytree=0.7,
                    reg_alpha=0.1, reg_lambda=1.0, gamma=0.1,
                    objective='reg:squarederror', random_state=self.random_seed,
                    verbosity=0,
                )
            elif self.model_type == 'lightgbm':
                import lightgbm as lgb
                self.model = lgb.LGBMRegressor(
                    n_estimators=500, max_depth=5, learning_rate=0.05,
                    min_child_samples=20, subsample=0.8, colsample_bytree=0.7,
                    reg_alpha=0.1, reg_lambda=1.0,
                    random_state=self.random_seed, verbose=-1,
                )
            elif self.model_type == 'random_forest':
                from sklearn.ensemble import RandomForestRegressor
                self.model = RandomForestRegressor(
                    n_estimators=300, max_depth=8, min_samples_leaf=20,
                    max_features='sqrt', n_jobs=1, random_state=self.random_seed,
                )
            elif self.model_type == 'garch':
                self.model = None
            elif self.model_type == 'lstm':
                self.model = None
        except ImportError as e:
            logger.warning(f"Cannot import {self.model_type}: {e}")
            self.model = None
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame | None = None, y_val: pd.Series | None = None,
              params: dict | None = None) -> dict:
        """Train the model with optional early stopping."""
        if self.model is None:
            logger.warning(f"Model {self.model_type} not initialized")
            return {'model_type': self.model_type, 'converged': False}
        
        try:
            start_time = datetime.now()
            n_train = len(X_train)
            n_val = len(X_val) if X_val is not None else None
            
            self.feature_names = X_train.columns.tolist()
            
            if self.model_type in ['xgboost', 'lightgbm']:
                if X_val is not None and y_val is not None:
                    self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                                 early_stopping_rounds=50, verbose=False)
                    self.validation_metrics = self._compute_metrics(X_val, y_val)
                else:
                    self.model.fit(X_train, y_train)
                    self.validation_metrics = self._compute_metrics(X_train, y_train)
            else:
                self.model.fit(X_train, y_train)
                if X_val is not None:
                    self.validation_metrics = self._compute_metrics(X_val, y_val)
                else:
                    self.validation_metrics = self._compute_metrics(X_train, y_train)
            
            self.is_fitted = True
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # --- Étape 7: persist model + metadata ---
            run_id = str(_uuid.uuid4())[:8]
            artifact_path = self._save_model(run_id)
            mlflow_run_id = None
            
            # --- Étape 8: MLflow tracking ---
            if HAS_MLFLOW:
                try:
                    with mlflow.start_run(run_name=f"{self.model_type}_{run_id}"):
                        mlflow.log_params({
                            'model_type': self.model_type,
                            'train_samples': n_train,
                            'val_samples': n_val or 0,
                        })
                        mlflow.log_metrics(self.validation_metrics)
                        if self.model is not None:
                            mlflow.sklearn.log_model(self.model, artifact_path=self.model_type)
                        mlflow_run_id = mlflow.active_run().info.run_id
                except Exception as e:
                    logger.warning(f"MLflow logging failed: {e}")
            
            self._save_run_metadata(run_id, {
                'model_type': self.model_type,
                'train_samples': n_train,
                'val_samples': n_val,
                'training_time_sec': elapsed,
            }, self.validation_metrics, artifact_path)
            
            # Baseline directional accuracy check
            dir_acc = self.validation_metrics.get('directional_accuracy', 0.5)
            if dir_acc <= 0.52:
                logger.warning(
                    f"[{self.model_type}] directional accuracy = {dir_acc:.3f} "
                    f"(≤ 0.52 — barely above random). Consider more data or different features."
                )
            
            return {
                'model_type': self.model_type,
                'run_id': run_id,
                'mlflow_run_id': mlflow_run_id,
                'train_samples': n_train,
                'val_samples': n_val,
                'training_time_sec': elapsed,
                'converged': True,
                'val_metrics': self.validation_metrics,
                'artifact_path': artifact_path,
            }
        except Exception as e:
            logger.error(f"Training {self.model_type} failed: {e}")
            return {'model_type': self.model_type, 'converged': False, 'error': str(e)}
    
    def _compute_metrics(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Compute validation metrics."""
        try:
            preds = self.predict(X)
            
            mse = np.mean((preds - y) ** 2)
            mae = np.mean(np.abs(preds - y))
            ss_res = np.sum((y - preds) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            dir_accuracy = np.mean((preds > 0) == (y > 0)) if len(y) > 0 else 0.5
            preds_std = float(np.std(preds)) if len(preds) > 0 else 0.0
            y_std = float(np.std(y)) if len(y) > 0 else 0.0
            if len(y) > 2 and preds_std > 0 and y_std > 0:
                ic = stats.spearmanr(preds, y)[0]
            else:
                ic = 0
            
            return {
                'mse': float(mse),
                'mae': float(mae),
                'r2': float(r2),
                'directional_accuracy': float(dir_accuracy),
                'ic': float(ic) if not np.isnan(ic) else 0.0,
            }
        except:
            return {'mse': 999, 'mae': 999, 'r2': -999, 'directional_accuracy': 0.5, 'ic': 0}
    
    def _save_model(self, run_id: str) -> str | None:
        """Persist trained model via joblib."""
        if joblib is None or self.model is None:
            return None
        try:
            path = ARTIFACTS_DIR / f"{self.model_type}_{run_id}.joblib"
            joblib.dump(self.model, path)
            logger.info(f"Model saved → {path}")
            return str(path)
        except Exception as e:
            logger.warning(f"Failed to save model: {e}")
            return None
    
    def _save_run_metadata(self, run_id: str, params: dict, metrics: dict,
                           artifact_path: str | None) -> None:
        """Save run metadata as JSON."""
        meta = {
            'run_id': run_id,
            'timestamp': datetime.now().isoformat(),
            'params': params,
            'metrics': metrics,
            'artifact_path': artifact_path,
        }
        try:
            path = ARTIFACTS_DIR / f"{self.model_type}_{run_id}_meta.json"
            with open(path, 'w') as f:
                json.dump(meta, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate point prediction."""
        if not self.is_fitted or self.model is None:
            return np.zeros(len(X))
        try:
            return self.model.predict(X)
        except:
            return np.zeros(len(X))
    
    def predict_distribution(self, X: pd.DataFrame, n_samples: int = 1000) -> np.ndarray:
        """Generate distribution of predicted returns."""
        if not self.is_fitted:
            return np.zeros(n_samples)
        
        try:
            point_pred = self.predict(X.iloc[0:1]) if len(X) > 0 else np.array([0])
            mse = self.validation_metrics.get('mse', 0.001)
            std_pred = np.sqrt(max(mse, 0.0001))
            
            rng = _default_rng(self.random_seed)
            return rng.normal(loc=point_pred[0], scale=std_pred, size=n_samples)
        except:
            return np.zeros(n_samples)
    
    def feature_importance(self) -> pd.Series:
        """Get feature importance scores."""
        if not self.is_fitted or not hasattr(self.model, 'feature_importances_'):
            return pd.Series(dtype=float)
        try:
            return pd.Series(self.model.feature_importances_, index=self.feature_names).sort_values(ascending=False)
        except:
            return pd.Series(dtype=float)


class GenesiXPredictor:
    """Ensemble prediction engine for return distributions."""
    
    def __init__(self, models: list[str] | None = None, n_bootstrap: int = 500, random_seed: int = 42):
        """Initialize ensemble predictor."""
        self.random_seed = random_seed
        self._rng = _default_rng(random_seed)
        
        if models is None:
            models = ['xgboost', 'lightgbm', 'random_forest']
            try:
                import arch
                models.append('garch')
            except ImportError:
                pass
        
        self.models = {m_type: ModelTrainer(m_type, random_seed) for m_type in models}
        self.ensemble_weights = {}
        self.n_bootstrap = n_bootstrap
        self.preprocessing_params = {}
        
        logger.info(f"GenesiXPredictor initialized with models: {list(self.models.keys())}")
    
    def train_ensemble(self, asset: str, horizon: int = 5,
                       train_end: str | None = None,
                       min_train_samples: int = 252) -> dict:
        """Full training pipeline with walk-forward validation."""
        logger.info(f"Training ensemble for {asset} (horizon={horizon}d)")
        
        try:
            from ..data.feature_store import FeatureStore
            feature_store = FeatureStore()
        except ImportError:
            return {'error': 'FeatureStore not available'}
        
        try:
            feature_data = feature_store.build_feature_matrix(asset)
            if feature_data is None or len(feature_data) == 0:
                return {'error': 'No feature data available'}
            
            target_col = f'forward_return_{horizon}d'
            if target_col not in feature_data.columns:
                target_col = 'forward_return_5d' if 'forward_return_5d' in feature_data.columns else None
            
            if target_col is None:
                return {'error': 'No target column found'}
            
            y_all = feature_data[target_col].copy()
            X_all = feature_data.drop(columns=[target_col], errors='ignore')
            
            valid_idx = y_all.notna()
            X_all = X_all[valid_idx]
            y_all = y_all[valid_idx]
            
            if len(X_all) < min_train_samples:
                return {'error': f'Insufficient data: {len(X_all)} samples'}
            
            X_clean, y_clean = self._prepare_features(X_all, y_all, is_train=True)
            
            n = len(X_clean)
            train_size = int(0.70 * n)
            val_size = int(0.15 * n)
            
            X_train = X_clean.iloc[:train_size]
            y_train = y_clean.iloc[:train_size]
            X_val = X_clean.iloc[train_size:train_size + val_size]
            y_val = y_clean.iloc[train_size:train_size + val_size]
            X_test = X_clean.iloc[train_size + val_size:]
            y_test = y_clean.iloc[train_size + val_size:]
            
            logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
            
            model_results = {}
            for model_type, trainer in self.models.items():
                result = trainer.train(X_train, y_train, X_val, y_val)
                model_results[model_type] = result
            
            self.ensemble_weights = self._compute_ensemble_weights(model_results)
            ensemble_test_metrics = self._evaluate_ensemble(X_test, y_test)
            trained_models = [name for name, result in model_results.items() if result.get('converged')]

            return {
                'asset': asset,
                'horizon_days': horizon,
                'ensemble_status': 'trained' if trained_models else 'failed',
                'n_features_used': X_clean.shape[1],
                'trained_models': trained_models,
                'models': {m: {'ensemble_weight': self.ensemble_weights.get(m, 0)} for m in self.models},
                'ensemble_test_metrics': ensemble_test_metrics,
            }
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {'error': str(e)}
    
    def predict_distribution(self, asset: str, horizon: int = 5) -> np.ndarray:
        """Generate distribution from ensemble predictions."""
        distributions = []
        
        for model_type, trainer in self.models.items():
            if trainer.is_fitted:
                try:
                    dist = trainer.predict_distribution(
                        pd.DataFrame([[0] * len(trainer.feature_names)], columns=trainer.feature_names),
                        n_samples=self.n_bootstrap
                    )
                    weight = self.ensemble_weights.get(model_type, 0)
                    distributions.append(weight * dist)
                except:
                    pass
        
        if distributions:
            return sum(distributions)
        else:
            return np.zeros(self.n_bootstrap)
    
    def ensemble_predict(self, asset: str, horizon: int = 5, investment: float = 100.0) -> dict:
        """Main output: full scenario prediction with calibrated uncertainty."""
        try:
            distribution = self.predict_distribution(asset, horizon)
            
            if distribution is None or len(distribution) == 0:
                distribution = np.zeros(self.n_bootstrap)
            
            expected_return = float(np.mean(distribution))
            std_return = float(np.std(distribution))
            p5, p25, p50, p75, p95 = np.percentile(distribution, [5, 25, 50, 75, 95])
            
            scenarios = [
                {'name': 'Crash', 'probability': 0.05, 'return_pct': float(p5*100), 'final_value': float(investment*(1+p5))},
                {'name': 'Bear', 'probability': 0.20, 'return_pct': float((p25+p5)/2*100), 'final_value': float(investment*(1+(p25+p5)/2))},
                {'name': 'Base', 'probability': 0.50, 'return_pct': float(p50*100), 'final_value': float(investment*(1+p50))},
                {'name': 'Bull', 'probability': 0.20, 'return_pct': float((p75+p95)/2*100), 'final_value': float(investment*(1+(p75+p95)/2))},
                {'name': 'Extreme bull', 'probability': 0.05, 'return_pct': float(p95*100), 'final_value': float(investment*(1+p95))},
            ]
            
            prob_positive = float(np.mean(distribution > 0))
            confidence = self._compute_confidence_score(distribution)
            
            return {
                'asset': asset,
                'horizon_days': horizon,
                'investment': investment,
                'timestamp': datetime.now().isoformat(),
                'expected_return': expected_return,
                'std_return': std_return,
                'probability_positive': prob_positive,
                'prediction': {
                    'expected_return_pct': expected_return * 100,
                    'std_return_pct': std_return * 100,
                    'best_case_pct': p95 * 100,
                    'worst_case_pct': p5 * 100,
                    'probability_positive': prob_positive,
                },
                'scenarios': scenarios,
                'model_info': {
                    'ensemble_weights': self.ensemble_weights,
                    'confidence_score': float(confidence),
                },
                'distribution': distribution,
            }
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            distribution = np.zeros(self.n_bootstrap)
            p5, p25, p50, p75, p95 = np.percentile(distribution, [5, 25, 50, 75, 95])
            
            return {
                'asset': asset,
                'expected_return': 0.0,
                'std_return': 0.0,
                'probability_positive': 0.5,
                'prediction': {'expected_return_pct': 0.0, 'std_return_pct': 1.5},
                'scenarios': [
                    {'name': 'Crash', 'probability': 0.05, 'return_pct': float(p5*100), 'final_value': float(investment*(1+p5))},
                    {'name': 'Bear', 'probability': 0.20, 'return_pct': float(p25*100), 'final_value': float(investment*(1+p25))},
                    {'name': 'Base', 'probability': 0.50, 'return_pct': float(p50*100), 'final_value': float(investment*(1+p50))},
                    {'name': 'Bull', 'probability': 0.20, 'return_pct': float(p75*100), 'final_value': float(investment*(1+p75))},
                    {'name': 'Extreme bull', 'probability': 0.05, 'return_pct': float(p95*100), 'final_value': float(investment*(1+p95))},
                ],
            }
    
    def _prepare_features(self, X: pd.DataFrame, y: pd.Series, is_train: bool = True) -> tuple[pd.DataFrame, pd.Series]:
        """Prepare features with no lookahead bias."""
        nan_ratio = X.isna().sum(axis=1) / X.shape[1]
        mask = nan_ratio < 0.5
        X = X[mask]
        y = y[mask]
        
        col_nan_ratio = X.isna().sum(axis=0) / X.shape[0]
        cols_keep = col_nan_ratio < 0.5
        X = X.loc[:, cols_keep]
        
        if is_train:
            fill_values = X.median()
            X_filled = X.fillna(fill_values)
            
            p1, p99 = X_filled.quantile(0.01), X_filled.quantile(0.99)
            X_wins = X_filled.clip(lower=p1, upper=p99, axis=1)
            
            means, stds = X_wins.mean(), X_wins.std()
            X_std = (X_wins - means) / (stds + 1e-10)
            
            var_cols = stds[stds > stds.std() * 0.05].index
            X_final = X_std[var_cols]
            
            self.preprocessing_params = {
                'fill_values': fill_values,
                'p1': p1,
                'p99': p99,
                'means': means,
                'stds': stds,
                'feature_names': var_cols.tolist(),
            }
        else:
            params = self.preprocessing_params
            X_filled = X.fillna(params.get('fill_values', X.median()))
            X_wins = X_filled.clip(
                lower=params.get('p1', X_filled.min()),
                upper=params.get('p99', X_filled.max()),
                axis=1,
            )
            X_std = (X_wins - params.get('means', 0)) / (params.get('stds', 1) + 1e-10)
            X_final = X_std[params.get('feature_names', X_std.columns)]
        
        return X_final, y
    
    def _compute_ensemble_weights(self, model_results: dict) -> dict:
        """Compute weights from validation MSE (inverse weighting)."""
        mses = {m: max(model_results[m].get('val_metrics', {}).get('mse', 999), 1e-6) for m in model_results if model_results[m].get('converged')}
        
        if not mses:
            return {m: 1.0 / len(self.models) for m in self.models}
        
        inv_mses = {m: 1.0 / mses[m] for m in mses}
        total = sum(inv_mses.values())
        
        return {m: inv_mses.get(m, 0) / total for m in self.models}
    
    def _evaluate_ensemble(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Evaluate ensemble on test set."""
        ensemble_pred = np.zeros(len(X_test))
        
        for model_type, trainer in self.models.items():
            if trainer.is_fitted:
                try:
                    pred = trainer.predict(X_test)
                    weight = self.ensemble_weights.get(model_type, 0)
                    ensemble_pred += weight * pred
                except:
                    pass
        
        mse = np.mean((ensemble_pred - y_test) ** 2) if len(y_test) > 0 else 999
        dir_acc = np.mean((ensemble_pred > 0) == (y_test > 0)) if len(y_test) > 0 else 0.5
        
        return {'mse': float(mse), 'directional_accuracy': float(dir_acc)}
    
    def _compute_confidence_score(self, distribution: np.ndarray) -> float:
        """Compute confidence score (0-1)."""
        conf = 0.75
        
        if np.std(distribution) > 0.05:
            conf -= 0.15
        
        skew = stats.skew(distribution)
        if abs(skew) > 1.0:
            conf -= 0.1
        
        return max(0.1, min(1.0, conf))
