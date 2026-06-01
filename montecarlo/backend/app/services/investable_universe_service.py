"""
services/investable_universe_service.py - eligibility layer for allocator inputs.

Builds a canonical `EligibleUniverse` from a candidate ticker list and a
normalized investor policy.
"""

from __future__ import annotations

from app.schemas.allocator import (
    AllocationRecommendationRequest,
    EligibleAsset,
    EligibleUniverseResponse,
    EligibilityCriteria,
    IneligibleAsset,
    InvestorPolicy,
    InvestorRiskProfile,
    LiquidityNeeds,
)
from app.schemas.universe import InstrumentResponse
from app.services.universe_service import get_instrument_detail


def _coerce_request(
    req: AllocationRecommendationRequest | dict[str, object] | object,
) -> AllocationRecommendationRequest:
    if isinstance(req, AllocationRecommendationRequest):
        return req
    if isinstance(req, dict):
        return AllocationRecommendationRequest(**req)
    if hasattr(req, "__dict__"):
        return AllocationRecommendationRequest(**vars(req))
    raise TypeError(f"Unsupported eligible universe payload: {type(req)!r}")


def _min_market_cap(policy: InvestorPolicy) -> float | None:
    if policy.risk_profile == InvestorRiskProfile.conservative:
        return 10_000_000_000.0
    if policy.risk_profile == InvestorRiskProfile.moderate:
        return 2_000_000_000.0
    return 300_000_000.0


def _min_volume_avg_30d(policy: InvestorPolicy) -> float | None:
    if policy.liquidity_needs == LiquidityNeeds.high:
        return 2_000_000.0
    if policy.liquidity_needs == LiquidityNeeds.medium:
        return 500_000.0
    return 100_000.0


def build_eligibility_criteria(policy: InvestorPolicy) -> EligibilityCriteria:
    """Derive explicit eligibility criteria from the investor mandate."""
    return EligibilityCriteria(
        min_market_cap=_min_market_cap(policy),
        min_volume_avg_30d=_min_volume_avg_30d(policy),
        allowed_asset_classes=list(policy.allowed_asset_classes),
        allowed_currencies=[],
        require_price=True,
        require_market_cap_for_equities=True,
        require_volume_proxy=True,
        require_cost_proxy=False,
    )


def _data_quality_score(inst: InstrumentResponse) -> float:
    fields = [
        inst.price,
        inst.volume_avg_30d,
        inst.market_cap,
        inst.volatility_1y,
        inst.sharpe_1y,
        inst.exchange,
        inst.currency,
    ]
    available = sum(1 for value in fields if value not in (None, "", 0))
    return round(available / len(fields), 2)


def _liquidity_tier(inst: InstrumentResponse) -> str:
    volume = inst.volume_avg_30d or 0.0
    if volume >= 2_000_000:
        return "high"
    if volume >= 500_000:
        return "medium"
    if volume > 0:
        return "low"
    return "unknown"


def _cost_proxy_available(inst: InstrumentResponse) -> bool:
    return bool(inst.asset_class.lower() == "equity" and inst.volume_avg_30d and inst.market_cap)


def _base_asset(inst: InstrumentResponse) -> dict[str, object]:
    return {
        "ticker": inst.ticker,
        "name": inst.name,
        "asset_class": inst.asset_class,
        "currency": inst.currency,
        "price": inst.price,
        "price_change_1m": inst.price_change_1m,
        "price_change_1y": inst.price_change_1y,
        "market_cap": inst.market_cap,
        "volume_avg_30d": inst.volume_avg_30d,
        "dividend_yield": inst.dividend_yield,
        "volatility_1y": inst.volatility_1y,
        "sharpe_1y": inst.sharpe_1y,
        "liquidity_tier": _liquidity_tier(inst),
        "data_quality_score": _data_quality_score(inst),
        "cost_proxy_available": _cost_proxy_available(inst),
        "notes": [],
    }


