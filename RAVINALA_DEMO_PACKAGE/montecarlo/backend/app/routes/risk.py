"""
routes/risk.py — Risk engine governance API.

Étape 10 — Risk Engine Governance
──────────────────────────────────
Endpoints:
  POST /api/v1/risk/compute           — compute full risk report for an asset
  GET  /api/v1/risk/conventions       — current quant conventions
  GET  /api/v1/risk/metrics           — metric spec sheets (what/how/limits)
  GET  /api/v1/risk/metrics/{name}    — single metric spec
  GET  /api/v1/risk/governance-levels — governance level definitions
  GET  /api/v1/risk/incoherences      — current incoherences & correction plan
  GET  /api/v1/risk/snapshots         — list past risk snapshots
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.executor import get_shared_executor
from app.risk.conventions import (
    CONVENTIONS,
    CORRECTION_PLAN,
    CURRENT_INCOHERENCES,
    GOVERNANCE_LEVELS,
    METRIC_SPECS,
)
from app.schemas.envelope import ApiResponse
from app.schemas.risk_api import (
    ConventionsResponse,
    GovernanceLevelsCatalog,
    RiskAsyncResponse,
    RiskComputeRequest,
    RiskComputeResponse,
    RiskIncoherencesResponse,
    RiskMetricSpec,
    RiskMetricsCatalog,
    RiskSnapshotRecord,
)
from app.services.risk_service import (
    RiskComputationError,
    RiskPriceFetchError,
    compute_risk_report,
    list_risk_snapshots_with_fallback,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/compute", response_model=ApiResponse[RiskComputeResponse])
async def compute_risk(req: RiskComputeRequest):
    """
    Compute full governed risk report for a single asset.

    Returns all metrics (VaR, CVaR, vol, drawdown, Sharpe, Sortino, Calmar, stress)
    each wrapped with governance metadata (level, method, conventions, limitations).
    """
    try:
        payload = await compute_risk_report(
            asset=req.asset,
            period=req.period,
            portfolio_value=req.portfolio_value,
            executor=get_shared_executor(),
        )
    except RiskPriceFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except RiskComputationError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ApiResponse(
        status="ok",
        data_quality="live",
        data=payload,
    )


@router.post("/compute/async", response_model=ApiResponse[RiskAsyncResponse])
async def compute_risk_async(req: RiskComputeRequest):
    """
    Dispatch risk computation to Celery and return a job_id immediately.

    Poll GET /api/v1/jobs/{job_id} for status.
    """
    try:
        from app.workers.tasks.risk_task import compute_risk as _task
        task = _task.delay(
            asset=req.asset,
            period=req.period,
            portfolio_value=req.portfolio_value,
        )
        return ApiResponse(
            data_quality="live",
            status="ok",
            data=RiskAsyncResponse(job_id=task.id, status="PENDING"),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {exc}")


@router.get("/conventions", response_model=ApiResponse[ConventionsResponse])
async def get_conventions():
    """
    Current quant conventions — single source of truth.

    All risk metrics use these parameters.  Any deviation is flagged
    in the metric's `conventions_snapshot`.
    """
    return ApiResponse(
        status="ok",
        data_quality="demo_static",
        data=ConventionsResponse(
            trading_days_per_year=CONVENTIONS.trading_days_per_year,
            risk_free_rate=CONVENTIONS.risk_free_rate,
            risk_free_rate_source=CONVENTIONS.risk_free_rate_source,
            risk_free_rate_last_updated=CONVENTIONS.risk_free_rate_last_updated,
            return_type=CONVENTIONS.return_type,
            ann_factor_vol=round(CONVENTIONS.ann_factor_vol, 6),
            var_confidence_levels=list(CONVENTIONS.var_confidence_levels),
            var_sign_convention=CONVENTIONS.var_sign_convention,
            var_min_observations=CONVENTIONS.var_min_observations,
            rolling_windows=list(CONVENTIONS.rolling_windows),
            default_rolling_window=CONVENTIONS.default_rolling_window,
            mc_simulations=CONVENTIONS.mc_simulations,
            data_source_policy=CONVENTIONS.data_source_policy,
            stale_data_threshold_days=CONVENTIONS.stale_data_threshold_days,
            min_history_for_governed=CONVENTIONS.min_history_for_governed,
        ),
    )


@router.get("/metrics", response_model=ApiResponse[RiskMetricsCatalog])
async def get_metric_specs():
    """
    Spec sheets for all governed metrics.

    Each spec documents: method, formula, conventions, horizons,
    limitations, what to keep simple, what to defer.
    """
    return ApiResponse(
        status="ok",
        data_quality="demo_static",
        data=RiskMetricsCatalog.model_validate(METRIC_SPECS),
    )


@router.get("/metrics/{name}", response_model=ApiResponse[RiskMetricSpec])
async def get_metric_spec(name: str):
    """Single metric spec sheet."""
    if name not in METRIC_SPECS:
        raise HTTPException(
            status_code=404,
            detail=f"Metric '{name}' not found. Available: {list(METRIC_SPECS.keys())}",
        )
    return ApiResponse(
        status="ok",
        data_quality="demo_static",
        data=RiskMetricSpec.model_validate(METRIC_SPECS[name]),
    )


@router.get("/governance-levels", response_model=ApiResponse[GovernanceLevelsCatalog])
async def get_governance_levels():
    """
    Definitions of governance levels: calculated / governed / exploitable.

    A metric progresses through these levels as documentation,
    persistence, and operational maturity improve.
    """
    return ApiResponse(
        status="ok",
        data_quality="demo_static",
        data=GovernanceLevelsCatalog.model_validate(GOVERNANCE_LEVELS),
    )


@router.get("/incoherences", response_model=ApiResponse[RiskIncoherencesResponse])
async def get_incoherences():
    """
    Current incoherences identified in the codebase + correction plan.

    Transparency: documents what was inconsistent and how it was fixed.
    """
    return ApiResponse(
        status="ok",
        data_quality="demo_static",
        data=RiskIncoherencesResponse.model_validate({
            "incoherences": CURRENT_INCOHERENCES,
            "correction_plan": CORRECTION_PLAN,
        }),
    )


@router.get("/snapshots", response_model=ApiResponse[list[RiskSnapshotRecord]])
async def list_snapshots(
    asset: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List past risk computation snapshots (most recent first)."""
    return ApiResponse(
        status="ok",
        data_quality="mixed",
        data=await list_risk_snapshots_with_fallback(asset=asset, limit=limit),
    )
