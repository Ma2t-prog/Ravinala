"""
MLflow model loader — load the latest registered model for inference.

Graceful degradation: if MLflow is unavailable, falls back to joblib artifacts.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "data" / "ml_artifacts"

try:
    import mlflow
    HAS_MLFLOW = True
except ImportError:
    mlflow = None
    HAS_MLFLOW = False

try:
    import joblib
except ImportError:
    joblib = None


def load_latest_model(model_name: str):
    """Load the latest model, trying MLflow first then joblib fallback.

    Args:
        model_name: Model type name (e.g. 'xgboost', 'lightgbm', 'random_forest')

    Returns:
        Loaded model object or None if unavailable.
    """
    # Try MLflow registry first
    if HAS_MLFLOW:
        try:
            model_uri = f"models:/{model_name}/latest"
            model = mlflow.sklearn.load_model(model_uri)
            logger.info(f"Loaded {model_name} from MLflow registry")
            return model
        except Exception as e:
            logger.debug(f"MLflow load failed for {model_name}: {e}")

    # Fallback: find latest joblib artifact
    if joblib is not None and ARTIFACTS_DIR.exists():
        artifacts = sorted(
            ARTIFACTS_DIR.glob(f"{model_name}_*.joblib"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if artifacts:
            model = joblib.load(artifacts[0])
            logger.info(f"Loaded {model_name} from {artifacts[0]}")
            return model

    logger.warning(f"No model found for {model_name}")
    return None