def build_eligible_universe(
    req: AllocationRecommendationRequest | dict[str, object] | object,
    policy: InvestorPolicy,
) -> EligibleUniverseResponse:
    """
    Filter a candidate ticker list into a canonical investable universe.

    This first slice is explicit about what it can and cannot enforce:
    price presence, asset-class allowance, liquidity proxies, size proxies and
    basic data quality. It does not yet model transaction costs or FX risk.
    """
    req = _coerce_request(req)
    criteria = build_eligibility_criteria(policy)
    allowed_asset_classes = {item.lower() for item in criteria.allowed_asset_classes}
    excluded_tickers = set(policy.excluded_tickers)

    eligible_assets: list[EligibleAsset] = []
    rejected_assets: list[IneligibleAsset] = []
    warnings: list[str] = []
    non_base_currency: set[str] = set()

    for raw_ticker in req.candidate_tickers:
        ticker = (raw_ticker or "").strip().upper()
        if not ticker:
            continue
        if ticker in excluded_tickers:
            rejected_assets.append(
                IneligibleAsset(
                    ticker=ticker,
                    name=ticker,
                    asset_class="unknown",
                    currency=policy.base_currency,
                    price=None,
                    market_cap=None,
                    volume_avg_30d=None,
                    liquidity_tier="unknown",
                    data_quality_score=0.0,
                    cost_proxy_available=False,
                    notes=[],
                    rejection_reasons=["excluded_by_investor_policy"],
                )
            )
            continue

        inst = get_instrument_detail(ticker)
        if inst is None:
            rejected_assets.append(
                IneligibleAsset(
                    ticker=ticker,
                    name=ticker,
                    asset_class="unknown",
                    currency=policy.base_currency,
                    price=None,
                    market_cap=None,
                    volume_avg_30d=None,
                    liquidity_tier="unknown",
                    data_quality_score=0.0,
                    cost_proxy_available=False,
                    notes=[],
                    rejection_reasons=["instrument_not_found_in_backend_universe"],
                )
            )
            continue

        payload = _base_asset(inst)
        rejection_reasons: list[str] = []
        notes: list[str] = list(payload["notes"])
        asset_class = inst.asset_class.lower()

        if allowed_asset_classes and asset_class not in allowed_asset_classes:
            rejection_reasons.append("asset_class_not_allowed_by_investor_policy")

        if criteria.require_price and (inst.price is None or inst.price <= 0):
            rejection_reasons.append("missing_or_non_positive_price")

        if (
            criteria.require_market_cap_for_equities
            and asset_class == "equity"
            and criteria.min_market_cap is not None
            and (inst.market_cap is None or inst.market_cap < criteria.min_market_cap)
        ):
            rejection_reasons.append("market_cap_below_threshold")

        if (
            criteria.require_volume_proxy
            and criteria.min_volume_avg_30d is not None
            and (inst.volume_avg_30d is None or inst.volume_avg_30d < criteria.min_volume_avg_30d)
        ):
            rejection_reasons.append("average_volume_below_threshold")

        if payload["data_quality_score"] < 0.50:
            rejection_reasons.append("insufficient_data_quality_score")

        if inst.currency.upper() != policy.base_currency.upper():
            notes.append("currency differs from investor base currency; FX risk layer not yet integrated")
            non_base_currency.add(inst.currency.upper())

        if not payload["cost_proxy_available"]:
            notes.append("transaction cost proxy not yet available for this instrument")

        payload["notes"] = notes
        if rejection_reasons:
            rejected_assets.append(
                IneligibleAsset(**payload, rejection_reasons=rejection_reasons)
            )
            continue

        eligible_assets.append(EligibleAsset(**payload))

    if not criteria.allowed_asset_classes:
        warnings.append(
            "no allowed_asset_classes constraint was supplied; candidate tickers are assumed pre-filtered"
        )
    if non_base_currency:
        warnings.append(
            "eligible universe contains non-base-currency instruments without an explicit FX risk layer: "
            + ", ".join(sorted(non_base_currency))
        )
    warnings.append(
        "eligibility v1 uses explicit liquidity and size heuristics; transaction costs and spread-aware filtering are not yet enforced"
    )

    return EligibleUniverseResponse(
        criteria=criteria,
        eligible_assets=eligible_assets,
        rejected_assets=rejected_assets,
        warnings=warnings,
    )


__all__ = ["build_eligible_universe", "build_eligibility_criteria"]
