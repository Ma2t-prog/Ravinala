"""
MLAgent — machine learning inventory, training and prediction.

This node must stay honest:
- if real prediction/training inputs are missing, it reports `not_executed`
- if an execution fails, it reports an error instead of fabricating metrics
- otherwise it delegates to the shared backend ML services
"""

from __future__ import annotations

import logging
import time
from typing import Any

from langgraph.config import get_stream_writer

from app.core.executor import get_shared_executor
from app.services.ml_service import (
    ArtifactNotFoundError,
    InvalidModelTypeError,
    PredictionExecutionError,
    PriceFetchError,
    build_train_response,
    fetch_runs,
    list_model_artifacts,
    run_prediction,
    run_training,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "MLAgent"


def _counts_by_model_type(models: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in models:
        model_type = getattr(model, "model_type", None) or model.get("model_type", "unknown")
        counts[model_type] = counts.get(model_type, 0) + 1
    return counts


async def ml_agent_node(state: dict) -> dict:
    """Run an honest ML workflow against the backend ML services."""
    writer = get_stream_writer()
    started_at = time.time()

    params = state.get("params", {})
    task = params.get("task", "inventory")
    asset = params.get("asset") or params.get("ticker")
    run_id = params.get("run_id")
    period = params.get("period", "1y")
    horizon_days = int(params.get("horizon_days", 5))
    model_type = params.get("model_type", "random_forest")

    writer(
        {
            "agent": AGENT_NAME,
            "event": "ml_start",
            "data": {"task": task, "asset": asset, "run_id": run_id, "model_type": model_type},
            "status": "running",
            "progress": 0.0,
            "timestamp": time.time(),
        }
    )

    try:
        artifacts = list_model_artifacts()
        recent_runs = await fetch_runs(asset=asset, model_type=None, limit=5)
        writer(
            {
                "agent": AGENT_NAME,
                "event": "ml_inventory",
                "data": {
                    "available_artifacts": len(artifacts),
                    "available_runs": len(recent_runs),
                    "model_counts": _counts_by_model_type(artifacts),
                },
                "status": "running",
                "progress": 0.25,
                "timestamp": time.time(),
            }
        )

        ml_result: dict[str, Any] = {
            "source": "ml_service",
            "task": task,
            "status": "completed",
            "available_artifacts": len(artifacts),
            "available_runs": len(recent_runs),
            "model_inventory": [model.model_dump() for model in artifacts[:10]],
            "recent_runs": [run.model_dump() for run in recent_runs],
        }

        if task == "predict":
            if not asset or not run_id:
                ml_result.update(
                    {
                        "status": "not_executed",
                        "reason": "predict requires both asset and run_id",
                    }
                )
                writer(
                    {
                        "agent": AGENT_NAME,
                        "event": "ml_skipped",
                        "data": {"reason": ml_result["reason"]},
                        "status": "completed",
                        "progress": 1.0,
                        "timestamp": time.time(),
                    }
                )
                return {
                    "ml_data": ml_result,
                    "agents_completed": [AGENT_NAME],
                }

            prediction = await run_prediction(
                asset=asset,
                run_id=run_id,
                horizon_days=horizon_days,
                period=period,
                executor=get_shared_executor(),
            )
            ml_result.update(
                {
                    "prediction": prediction.model_dump(),
                    "confidence": prediction.confidence,
                    "predicted_direction": prediction.predicted_direction,
                    "predicted_return": prediction.predicted_return,
                    "run_id": prediction.run_id,
                    "asset": prediction.asset,
                }
            )

        elif task == "train":
            if not asset:
                ml_result.update(
                    {
                        "status": "not_executed",
                        "reason": "train requires an asset ticker",
                    }
                )
                writer(
                    {
                        "agent": AGENT_NAME,
                        "event": "ml_skipped",
                        "data": {"reason": ml_result["reason"]},
                        "status": "completed",
                        "progress": 1.0,
                        "timestamp": time.time(),
                    }
                )
                return {
                    "ml_data": ml_result,
                    "agents_completed": [AGENT_NAME],
                }

            training_bundle = await run_training(
                asset=asset,
                model_type=model_type,
                horizon_days=horizon_days,
                period=params.get("period", "5y"),
                seed=int(params.get("seed", 42)),
                params=params.get("params"),
                include_baselines=bool(params.get("include_baselines", True)),
                executor=get_shared_executor(),
            )
            train_response = build_train_response(training_bundle)
            ml_result.update(
                {
                    "training": train_response.model_dump(),
                    "run_id": train_response.primary.run_id,
                    "asset": train_response.primary.asset,
                    "model_type": train_response.primary.model_type,
                    "status": train_response.primary.status,
                }
            )

        duration_ms = int((time.time() - started_at) * 1000)
        writer(
            {
                "agent": AGENT_NAME,
                "event": "ml_complete",
                "data": {
                    "task": task,
                    "status": ml_result["status"],
                    "duration_ms": duration_ms,
                    "available_artifacts": ml_result["available_artifacts"],
                    "available_runs": ml_result["available_runs"],
                },
                "status": "completed",
                "progress": 1.0,
                "timestamp": time.time(),
            }
        )

        return {
            "ml_data": ml_result,
            "agents_completed": [AGENT_NAME],
        }

    except (
        ArtifactNotFoundError,
        InvalidModelTypeError,
        PredictionExecutionError,
        PriceFetchError,
    ) as exc:
        logger.warning("MLAgent execution blocked: %s", exc)
        writer(
            {
                "agent": AGENT_NAME,
                "event": "ml_error",
                "data": {"error": str(exc), "task": task},
                "status": "error",
                "progress": 0.0,
                "timestamp": time.time(),
            }
        )
        return {
            "ml_data": {
                "source": "ml_service",
                "task": task,
                "status": "error",
                "error": str(exc),
            },
            "agents_failed": [AGENT_NAME],
            "errors": [{"agent": AGENT_NAME, "error": str(exc), "timestamp": time.time()}],
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("MLAgent unexpected error: %s", exc)
        writer(
            {
                "agent": AGENT_NAME,
                "event": "ml_error",
                "data": {"error": str(exc), "task": task},
                "status": "error",
                "progress": 0.0,
                "timestamp": time.time(),
            }
        )
        return {
            "ml_data": {
                "source": "ml_service",
                "task": task,
                "status": "error",
                "error": str(exc),
            },
            "agents_failed": [AGENT_NAME],
            "errors": [{"agent": AGENT_NAME, "error": str(exc), "timestamp": time.time()}],
        }
