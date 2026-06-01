"""
services/allocation_recommendation_service.py - Allocation recommendation orchestration.

First backend slice of the Portfolio Construction Engine:
normalize investor inputs, reuse the existing optimizer, explain the result,
and persist the run when the database is active.
"""

from __future__ import annotations

import logging
import math
import uuid

from app.allocation.persistence import (
    get_allocation_run_db,
    list_allocation_runs_db,
    save_allocation_run_sync,
)
from app.schemas.allocator import (
    AllocationAlternatives,
    AlternativeAllocation,
    AllocationCandidateConstraintDiagnostics,
    AllocationCandidateAsset,
    AllocationCandidatePortfolio,
    AllocationConstraintSnapshot,
    AllocationOptimizationSummary,
    AllocationRecommendationRequest,
    AllocationRecommendationResponse,
    AllocationRunSummary,
    AssetClassExposure,
    AssetCapitalMarketAssumption,
    BenchmarkComparison,
    EligibleAsset,
    MLPredictionInput,
    PersistenceStatus,
    PortfolioSleeve,
    RebalancingDelta,
    RebalancingTradeInstruction,
    RecommendedAsset,
    RejectedAsset,
    SleeveBreakdown,
    StressScenarioResult,
    StressTestSummary,
)
from app.services.capital_market_assumptions_service import build_capital_market_assumptions
from app.services.investor_policy_service import build_investor_policy
from app.services.investable_universe_service import build_eligible_universe
from app.services.portfolio_optimization_service import (
    run_allocator_candidate_optimizations_payload,
)
from app.services.portfolio_risk_inputs_service import (
    build_candidate_risk_diagnostics,
    build_portfolio_risk_inputs,
)

logger = logging.getLogger(__name__)


