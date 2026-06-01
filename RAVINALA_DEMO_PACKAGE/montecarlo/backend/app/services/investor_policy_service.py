"""
services/investor_policy_service.py - Canonical investor policy normalization.

This service turns raw investor inputs into a stable internal mandate that can
be reused by future eligibility / CMA / recommendation layers.
"""

from __future__ import annotations

from app.risk.conventions import CONVENTIONS
from app.schemas.allocator import (
    AssetClassConstraintInput,
    AllocationRecommendationRequest,
    CurrentPositionInput,
    InvestorObjectiveType,
    InvestorPolicy,
    InvestorRiskProfile,
    LiquidityNeeds,
)
from app.schemas.portfolio import OptimizationObjective


def _coerce_request(req: AllocationRecommendationRequest | dict[str, object] | object) -> AllocationRecommendationRequest:
    if isinstance(req, AllocationRecommendationRequest):
        return req
    if isinstance(req, dict):
        return AllocationRecommendationRequest(**req)
    if hasattr(req, "__dict__"):
        return AllocationRecommendationRequest(**vars(req))
    raise TypeError(f"Unsupported investor policy payload: {type(req)!r}")


def _unique_strings(values: list[str], *, uppercase: bool = False) -> list[str]:
    """Normalize a list of user-provided identifiers while preserving order."""
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in values:
        value = (raw or "").strip()
        if not value:
            continue
        value = value.upper() if uppercase else value.lower()
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _risk_profile(risk_aversion: float) -> InvestorRiskProfile:
    if risk_aversion >= 0.70:
        return InvestorRiskProfile.conservative
    if risk_aversion >= 0.35:
        return InvestorRiskProfile.moderate
    return InvestorRiskProfile.aggressive


def _objective_used(
    *,
    profile: InvestorRiskProfile,
    objective_type: InvestorObjectiveType,
    liquidity_needs: LiquidityNeeds,
) -> OptimizationObjective:
    if objective_type == InvestorObjectiveType.capital_preservation:
        return OptimizationObjective.min_variance
    if objective_type == InvestorObjectiveType.income:
        return OptimizationObjective.risk_parity
    if liquidity_needs == LiquidityNeeds.high and profile != InvestorRiskProfile.aggressive:
        return OptimizationObjective.min_variance
    if profile == InvestorRiskProfile.conservative:
        return OptimizationObjective.min_variance
    if profile == InvestorRiskProfile.moderate:
        return OptimizationObjective.risk_parity
    return OptimizationObjective.max_sharpe


def _max_weight(
    *,
    profile: InvestorRiskProfile,
    liquidity_needs: LiquidityNeeds,
    candidate_count: int,
) -> float:
    if candidate_count <= 4:
        baseline = 0.40
    elif candidate_count <= 8:
        baseline = 0.28
    else:
        baseline = 0.18

    if profile == InvestorRiskProfile.aggressive:
        baseline += 0.10
    elif profile == InvestorRiskProfile.conservative:
        baseline -= 0.05

    if liquidity_needs == LiquidityNeeds.high:
        baseline -= 0.05

    return min(0.60, max(0.10, baseline))


def _min_weight(candidate_count: int) -> float:
    if candidate_count >= 12:
        return 0.02
    if candidate_count >= 6:
        return 0.01
    return 0.0


def _cash_buffer_weight(
    *,
    profile: InvestorRiskProfile,
    objective_type: InvestorObjectiveType,
    liquidity_needs: LiquidityNeeds,
) -> float:
    if objective_type == InvestorObjectiveType.capital_preservation:
        return 0.15
    if liquidity_needs == LiquidityNeeds.high:
        return 0.10
    if profile == InvestorRiskProfile.conservative or objective_type == InvestorObjectiveType.income:
        return 0.05
    return 0.0


def _lookback_days(horizon_years: int) -> int:
    if horizon_years <= 1:
        return 252
    if horizon_years <= 3:
        return 504
    return 756


def _target_volatility(profile: InvestorRiskProfile) -> float | None:
    """
    Reserved target volatility hint for future constraint expansion.

    Kept explicit in the policy so allocator runs can persist the intended risk
    budget even before it becomes a hard optimizer constraint everywhere.
    """
    if profile == InvestorRiskProfile.conservative:
        return 0.10
    if profile == InvestorRiskProfile.moderate:
        return 0.14
    return 0.20


def _default_drawdown_tolerance(profile: InvestorRiskProfile) -> float:
    if profile == InvestorRiskProfile.conservative:
        return 0.12
    if profile == InvestorRiskProfile.moderate:
        return 0.20
    return 0.30


def _default_benchmark(
    *,
    profile: InvestorRiskProfile,
    objective_type: InvestorObjectiveType,
) -> str:
    if objective_type == InvestorObjectiveType.capital_preservation:
        return "short_duration_treasuries"
    if objective_type == InvestorObjectiveType.income:
        return "income_blend"
    if profile == InvestorRiskProfile.aggressive:
        return "acwi"
    if profile == InvestorRiskProfile.conservative:
        return "global_agg"
    return "60_40"


