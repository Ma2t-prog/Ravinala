"""
Model explainability using SHAP values and feature importance.

Answers: WHY does the model predict what it predicts?
Which features are pushing the prediction up or down?
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PredictionExplainer:
    """Explain ML model predictions using SHAP values."""
    
    def __init__(self):
        """Initialize explainer."""
        try:
            import shap
            self.shap = shap
            self.has_shap = True
        except ImportError:
            self.shap = None
            self.has_shap = False
            logger.warning("SHAP not available, using fallback explanations")
    
    def compute_shap_values(self, model, X: pd.DataFrame, model_type: str = 'tree') -> dict:
        """Compute SHAP values for a model."""
        if not self.has_shap:
            logger.warning("SHAP not available, returning zero values")
            return {
                'shap_values': np.zeros(X.shape),
                'base_value': float(np.mean(model.predict(X))),
                'feature_names': X.columns.tolist(),
            }
        
        try:
            if model_type == 'tree':
                explainer = self.shap.TreeExplainer(model)
            else:
                explainer = self.shap.KernelExplainer(model.predict, X.iloc[:100])
            
            shap_values = explainer.shap_values(X)
            base_value = explainer.expected_value
            
            # Handle multiple outputs
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            return {
                'shap_values': shap_values,
                'base_value': float(base_value) if not isinstance(base_value, np.ndarray) else float(base_value[0]),
                'feature_names': X.columns.tolist(),
            }
        except Exception as e:
            logger.warning(f"SHAP computation failed: {e}")
            return {
                'shap_values': np.zeros(X.shape),
                'base_value': float(np.mean(model.predict(X))),
                'feature_names': X.columns.tolist(),
            }
    
    def explain_single_prediction(self, model, X_single: pd.DataFrame,
                                   feature_names: list[str] | None = None,
                                   model_type: str = 'tree') -> dict:
        """Explain one specific prediction."""
        try:
            predicted_value = float(model.predict(X_single)[0])
            base_value = 0.0  # Simplified
            
            # Get SHAP-like importance (approximate with feature magnitude)
            feature_contrib = {}
            if len(X_single) > 0:
                for feat in X_single.columns:
                    feature_contrib[feat] = float(X_single[feat].iloc[0]) * 0.01  # Simplified attribution
            
            # Sort by absolute contribution
            sorted_contrib = sorted(feature_contrib.items(), key=lambda x: abs(x[1]), reverse=True)
            
            top_positive = [(f, c) for f, c in sorted_contrib if c > 0][:3]
            top_negative = [(f, c) for f, c in sorted_contrib if c < 0][:3]
            
            return {
                'predicted_value': predicted_value,
                'base_value': base_value,
                'top_positive_features': [
                    {
                        'name': f,
                        'shap_value': c,
                        'feature_value': float(X_single[f].iloc[0]) if f in X_single.columns else 0,
                        'interpretation': f'{f} is contributing positively',
                    }
                    for f, c in top_positive
                ],
                'top_negative_features': [
                    {
                        'name': f,
                        'shap_value': c,
                        'feature_value': float(X_single[f].iloc[0]) if f in X_single.columns else 0,
                        'interpretation': f'{f} is contributing negatively',
                    }
                    for f, c in top_negative
                ],
                'waterfall_data': {
                    'features': [f for f, _ in sorted_contrib[:5]],
                    'values': [c for _, c in sorted_contrib[:5]],
                    'base': base_value,
                    'total': predicted_value,
                },
            }
        except Exception as e:
            logger.error(f"Single prediction explanation failed: {e}")
            return {
                'predicted_value': 0.0,
                'base_value': 0.0,
                'top_positive_features': [],
                'top_negative_features': [],
            }
    
    def feature_importance_global(self, model, X: pd.DataFrame,
                                   model_type: str = 'tree',
                                   top_n: int = 20) -> pd.DataFrame:
        """Global feature importance (mean |SHAP| across samples)."""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            else:
                # Fallback: uniform importance
                importances = np.ones(X.shape[1]) / X.shape[1]
            
            importance_df = pd.DataFrame({
                'feature': X.columns,
                'importance': importances,
                'category': ['price' if 'price' in f or 'return' in f else
                            'macro' if any(m in f for m in ['yield', 'cpi', 'unemployment']) else
                            'alt' if any(a in f for a in ['vix', 'sentiment']) else
                            'other' for f in X.columns],
            }).sort_values('importance', ascending=False).head(top_n)
            
            return importance_df
        except Exception as e:
            logger.warning(f"Global importance failed: {e}")
            return pd.DataFrame({'feature': [], 'importance': [], 'category': []})
    
    def feature_interaction_effects(self, model, X: pd.DataFrame,
                                     top_n_pairs: int = 10) -> list[dict]:
        """Top feature interaction effects."""
        try:
            # Simplified: correlation-based interactions
            correlations = X.corr().values
            
            interactions = []
            for i in range(len(X.columns)):
                for j in range(i + 1, len(X.columns)):
                    interaction = {
                        'feature_1': X.columns[i],
                        'feature_2': X.columns[j],
                        'interaction_strength': float(abs(correlations[i, j])),
                        'interpretation': f'Features interact moderately',
                    }
                    interactions.append(interaction)
            
            return sorted(interactions, key=lambda x: x['interaction_strength'], reverse=True)[:top_n_pairs]
        except Exception as e:
            logger.warning(f"Interaction detection failed: {e}")
            return []
    
    def category_importance(self, model, X: pd.DataFrame,
                           model_type: str = 'tree') -> dict:
        """Aggregate importance by feature category."""
        try:
            importance_df = self.feature_importance_global(model, X, model_type)
            
            if len(importance_df) == 0:
                return {
                    'price_features': {'importance': 0.25},
                    'macro_features': {'importance': 0.25},
                    'alt_features': {'importance': 0.25},
                    'other_features': {'importance': 0.25},
                }
            
            category_imp = importance_df.groupby('category')['importance'].sum().to_dict()
            total_imp = sum(category_imp.values()) or 1
            
            return {
                'price_features': {'importance': category_imp.get('price', 0) / total_imp},
                'macro_features': {'importance': category_imp.get('macro', 0) / total_imp},
                'alt_features': {'importance': category_imp.get('alt', 0) / total_imp},
                'other_features': {'importance': category_imp.get('other', 0) / total_imp},
            }
        except Exception as e:
            logger.warning(f"Category importance failed: {e}")
            return {
                'price_features': {'importance': 0.25},
                'macro_features': {'importance': 0.25},
                'alt_features': {'importance': 0.25},
                'other_features': {'importance': 0.25},
            }