def _unique_tickers(values: list[str]) -> list[str]:
    seen: set[str] = set()
    tickers: list[str] = []
    for raw in values:
        ticker = (raw or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tickers


def _coerce_request(
    req: AllocationRecommendationRequest | dict[str, object] | object,
) -> AllocationRecommendationRequest:
    if isinstance(req, AllocationRecommendationRequest):
        return req
    if isinstance(req, dict):
        return AllocationRecommendationRequest(**req)
    if hasattr(req, "__dict__"):
        return AllocationRecommendationRequest(**vars(req))
    raise TypeError(f"Unsupported allocation recommendation payload: {type(req)!r}")


def _weight_value(asset: object) -> float:
    if hasattr(asset, "weight"):
        return float(getattr(asset, "weight"))
    return float(asset["weight"])


def _asset_field(asset: object, name: str):
    if hasattr(asset, name):
        return getattr(asset, name)
    return asset.get(name)


def _assumptions_by_ticker(assumptions: list[AssetCapitalMarketAssumption]) -> dict[str, AssetCapitalMarketAssumption]:
    return {item.ticker: item for item in assumptions}


def _asset_role(*, rank: int, weight: float) -> str:
    if rank == 0 or weight >= 0.25:
        return "core"
    if weight >= 0.10:
        return "satellite"
    return "diversifier"


def _selection_reason(
    *,
    objective_used: str,
    weight: float,
    rank: int,
) -> str:
    if rank == 0:
        return f"highest-conviction allocation under the {objective_used} mandate"
    if weight >= 0.15:
        return f"meaningful portfolio weight retained by the {objective_used} optimizer"
    return f"kept as a lower-weight diversifier within the {objective_used} solution"


def _constraint_snapshot(policy) -> AllocationConstraintSnapshot:
    return AllocationConstraintSnapshot(
        max_weight=policy.max_weight,
        min_weight=policy.min_weight,
        target_volatility=policy.target_volatility,
        max_drawdown_tolerance=policy.max_drawdown_tolerance,
        cash_buffer_weight=policy.cash_buffer_weight,
        lookback_days=policy.lookback_days,
        max_selected_assets=policy.max_selected_assets,
        asset_class_constraints=policy.asset_class_constraints,
    )


def _candidate_asset_allocations(
    *,
    candidate_weights: list[object],
    investable_amount: float,
    eligibility_by_ticker: dict[str, EligibleAsset],
) -> list[AllocationCandidateAsset]:
    assets: list[AllocationCandidateAsset] = []
    for asset in sorted(candidate_weights, key=_weight_value, reverse=True):
        weight = _weight_value(asset)
        if weight <= 0:
            continue
        ticker = str(_asset_field(asset, "ticker"))
        eligible_asset = eligibility_by_ticker.get(ticker)
        assets.append(
            AllocationCandidateAsset(
                ticker=ticker,
                name=eligible_asset.name if eligible_asset else ticker,
                weight=weight,
                amount=round(investable_amount * weight, 2),
                expected_return=_asset_field(asset, "expected_return"),
                volatility=_asset_field(asset, "volatility"),
            )
        )
    return assets


def _candidate_weight_map(candidate_weights: list[object]) -> dict[str, float]:
    return {
        str(_asset_field(asset, "ticker")): _weight_value(asset)
        for asset in candidate_weights
        if _weight_value(asset) > 0
    }


def _turnover_from_current(
    *,
    candidate_weights: dict[str, float],
    current_position_weights: dict[str, float],
) -> float | None:
    if not current_position_weights:
        return None
    universe = set(candidate_weights) | set(current_position_weights)
    return 0.5 * sum(
        abs(float(candidate_weights.get(ticker, 0.0)) - float(current_position_weights.get(ticker, 0.0)))
        for ticker in universe
    )


_HOLD_BAND: float = 0.001  # weight changes < 0.1pp are treated as "hold"


def _build_rebalancing_delta(
    *,
    recommended_assets: list[RecommendedAsset],
    current_position_weights: dict[str, float],
) -> RebalancingDelta:
    """
    Build a RebalancingDelta comparing the recommendation to the current portfolio.

    When current_position_weights is empty the delta is computed against a
    zero-weight baseline (every position is an "open").
    """
    available = bool(current_position_weights)
    target_weights: dict[str, float] = {a.ticker: a.target_weight for a in recommended_assets}

    universe = set(target_weights) | set(current_position_weights)
    trades: list[RebalancingTradeInstruction] = []
    new_positions: list[str] = []
    closed_positions: list[str] = []

    for ticker in universe:
        cur = float(current_position_weights.get(ticker, 0.0))
        tgt = float(target_weights.get(ticker, 0.0))
        delta = tgt - cur

        if abs(delta) < _HOLD_BAND:
            action = "hold"
        elif cur == 0.0:
            action = "open"
            new_positions.append(ticker)
        elif tgt == 0.0:
            action = "close"
            closed_positions.append(ticker)
        elif delta > 0:
            action = "buy"
        else:
            action = "sell"

        trades.append(RebalancingTradeInstruction(
            ticker=ticker,
            current_weight=cur,
            target_weight=tgt,
            delta_weight=round(delta, 6),
            action=action,
        ))

    trades.sort(key=lambda t: abs(t.delta_weight), reverse=True)
    one_way_turnover = round(
        0.5 * sum(abs(t.delta_weight) for t in trades),
        6,
    )

    return RebalancingDelta(
        available=available,
        one_way_turnover=one_way_turnover,
        trades=trades,
        new_positions=sorted(new_positions),
        closed_positions=sorted(closed_positions),
    )


# ── Benchmark comparison helpers (PC7.1) ─────────────────────────────────────

# Asset classes treated as "equity" and "bond" for benchmark construction
_EQUITY_CLASSES = frozenset({"equity"})
_BOND_CLASSES = frozenset({"fixed_income"})
_CASH_CLASSES = frozenset({"cash"})
_REAL_ESTATE_CLASSES = frozenset({"real_estate"})


def _benchmark_weights(
    *,
    benchmark_preference: str,
    eligible_tickers: list[str],
    asset_class_by_ticker: dict[str, str],
) -> tuple[dict[str, float], str]:
    """
    Derive per-ticker benchmark weights from a benchmark preference string.

    Returns (weights_dict, method_description).
    Falls back to equal-weight if the preferred split cannot be satisfied
    (e.g. no equity tickers for a 60/40 benchmark).
    """
    n = len(eligible_tickers)
    if n == 0:
        return {}, "no_eligible_tickers"

    def _class(t: str) -> str:
        return (asset_class_by_ticker.get(t) or "other").lower()

    eq_tickers  = [t for t in eligible_tickers if _class(t) in _EQUITY_CLASSES]
    bd_tickers  = [t for t in eligible_tickers if _class(t) in _BOND_CLASSES]
    cash_tickers = [t for t in eligible_tickers if _class(t) in _CASH_CLASSES]
    re_tickers  = [t for t in eligible_tickers if _class(t) in _REAL_ESTATE_CLASSES]

    def _ew(tickers: list[str]) -> dict[str, float]:
        k = len(tickers)
        return {t: round(1.0 / k, 8) for t in tickers} if k else {}

    def _fallback() -> tuple[dict[str, float], str]:
        return _ew(eligible_tickers), "equal_weight_fallback"

    name = benchmark_preference.lower()

    if name == "equal_weight":
        return _ew(eligible_tickers), "equal_weight"

    if name == "60_40":
        if not eq_tickers or not bd_tickers:
            return _fallback()
        w: dict[str, float] = {}
        for t in eq_tickers:
            w[t] = round(0.60 / len(eq_tickers), 8)
        for t in bd_tickers:
            w[t] = round(0.40 / len(bd_tickers), 8)
        return w, "60pct_equity_40pct_bonds_equal_within_class"

    if name == "acwi":
        if not eq_tickers:
            return _fallback()
        return _ew(eq_tickers), "all_equity_equal_weight"

    if name == "global_agg":
        if not bd_tickers:
            return _fallback()
        return _ew(bd_tickers), "all_bonds_equal_weight"

    if name == "income_blend":
        # Target: 50% bonds + 30% equity + 20% real_estate; renormalize if class absent
        targets = [
            (bd_tickers, 0.50),
            (eq_tickers, 0.30),
            (re_tickers, 0.20),
        ]
        available = [(tickers, alloc) for tickers, alloc in targets if tickers]
        if not available:
            return _fallback()
        total = sum(alloc for _, alloc in available)
        w = {}
        for tickers, alloc in available:
            share = (alloc / total) / len(tickers)
            for t in tickers:
                w[t] = round(share, 8)
        return w, "income_blend_50bd_30eq_20re"

    if name == "short_duration_treasuries":
        safe_tickers = bd_tickers + cash_tickers
        if not safe_tickers:
            return _fallback()
        return _ew(safe_tickers), "bonds_and_cash_equal_weight"

    # Unknown preference → equal weight
    return _ew(eligible_tickers), f"equal_weight_unknown_preference:{benchmark_preference}"


def _portfolio_stats_from_weights(
    weights: dict[str, float],
    *,
    assumptions_by_ticker: dict[str, AssetCapitalMarketAssumption],
    covariance_matrix: dict[str, dict[str, float]],
    risk_free_rate: float,
) -> tuple[float, float, float]:
    """
    Compute (expected_return_pct, volatility_pct, sharpe_ratio) for a weight dict.

    Returns are in **percentage** (×100), consistent with the optimizer output.
    ``risk_free_rate`` is a fraction (e.g. 0.03).
    The covariance matrix is annualized, in fraction² units.
    Returns (0, 0, 0) when the covariance matrix is unavailable.
    """
    tickers = [t for t in weights if t in assumptions_by_ticker]
    if not tickers:
        return 0.0, 0.0, 0.0

    er_frac = sum(
        weights[t] * assumptions_by_ticker[t].expected_return
        for t in tickers
    )

    # Build covariance sub-matrix
    cov_rows = []
    w_vec = []
    for t in tickers:
        row = covariance_matrix.get(t, {})
        cov_rows.append([float(row.get(t2, 0.0)) for t2 in tickers])
        w_vec.append(weights[t])

    if not cov_rows or all(all(v == 0.0 for v in row) for row in cov_rows):
        # No covariance data — return expected return only, vol=0
        return er_frac * 100, 0.0, 0.0

    vol_sq = sum(
        w_vec[i] * w_vec[j] * cov_rows[i][j]
        for i in range(len(tickers))
        for j in range(len(tickers))
    )
    vol_frac = math.sqrt(max(vol_sq, 0.0))
    sharpe = (er_frac - risk_free_rate) / vol_frac if vol_frac > 0 else 0.0
    return round(er_frac * 100, 6), round(vol_frac * 100, 6), round(sharpe, 6)


def _build_benchmark_comparison(
    *,
    benchmark_preference: str,
    eligible_tickers: list[str],
    asset_class_by_ticker: dict[str, str],
    assumptions_by_ticker: dict[str, AssetCapitalMarketAssumption],
    covariance_matrix: dict[str, dict[str, float]],
    recommended_weights: dict[str, float],
    recommended_expected_return: float,
    recommended_expected_volatility: float,
    risk_free_rate: float,
) -> BenchmarkComparison | None:
    """
    Build a BenchmarkComparison comparing the recommendation against a simple baseline.

    Returns None if benchmark weights cannot be derived (empty eligible universe).
    """
    bm_weights, method = _benchmark_weights(
        benchmark_preference=benchmark_preference,
        eligible_tickers=eligible_tickers,
        asset_class_by_ticker=asset_class_by_ticker,
    )
    if not bm_weights:
        return None

    bm_er, bm_vol, bm_sharpe = _portfolio_stats_from_weights(
        bm_weights,
        assumptions_by_ticker=assumptions_by_ticker,
        covariance_matrix=covariance_matrix,
        risk_free_rate=risk_free_rate,
    )

    active_return = round(recommended_expected_return - bm_er, 6)

    # Tracking error: σ(w_rec − w_bm)
    universe = sorted(set(recommended_weights) | set(bm_weights))
    active_weights = {
        t: recommended_weights.get(t, 0.0) - bm_weights.get(t, 0.0)
        for t in universe
        if t in covariance_matrix
    }

    active_risk: float | None = None
    if active_weights and covariance_matrix:
        tickers_cov = [t for t in universe if t in covariance_matrix]
        aw_vec = [active_weights.get(t, 0.0) for t in tickers_cov]
        te_sq = sum(
            aw_vec[i] * aw_vec[j] * float(covariance_matrix.get(tickers_cov[i], {}).get(tickers_cov[j], 0.0))
            for i in range(len(tickers_cov))
            for j in range(len(tickers_cov))
        )
        active_risk = round(math.sqrt(max(te_sq, 0.0)) * 100, 6)

    information_ratio: float | None = None
    if active_risk is not None and active_risk > 1e-10:
        information_ratio = round(active_return / active_risk, 6)

    return BenchmarkComparison(
        benchmark_name=benchmark_preference,
        benchmark_weights={t: round(w, 6) for t, w in bm_weights.items()},
        benchmark_expected_return=bm_er,
        benchmark_expected_volatility=bm_vol,
        benchmark_sharpe_ratio=bm_sharpe,
        recommended_expected_return=round(recommended_expected_return, 6),
        recommended_expected_volatility=round(recommended_expected_volatility, 6),
        active_return=active_return,
        active_risk=active_risk,
        information_ratio=information_ratio,
        method=method,
    )


# ── PC2.4 — Sleeve breakdown ──────────────────────────────────────────────────

_SLEEVE_MAP: dict[str, str] = {
    "fixed_income": "fixed_income",
    "commodity": "alternatives",
    "real_estate": "alternatives",
    "crypto": "alternatives",
    "cash": "cash",
}

_SLEEVE_LABELS: dict[str, str] = {
    "core_beta": "Core Beta",
    "satellite": "Satellite & Thematic",
    "fixed_income": "Fixed Income",
    "alternatives": "Alternatives",
    "cash": "Cash",
    "other": "Other",
}


def _sleeve_for_asset(ticker: str, asset_class: str, role: str) -> str:
    """Assign a ticker to a sleeve name based on its asset class and role."""
    ac = asset_class.lower()
    if ac in _SLEEVE_MAP:
        return _SLEEVE_MAP[ac]
    if ac == "equity":
        return "core_beta" if role in ("core",) else "satellite"
    return "other"


def _build_sleeve_breakdown(
    *,
    recommended_assets: list[RecommendedAsset],
    asset_class_by_ticker: dict[str, str],
    assumptions_by_ticker: dict[str, AssetCapitalMarketAssumption],
) -> SleeveBreakdown:
    """Group recommended assets into logical sleeves (PC2.4)."""
    from collections import defaultdict

    sleeve_assets: dict[str, list[RecommendedAsset]] = defaultdict(list)
    for asset in recommended_assets:
        ac = asset_class_by_ticker.get(asset.ticker, "other")
        sleeve = _sleeve_for_asset(asset.ticker, ac, asset.role)
        sleeve_assets[sleeve].append(asset)

    sleeves: list[PortfolioSleeve] = []
    for sleeve_name, assets in sleeve_assets.items():
        assets_sorted = sorted(assets, key=lambda a: a.target_weight, reverse=True)
        total_weight = round(sum(a.target_weight for a in assets_sorted), 6)
        # Weight-averaged expected return (in %, using CMA fractions → ×100)
        sleeve_er: float | None = None
        er_parts = [
            a.target_weight * assumptions_by_ticker[a.ticker].expected_return
            for a in assets_sorted
            if a.ticker in assumptions_by_ticker
        ]
        if er_parts and total_weight > 0:
            sleeve_er = round(sum(er_parts) / total_weight * 100, 4)

        sleeves.append(PortfolioSleeve(
            sleeve_name=sleeve_name,
            label=_SLEEVE_LABELS.get(sleeve_name, sleeve_name),
            tickers=[a.ticker for a in assets_sorted],
            total_weight=total_weight,
            sleeve_expected_return=sleeve_er,
        ))

    sleeves.sort(key=lambda s: s.total_weight, reverse=True)
    return SleeveBreakdown(sleeves=sleeves, method="asset_class_and_role_mapping")


# ── PC6.4 — Alternative allocations ──────────────────────────────────────────

_CANDIDATE_LABELS: dict[str, tuple[str, str]] = {
    "min_variance": ("More Defensive", "Lowest expected volatility — prioritizes capital preservation."),
    "max_sharpe": ("Higher Risk-Adjusted Return", "Best Sharpe ratio — maximizes return per unit of risk taken."),
    "risk_parity": ("Risk-Balanced", "Equal risk contribution across assets — diversified risk budget."),
    "equal_weight": ("Equal-Weight Baseline", "Naive 1/N allocation — benchmark for optimizer value-add."),
}


def _candidate_label(candidate_id: str, objective: str) -> tuple[str, str]:
    """Return (label, description) for a candidate portfolio."""
    for key, (label, desc) in _CANDIDATE_LABELS.items():
        if key in candidate_id.lower() or key in objective.lower():
            return label, desc
    return candidate_id.replace("_", " ").title(), "Alternative optimization candidate."


def _build_alternatives(
    *,
    candidates: list[dict],
    selected_candidate_id: str | None,
    recommended_expected_return: float,
    recommended_expected_volatility: float,
) -> AllocationAlternatives:
    """
    Build alternative allocations from non-selected optimization candidates (PC6.4).
    Excludes the selected candidate.  Sorted by sharpe_ratio descending.
    """
    alternatives: list[AlternativeAllocation] = []
    for candidate in candidates:
        cid = candidate["candidate_id"]
        if cid == selected_candidate_id:
            continue
        label, description = _candidate_label(cid, candidate.get("objective", ""))
        weights = _candidate_weight_map(candidate["weights"])
        alternatives.append(AlternativeAllocation(
            candidate_id=cid,
            label=label,
            description=description,
            weights={t: round(w, 6) for t, w in weights.items()},
            expected_return=candidate["expected_return"],
            expected_volatility=candidate["expected_volatility"],
            sharpe_ratio=candidate["sharpe_ratio"],
            return_diff=round(candidate["expected_return"] - recommended_expected_return, 4),
            volatility_diff=round(candidate["expected_volatility"] - recommended_expected_volatility, 4),
        ))

    alternatives.sort(key=lambda a: a.sharpe_ratio, reverse=True)
    return AllocationAlternatives(
        alternatives=alternatives,
        method="non_selected_optimization_candidates",
    )


# ── PC4.4 — Stress tests ──────────────────────────────────────────────────────

_STRESS_SCENARIOS: list[dict] = [
    {
        "name": "equity_crash",
        "label": "Equity Market Crash",
        "description": "Broad equity selloff (-30%), flight to quality lifts bonds (+10%).",
        "shocks": {
            "equity": -0.30, "fixed_income": +0.10,
            "commodity": -0.10, "real_estate": -0.20,
            "crypto": -0.50, "cash": +0.01, "other": -0.15,
        },
    },
    {
        "name": "rate_shock",
        "label": "Interest Rate Shock",
        "description": "Rapid rate rise crushes bonds (-20%), equities also soften (-10%).",
        "shocks": {
            "equity": -0.10, "fixed_income": -0.20,
            "commodity": +0.05, "real_estate": -0.10,
            "crypto": -0.15, "cash": +0.02, "other": -0.05,
        },
    },
    {
        "name": "inflation_spike",
        "label": "Inflation Spike",
        "description": "High inflation rewards real assets (+20% commodities), punishes bonds (-15%).",
        "shocks": {
            "equity": -0.05, "fixed_income": -0.15,
            "commodity": +0.20, "real_estate": +0.10,
            "crypto": +0.05, "cash": 0.0, "other": -0.05,
        },
    },
    {
        "name": "stagflation",
        "label": "Stagflation",
        "description": "Low growth + high inflation: equities and bonds both negative.",
        "shocks": {
            "equity": -0.20, "fixed_income": -0.10,
            "commodity": +0.15, "real_estate": -0.05,
            "crypto": -0.30, "cash": +0.01, "other": -0.10,
        },
    },
]


def _build_stress_tests(
    *,
    recommended_assets: list[RecommendedAsset],
    asset_class_by_ticker: dict[str, str],
) -> StressTestSummary:
    """
    Apply macro stress scenarios to the recommended portfolio (PC4.4).

    portfolio_impact = Σ(target_weight_i × shock(asset_class_i))
    Shock values are fractions (e.g. -0.30 = -30%).
    """
    results: list[StressScenarioResult] = []

    for scenario in _STRESS_SCENARIOS:
        shocks: dict[str, float] = scenario["shocks"]
        portfolio_impact = 0.0
        contributions: dict[str, float] = {}

        for asset in recommended_assets:
            ac = asset_class_by_ticker.get(asset.ticker, "other")
            shock = shocks.get(ac, shocks.get("other", 0.0))
            contrib = asset.target_weight * shock
            portfolio_impact += contrib
            contributions[asset.ticker] = contrib

        portfolio_impact = round(portfolio_impact, 6)

        # Largest detractor
        largest_detractor: str | None = None
        largest_contrib: float | None = None
        if contributions:
            worst_ticker = min(contributions, key=lambda t: contributions[t])
            if contributions[worst_ticker] < 0:
                largest_detractor = worst_ticker
                largest_contrib = round(contributions[worst_ticker], 6)

        results.append(StressScenarioResult(
            scenario_name=scenario["name"],
            label=scenario["label"],
            description=scenario["description"],
            asset_class_shocks=shocks,
            portfolio_impact=portfolio_impact,
            stressed_value=round(1.0 + portfolio_impact, 6),
            largest_detractor=largest_detractor,
            largest_detractor_contribution=largest_contrib,
        ))

    worst: StressScenarioResult | None = min(
        results, key=lambda r: r.portfolio_impact
    ) if results else None

    return StressTestSummary(
        scenarios=results,
        worst_scenario_name=worst.scenario_name if worst else None,
        worst_scenario_impact=worst.portfolio_impact if worst else None,
        methodology=(
            "asset_class_shock_weighted_sum: portfolio_impact = Σ(w_i × shock(asset_class_i)); "
            "shock values are single-period fractions, not annualized"
        ),
    )


def _build_constraint_diagnostics(
    *,
    candidate_weights: dict[str, float],
    policy,
    eligibility_by_ticker: dict[str, EligibleAsset],
    applied_constraints: list[str] | None = None,
) -> AllocationCandidateConstraintDiagnostics:
    positive_weights = {
        ticker: float(weight)
        for ticker, weight in candidate_weights.items()
        if float(weight) > 1e-12
    }
    selected_asset_count = len(positive_weights)
    cardinality_breach = (
        policy.max_selected_assets is not None and selected_asset_count > policy.max_selected_assets
    )

    exposure_map: dict[str, float] = {}
    for ticker, weight in positive_weights.items():
        asset = eligibility_by_ticker.get(ticker)
        asset_class = asset.asset_class if asset is not None else "unknown"
        exposure_map[asset_class] = exposure_map.get(asset_class, 0.0) + float(weight)

    constraint_map = {
        item.asset_class: item
        for item in policy.asset_class_constraints
    }
    exposures: list[AssetClassExposure] = []
    breaches: list[str] = []
    for asset_class, weight in sorted(exposure_map.items()):
        constraint = constraint_map.get(asset_class)
        min_weight = constraint.min_weight if constraint is not None else None
        max_weight = constraint.max_weight if constraint is not None else None
        within_bounds = True
        if min_weight is not None and weight < min_weight - 1e-9:
            within_bounds = False
            breaches.append(f"asset_class_min:{asset_class}")
        if max_weight is not None and weight > max_weight + 1e-9:
            within_bounds = False
            breaches.append(f"asset_class_max:{asset_class}")
        exposures.append(
            AssetClassExposure(
                asset_class=asset_class,
                weight=weight,
                min_weight=min_weight,
                max_weight=max_weight,
                within_bounds=within_bounds,
            )
        )

    active_constraints: list[str] = []
    if policy.max_selected_assets is not None:
        active_constraints.append("max_selected_assets")
    if policy.asset_class_constraints:
        active_constraints.extend(
            f"asset_class:{item.asset_class}" for item in policy.asset_class_constraints
        )
    if policy.current_position_weights:
        active_constraints.append("turnover_reporting")
    if applied_constraints:
        for item in applied_constraints:
            if item not in active_constraints:
                active_constraints.append(item)

    return AllocationCandidateConstraintDiagnostics(
        selected_asset_count=selected_asset_count,
        max_selected_assets=policy.max_selected_assets,
        cardinality_breach=cardinality_breach,
        turnover_from_current=_turnover_from_current(
            candidate_weights=positive_weights,
            current_position_weights=policy.current_position_weights,
        ),
        asset_class_exposures=exposures,
        asset_class_breaches=breaches,
        active_constraints=active_constraints,
    )


def _build_rejected_assets(
    *,
    requested_tickers: list[str],
    eligible_tickers: list[str],
    selected_tickers: set[str],
    exclusions: set[str],
    preferred_tickers: set[str],
    eligibility_rejections: dict[str, list[str]],
) -> list[RejectedAsset]:
    rejected: list[RejectedAsset] = []
    for ticker in requested_tickers:
        if ticker in exclusions:
            rejected.append(
                RejectedAsset(
                    ticker=ticker,
                    reason="excluded_by_investor_policy",
                    stage="policy",
                )
            )
        elif ticker in eligibility_rejections:
            rejected.append(
                RejectedAsset(
                    ticker=ticker,
                    reason=";".join(eligibility_rejections[ticker]),
                    stage="eligibility",
                )
            )
        elif ticker not in eligible_tickers:
            rejected.append(
                RejectedAsset(
                    ticker=ticker,
                    reason="not_eligible_after_policy_filters",
                    stage="eligibility",
                )
            )
        elif ticker not in selected_tickers:
            reason = "optimizer_weight_zero_or_below_threshold"
            if ticker in preferred_tickers:
                reason = "preferred_but_not_selected_by_optimizer"
            rejected.append(RejectedAsset(ticker=ticker, reason=reason, stage="optimizer"))
    return rejected


def build_allocation_recommendation(
    req: AllocationRecommendationRequest | dict[str, object] | object,
) -> AllocationRecommendationResponse:
    """Build a typed allocation recommendation from investor inputs and candidate tickers."""
    req = _coerce_request(req)
    recommendation_id = str(uuid.uuid4())
    requested_tickers = _unique_tickers(req.candidate_tickers)
    policy = build_investor_policy(req)
    warnings = list(policy.warnings)

    exclusions = set(policy.excluded_tickers)
    preferred_tickers = set(policy.preferred_tickers)
    eligibility = build_eligible_universe(req=req, policy=policy)
    warnings.extend(eligibility.warnings)
    eligibility_by_ticker: dict[str, EligibleAsset] = {
        asset.ticker: asset for asset in eligibility.eligible_assets
    }
    eligibility_rejections = {
        asset.ticker: list(asset.rejection_reasons)
        for asset in eligibility.rejected_assets
    }
    ml_views: dict[str, MLPredictionInput] = {
        ml.ticker: ml for ml in (req.ml_predictions or [])
    }
    assumptions = build_capital_market_assumptions(
        eligibility=eligibility,
        policy=policy,
        ml_views=ml_views if ml_views else None,
    )
    warnings.extend(assumptions.warnings)
    risk_inputs = build_portfolio_risk_inputs(
        eligibility=eligibility,
        policy=policy,
    )
    warnings.extend(risk_inputs.warnings)
    assumptions_by_ticker = _assumptions_by_ticker(assumptions.assumptions)
    eligible_tickers = [
        ticker
        for ticker in requested_tickers
        if ticker not in exclusions and ticker in set(risk_inputs.tickers_used)
    ]
    if len(eligible_tickers) < 2:
        raise ValueError("at least two eligible tickers are required after applying exclusions")

    investable_amount = round(req.amount * (1.0 - policy.cash_buffer_weight), 2)
    if investable_amount <= 0:
        raise ValueError("investable amount must stay positive after applying the liquidity cash buffer")

    expected_returns = {
        item.ticker: item.expected_return for item in assumptions.assumptions
    }
    candidate_engine = run_allocator_candidate_optimizations_payload(
        tickers=eligible_tickers,
        expected_returns=expected_returns,
        selected_objective=policy.objective_used.value,
        risk_inputs=risk_inputs,
        risk_free_rate=policy.risk_free_rate_used,
        lookback_days=policy.lookback_days,
        max_weight=policy.max_weight,
        min_weight=policy.min_weight,
        max_selected_assets=policy.max_selected_assets,
        asset_class_constraints=policy.asset_class_constraints,
        asset_class_by_ticker={
            ticker: asset.asset_class for ticker, asset in eligibility_by_ticker.items()
        },
    )
    warnings.extend(candidate_engine["warnings"])
    optimization_payload = candidate_engine["selected_payload"]

    ranked_weights = sorted(
        optimization_payload["weights"],
        key=_weight_value,
        reverse=True,
    )
    recommended_assets: list[RecommendedAsset] = []
    selected_tickers: set[str] = set()
    for rank, asset in enumerate(ranked_weights):
        weight = _weight_value(asset)
        if weight <= 0:
            continue
        ticker = str(_asset_field(asset, "ticker"))
        selected_tickers.add(ticker)
        eligible_asset = eligibility_by_ticker.get(ticker)
        assumption = assumptions_by_ticker.get(ticker)
        selection_reason = _selection_reason(
            objective_used=policy.objective_used.value,
            weight=weight,
            rank=rank,
        )
        if assumption is not None:
            selection_reason += (
                f"; expected return assumption={assumption.expected_return:.2%}"
                f" (confidence={assumption.confidence:.0%})"
            )
        recommended_assets.append(
            RecommendedAsset(
                ticker=ticker,
                name=eligible_asset.name if eligible_asset else ticker,
                target_weight=weight,
                target_amount=round(investable_amount * weight, 2),
                role=_asset_role(rank=rank, weight=weight),
                selection_reason=selection_reason,
                expected_return=(
                    assumption.expected_return
                    if assumption is not None
                    else _asset_field(asset, "expected_return")
                ),
                volatility=_asset_field(asset, "volatility"),
            )
        )

    if preferred_tickers:
        missing_preferred = sorted(preferred_tickers - set(eligible_tickers))
        if missing_preferred:
            warnings.append(
                "preferred tickers outside the eligible candidate universe were ignored: "
                + ", ".join(missing_preferred)
            )
        skipped_preferred = sorted(preferred_tickers - selected_tickers - set(missing_preferred))
        if skipped_preferred:
            warnings.append(
                "optimizer did not retain some preferred tickers in the final solution: "
                + ", ".join(skipped_preferred)
            )

    rejected_assets = _build_rejected_assets(
        requested_tickers=requested_tickers,
        eligible_tickers=eligible_tickers,
        selected_tickers=selected_tickers,
        exclusions=exclusions,
        preferred_tickers=preferred_tickers,
        eligibility_rejections=eligibility_rejections,
    )

    total_allocated_amount = round(
        sum(asset.target_amount for asset in recommended_assets),
        2,
    )
    cash_reserve_amount = round(req.amount - total_allocated_amount, 2)

    candidate_portfolios = []
    selected_candidate_id = candidate_engine["selected_candidate_id"]
    selected_risk_diagnostics = None
    selected_constraint_diagnostics = None
    for candidate in candidate_engine["candidates"]:
        candidate_weight_map = _candidate_weight_map(candidate["weights"])
        risk_diagnostics = build_candidate_risk_diagnostics(
            candidate_weights=candidate_weight_map,
            risk_inputs=risk_inputs,
        )
        constraint_diagnostics = _build_constraint_diagnostics(
            candidate_weights=candidate_weight_map,
            policy=policy,
            eligibility_by_ticker=eligibility_by_ticker,
            applied_constraints=candidate.get("applied_constraints"),
        )
        if candidate["candidate_id"] == selected_candidate_id:
            selected_risk_diagnostics = risk_diagnostics
            selected_constraint_diagnostics = constraint_diagnostics
        candidate_portfolios.append(
            AllocationCandidatePortfolio(
                candidate_id=candidate["candidate_id"],
                objective=candidate["objective"],
                selected=candidate["candidate_id"] == selected_candidate_id,
                expected_return=candidate["expected_return"],
                expected_volatility=candidate["expected_volatility"],
                sharpe_ratio=candidate["sharpe_ratio"],
                diversification_ratio=candidate.get("diversification_ratio"),
                tradeoff_summary=candidate["tradeoff_summary"],
                weights=_candidate_asset_allocations(
                    candidate_weights=candidate["weights"],
                    investable_amount=investable_amount,
                    eligibility_by_ticker=eligibility_by_ticker,
                ),
                risk_diagnostics=risk_diagnostics,
                constraint_diagnostics=constraint_diagnostics,
            )
        )

    optimization = AllocationOptimizationSummary(
        objective=optimization_payload["objective"],
        expected_return=optimization_payload["expected_return"],
        expected_volatility=optimization_payload["expected_volatility"],
        sharpe_ratio=optimization_payload["sharpe_ratio"],
        risk_free_rate_used=optimization_payload["risk_free_rate_used"],
        diversification_ratio=optimization_payload.get("diversification_ratio"),
        selected_candidate_id=selected_candidate_id,
        constraint_snapshot=_constraint_snapshot(policy),
        selected_risk_diagnostics=selected_risk_diagnostics,
        selected_constraint_diagnostics=selected_constraint_diagnostics,
        candidate_portfolios=candidate_portfolios,
        efficient_frontier=optimization_payload.get("efficient_frontier", []),
    )

    rebalancing_delta = _build_rebalancing_delta(
        recommended_assets=recommended_assets,
        current_position_weights=policy.current_position_weights,
    )

    _asset_class_by_ticker = {
        ticker: asset.asset_class for ticker, asset in eligibility_by_ticker.items()
    }

    sleeve_breakdown = _build_sleeve_breakdown(
        recommended_assets=recommended_assets,
        asset_class_by_ticker=_asset_class_by_ticker,
        assumptions_by_ticker=assumptions_by_ticker,
    )

    alternatives = _build_alternatives(
        candidates=candidate_engine["candidates"],
        selected_candidate_id=selected_candidate_id,
        recommended_expected_return=optimization_payload["expected_return"],
        recommended_expected_volatility=optimization_payload["expected_volatility"],
    )

    stress_tests = _build_stress_tests(
        recommended_assets=recommended_assets,
        asset_class_by_ticker=_asset_class_by_ticker,
    )

    benchmark_comparison = _build_benchmark_comparison(
        benchmark_preference=policy.benchmark_preference,
        eligible_tickers=eligible_tickers,
        asset_class_by_ticker=_asset_class_by_ticker,
        assumptions_by_ticker=assumptions_by_ticker,
        covariance_matrix=risk_inputs.covariance_matrix,
        recommended_weights={a.ticker: a.target_weight for a in recommended_assets},
        recommended_expected_return=optimization_payload["expected_return"],
        recommended_expected_volatility=optimization_payload["expected_volatility"],
        risk_free_rate=policy.risk_free_rate_used,
    )

    response = AllocationRecommendationResponse(
        recommendation_id=recommendation_id,
        run_id=None,
        persistence_status=PersistenceStatus.inactive,
        policy=policy,
        eligibility=eligibility,
        assumptions=assumptions,
        risk_inputs=risk_inputs,
        eligible_tickers=eligible_tickers,
        recommended_assets=recommended_assets,
        rejected_assets=rejected_assets,
        optimization=optimization,
        total_allocated_amount=total_allocated_amount,
        cash_reserve_amount=cash_reserve_amount,
        sleeve_breakdown=sleeve_breakdown,
        alternatives=alternatives,
        stress_tests=stress_tests,
        rebalancing_delta=rebalancing_delta,
        benchmark_comparison=benchmark_comparison,
        warnings=warnings,
    )

    try:
        persistence_summary = save_allocation_run_sync(
            {
                "recommendation_id": recommendation_id,
                "request_payload": req.model_dump(mode="json"),
                "policy": response.policy.model_dump(mode="json"),
                "eligibility": response.eligibility.model_dump(mode="json"),
                "assumptions": response.assumptions.model_dump(mode="json"),
                "risk_inputs": response.risk_inputs.model_dump(mode="json"),
                "eligible_tickers": response.eligible_tickers,
                "recommended_assets": [
                    asset.model_dump(mode="json") for asset in response.recommended_assets
                ],
                "rejected_assets": [
                    asset.model_dump(mode="json") for asset in response.rejected_assets
                ],
                "optimization": response.optimization.model_dump(mode="json"),
                "total_allocated_amount": response.total_allocated_amount,
                "cash_reserve_amount": response.cash_reserve_amount,
                "warnings": response.warnings,
            }
        )
    except Exception as exc:
        logger.warning("Allocation recommendation persistence failed: %s", exc)
        response.persistence_status = PersistenceStatus.error
        response.warnings.append(
            "allocation run persistence failed; run history is unavailable for this recommendation"
        )
        return response

    if persistence_summary is None:
        response.persistence_status = PersistenceStatus.inactive
        response.warnings.append(
            "allocation persistence is inactive; configure DATABASE_URL to keep run history"
        )
        return response

    response.persistence_status = PersistenceStatus.persisted
    response.run_id = persistence_summary["run_id"]
    return response


async def list_allocation_runs(*, limit: int) -> list[AllocationRunSummary] | None:
    """Return persisted allocation run summaries, or ``None`` if DB is inactive."""
    payload = await list_allocation_runs_db(limit=limit)
    if payload is None:
        return None
    return [AllocationRunSummary(**item) for item in payload]


async def get_allocation_run_payload(run_id: str) -> dict[str, object] | None:
    """
    Return a persisted allocation run payload.

    ``None`` means persistence is inactive.
    ``{}`` means the run id does not exist.
    """
    payload = await get_allocation_run_db(run_id)
    if payload is None:
        return None
    return payload


async def build_live_ml_predictions(
    ml_run_ids: dict[str, str],
    *,
    horizon_days: int = 5,
    period: str = "3y",
    executor=None,
) -> tuple[list[MLPredictionInput], list[str]]:
    """Fetch live ML predictions concurrently for a ticker→run_id mapping.

    Returns (predictions, warnings).  Tickers whose prediction fails are skipped
    and surfaced as warnings rather than raising — the allocator can still run
    without ML views for those assets.

    Adapter:
        PredictionResult.asset              → MLPredictionInput.ticker
        PredictionResult.predicted_return   → MLPredictionInput.predicted_return
        PredictionResult.confidence         → MLPredictionInput.confidence
        PredictionResult.horizon_days       → MLPredictionInput.horizon_days
        f"ml_run:{PredictionResult.run_id}" → MLPredictionInput.source
    """
    import asyncio as _asyncio

    from app.services.ml_service import (
        ArtifactNotFoundError,
        PriceFetchError,
        PredictionExecutionError,
        run_prediction,
    )

    predictions: list[MLPredictionInput] = []
    warnings: list[str] = []

    async def _fetch_one(ticker: str, run_id: str) -> MLPredictionInput | None:
        try:
            result = await run_prediction(
                asset=ticker,
                run_id=run_id,
                horizon_days=horizon_days,
                period=period,
                executor=executor,
            )
            return MLPredictionInput(
                ticker=result.asset,
                predicted_return=result.predicted_return,
                confidence=result.confidence,
                horizon_days=result.horizon_days,
                source=f"ml_run:{result.run_id}",
            )
        except (ArtifactNotFoundError, PriceFetchError, PredictionExecutionError) as exc:
            warnings.append(f"live ML prediction skipped for {ticker}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"live ML prediction skipped for {ticker} (unexpected error): {exc}")
            return None

    results = await _asyncio.gather(*[_fetch_one(t, r) for t, r in ml_run_ids.items()])
    for result in results:
        if result is not None:
            predictions.append(result)

    return predictions, warnings


__all__ = [
    "build_allocation_recommendation",
    "build_live_ml_predictions",
    "get_allocation_run_payload",
    "list_allocation_runs",
]