def _max_selected_assets(
    *,
    explicit_value: int | None,
    profile: InvestorRiskProfile,
    candidate_count: int,
) -> int | None:
    if explicit_value is not None:
        return min(explicit_value, max(candidate_count, 2))
    default_cap = {
        InvestorRiskProfile.conservative: 6,
        InvestorRiskProfile.moderate: 8,
        InvestorRiskProfile.aggressive: 10,
    }[profile]
    return min(default_cap, max(candidate_count, 2))


def _normalize_asset_class_constraints(
    constraints: list[AssetClassConstraintInput],
) -> list[AssetClassConstraintInput]:
    normalized: list[AssetClassConstraintInput] = []
    seen: set[str] = set()
    for item in constraints:
        asset_class = (item.asset_class or "").strip().lower()
        if not asset_class or asset_class in seen:
            continue
        seen.add(asset_class)
        normalized.append(
            AssetClassConstraintInput(
                asset_class=asset_class,
                min_weight=item.min_weight,
                max_weight=item.max_weight,
            )
        )
    return normalized


def _normalize_current_positions(
    positions: list[CurrentPositionInput],
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for item in positions:
        ticker = (item.ticker or "").strip().upper()
        if not ticker:
            continue
        normalized[ticker] = float(item.weight)
    total_weight = float(sum(normalized.values()))
    if total_weight > 1.0 + 1e-9:
        raise ValueError("current_positions weights must sum to <= 1.0")
    return normalized


def build_investor_policy(
    req: AllocationRecommendationRequest | dict[str, object] | object,
) -> InvestorPolicy:
    """Normalize raw investor inputs into a versionable internal mandate."""
    req = _coerce_request(req)
    candidate_count = len(_unique_strings(req.candidate_tickers, uppercase=True))
    profile = _risk_profile(req.risk_aversion)
    objective_used = _objective_used(
        profile=profile,
        objective_type=req.objective_type,
        liquidity_needs=req.liquidity_needs,
    )
    allowed_asset_classes = _unique_strings(req.allowed_asset_classes, uppercase=False)
    excluded_tickers = _unique_strings(req.exclusions, uppercase=True)
    preferred_tickers = _unique_strings(req.preferred_tickers, uppercase=True)
    asset_class_constraints = _normalize_asset_class_constraints(req.asset_class_constraints)
    current_position_weights = _normalize_current_positions(req.current_positions)
    max_selected_assets = _max_selected_assets(
        explicit_value=req.max_selected_assets,
        profile=profile,
        candidate_count=max(candidate_count, 2),
    )

    warnings: list[str] = []
    if candidate_count < 4:
        warnings.append(
            "candidate universe is narrow; recommendation quality and diversification will be limited"
        )
    if req.investment_horizon_years <= 2 and req.objective_type == InvestorObjectiveType.growth:
        warnings.append(
            "short horizon and growth mandate may be structurally in tension; treat the allocation as opportunistic"
        )
    if req.income_need >= 0.5 and req.objective_type == InvestorObjectiveType.growth:
        warnings.append(
            "high income need is inconsistent with a pure growth mandate; future slices should arbitrate this formally"
        )
    if current_position_weights and not preferred_tickers:
        warnings.append(
            "current positions are provided for turnover diagnostics only; they do not bias expected returns or preferred names"
        )

    return InvestorPolicy(
        amount=req.amount,
        base_currency=req.base_currency.upper(),
        risk_aversion=req.risk_aversion,
        risk_profile=profile,
        investment_horizon_years=req.investment_horizon_years,
        liquidity_needs=req.liquidity_needs,
        objective_type=req.objective_type,
        objective_used=objective_used,
        income_need=req.income_need,
        max_drawdown_tolerance=req.max_drawdown_tolerance or _default_drawdown_tolerance(profile),
        max_weight=_max_weight(
            profile=profile,
            liquidity_needs=req.liquidity_needs,
            candidate_count=max(candidate_count, 2),
        ),
        min_weight=_min_weight(candidate_count),
        target_volatility=_target_volatility(profile),
        lookback_days=_lookback_days(req.investment_horizon_years),
        cash_buffer_weight=_cash_buffer_weight(
            profile=profile,
            objective_type=req.objective_type,
            liquidity_needs=req.liquidity_needs,
        ),
        risk_free_rate_used=CONVENTIONS.risk_free_rate,
        allowed_asset_classes=allowed_asset_classes,
        excluded_tickers=excluded_tickers,
        preferred_tickers=preferred_tickers,
        max_selected_assets=max_selected_assets,
        asset_class_constraints=asset_class_constraints,
        current_position_weights=current_position_weights,
        benchmark_preference=req.benchmark_preference
        or _default_benchmark(profile=profile, objective_type=req.objective_type),
        warnings=warnings,
    )


__all__ = ["build_investor_policy"]
