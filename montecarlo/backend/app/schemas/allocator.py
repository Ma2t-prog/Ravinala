"""
schemas/allocator.py - Canonical investor policy and allocation recommendation schemas.

First vertical slice of the Portfolio Construction Engine:
`InvestorPolicy` + `AllocationRecommendation`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator

from app.schemas.portfolio import EfficientFrontierPoint, OptimizationObjective


class InvestorObjectiveType(str, Enum):
    growth = "growth"
    balanced = "balanced"
    income = "income"
    capital_preservation = "capital_preservation"


class LiquidityNeeds(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class InvestorRiskProfile(str, Enum):
    aggressive = "aggressive"
    moderate = "moderate"
    conservative = "conservative"


class PersistenceStatus(str, Enum):
    persisted = "persisted"
    inactive = "inactive"
    error = "error"


class CurrentPositionInput(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    weight: float = Field(..., ge=0.0, le=1.0)


class AssetClassConstraintInput(BaseModel):
    asset_class: str = Field(..., min_length=1, max_length=50)
    min_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    max_weight: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "AssetClassConstraintInput":
        if self.min_weight is None and self.max_weight is None:
            raise ValueError("at least one of min_weight or max_weight is required")
        if (
            self.min_weight is not None
            and self.max_weight is not None
            and self.min_weight > self.max_weight
        ):
            raise ValueError("min_weight must be <= max_weight")
        return self


class MLPredictionInput(BaseModel):
    """ML model prediction to be blended into CMA expected returns."""
    ticker: str = Field(..., min_length=1, max_length=20)
    predicted_return: float = Field(
        ...,
        description="Predicted return over horizon_days (decimal, e.g. 0.031 = +3.1%).",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence (val_directional_accuracy). None = legacy artifact, view skipped.",
    )
    horizon_days: int = Field(
        default=5,
        ge=1,
        le=252,
        description="Prediction horizon in trading days, used to annualize the predicted return.",
    )
    source: str = Field(
        default="ml_artifact",
        description="Provenance label for audit purposes.",
    )


class AllocationRecommendationRequest(BaseModel):
    amount: float = Field(..., gt=0.0, description="Portfolio amount to allocate.")
    base_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Reference currency for the recommendation.",
    )
    risk_aversion: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0 = risk-seeking, 1 = strongly risk-averse.",
    )
    investment_horizon_years: int = Field(
        ...,
        ge=1,
        le=50,
        validation_alias=AliasChoices("investment_horizon_years", "investment_horizon"),
        description="Investment horizon used to normalize the investor mandate.",
    )
    liquidity_needs: LiquidityNeeds = Field(
        default=LiquidityNeeds.medium,
        description="Liquidity preference influencing the cash buffer.",
    )
    objective_type: InvestorObjectiveType = Field(
        default=InvestorObjectiveType.balanced,
        description="Primary portfolio objective.",
    )
    income_need: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Income preference ratio used for policy normalization.",
    )
    max_drawdown_tolerance: float | None = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Optional maximum drawdown tolerance.",
    )
    allowed_asset_classes: list[str] = Field(
        default_factory=list,
        description="Allowed asset classes enforced by the allocator eligibility layer.",
    )
    candidate_tickers: list[str] = Field(
        ...,
        min_length=2,
        max_length=50,
        validation_alias=AliasChoices("candidate_tickers", "tickers"),
        description="Candidate investable universe for this first allocator slice.",
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Tickers explicitly excluded by the investor mandate.",
    )
    preferred_tickers: list[str] = Field(
        default_factory=list,
        description="Preferred tickers, used as a soft signal only in this slice.",
    )
    max_selected_assets: int | None = Field(
        default=None,
        ge=2,
        le=25,
        description="Optional cap on the number of non-zero positions kept in the final candidate solutions.",
    )
    asset_class_constraints: list[AssetClassConstraintInput] = Field(
        default_factory=list,
        description="Optional asset-class min/max weight bounds enforced by the allocator candidate engine.",
    )
    current_positions: list[CurrentPositionInput] = Field(
        default_factory=list,
        description="Optional current portfolio weights used to report one-shot turnover versus each candidate.",
    )
    benchmark_preference: str | None = Field(
        default=None,
        description="Optional benchmark preference label for reporting.",
    )
    ml_predictions: list[MLPredictionInput] = Field(
        default_factory=list,
        description=(
            "Optional ML model predictions to blend into CMA expected returns. "
            "When provided, each prediction is confidence-weighted and fused with the "
            "baseline CMA view for the corresponding ticker (blend_factor=0.40)."
        ),
    )


class AllocationLiveMLRequest(AllocationRecommendationRequest):
    """Extends AllocationRecommendationRequest with live ML prediction dispatch.

    The /recommend/with-live-ml endpoint uses this schema to automatically fetch
    ML predictions for the supplied ticker→run_id pairs before CMA blending.
    Explicit ml_predictions (if any) take priority over live-fetched ones.
    """

    ml_run_ids: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Maps ticker → ML run_id. The endpoint will call run_prediction() for each "
            "pair and inject the results into ml_predictions before CMA blending. "
            "Explicit ml_predictions entries override live-fetched ones for the same ticker."
        ),
    )
    ml_horizon_days: int = Field(
        default=5,
        ge=1,
        le=252,
        description="Horizon in trading days used when annualizing live ML predictions.",
    )
    ml_price_period: str = Field(
        default="3y",
        description="Price history period passed to the ML price fetcher (e.g. '3y', '5y').",
    )


class InvestorPolicy(BaseModel):
    recommendation_scope: Literal["candidate_universe_only"] = "candidate_universe_only"
    amount: float
    base_currency: str
    risk_aversion: float
    risk_profile: InvestorRiskProfile
    investment_horizon_years: int
    liquidity_needs: LiquidityNeeds
    objective_type: InvestorObjectiveType
    objective_used: OptimizationObjective
    income_need: float
    max_drawdown_tolerance: float
    max_weight: float
    min_weight: float
    target_volatility: float | None = None
    lookback_days: int
    cash_buffer_weight: float
    risk_free_rate_used: float
    allowed_asset_classes: list[str] = Field(default_factory=list)
    excluded_tickers: list[str] = Field(default_factory=list)
    preferred_tickers: list[str] = Field(default_factory=list)
    max_selected_assets: int | None = None
    asset_class_constraints: list[AssetClassConstraintInput] = Field(default_factory=list)
    current_position_weights: dict[str, float] = Field(default_factory=dict)
    benchmark_preference: str
    warnings: list[str] = Field(default_factory=list)


class RecommendedAsset(BaseModel):
    ticker: str
    name: str
    target_weight: float
    target_amount: float
    role: str
    selection_reason: str
    expected_return: float | None = None
    volatility: float | None = None


class RejectedAsset(BaseModel):
    ticker: str
    reason: str
    stage: str = ""


class EligibilityCriteria(BaseModel):
    heuristic_version: str = "v1"
    min_market_cap: float | None = None
    min_volume_avg_30d: float | None = None
    allowed_asset_classes: list[str] = Field(default_factory=list)
    allowed_currencies: list[str] = Field(default_factory=list)
    require_price: bool = True
    require_market_cap_for_equities: bool = True
    require_volume_proxy: bool = True
    require_cost_proxy: bool = False


class EligibleAsset(BaseModel):
    ticker: str
    name: str
    asset_class: str
    currency: str
    price: float | None = None
    price_change_1m: float | None = None
    price_change_1y: float | None = None
    market_cap: float | None = None
    volume_avg_30d: float | None = None
    dividend_yield: float | None = None
    volatility_1y: float | None = None
    sharpe_1y: float | None = None
    liquidity_tier: str
    data_quality_score: float
    cost_proxy_available: bool
    notes: list[str] = Field(default_factory=list)


class IneligibleAsset(EligibleAsset):
    rejection_reasons: list[str] = Field(default_factory=list)


class EligibleUniverseResponse(BaseModel):
    criteria: EligibilityCriteria
    eligible_assets: list[EligibleAsset] = Field(default_factory=list)
    rejected_assets: list[IneligibleAsset] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CapitalMarketView(BaseModel):
    source: str
    signal: str
    annualized_impact: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class AssetCapitalMarketAssumption(BaseModel):
    ticker: str
    name: str
    asset_class: str
    baseline_expected_return: float
    expected_return: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    volatility_proxy: float | None = None
    methodology: str
    views: list[CapitalMarketView] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CapitalMarketAssumptionsResponse(BaseModel):
    methodology_version: str
    risk_free_rate_used: float
    investment_horizon_years: int
    assumptions: list[AssetCapitalMarketAssumption] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ml_signals_applied: int = Field(
        default=0,
        description="Number of assets whose expected return was blended with an ML prediction view.",
    )


class PortfolioRiskBudget(BaseModel):
    target_volatility: float | None = None
    max_drawdown_tolerance: float
    max_single_name_weight: float
    min_weight: float
    cash_buffer_weight: float
    concentration_hhi_soft_limit: float
    effective_name_floor: float


class AssetRiskInput(BaseModel):
    ticker: str
    name: str
    asset_class: str
    annualized_volatility: float
    downside_volatility: float | None = None
    max_drawdown_proxy: float | None = None
    var_95_1d: float | None = None
    cvar_95_1d: float | None = None
    data_points_used: int


class CorrelationPair(BaseModel):
    left_ticker: str
    right_ticker: str
    correlation: float
    absolute_correlation: float


class UniverseRiskDiagnostics(BaseModel):
    asset_count: int
    observation_count: int
    average_pairwise_correlation: float | None = None
    max_pairwise_correlation: float | None = None
    volatility_dispersion: float | None = None


class RiskGovernanceSummary(BaseModel):
    model_type: str
    covariance_estimator: str
    concentration_support: str
    scenario_support: str
    limitations: list[str] = Field(default_factory=list)


class PortfolioRiskInputsResponse(BaseModel):
    methodology_version: str
    risk_model_type: str
    data_source: str
    lookback_days: int
    observation_count: int
    annualization_factor: int
    risk_free_rate_used: float
    benchmark_preference: str
    tickers_used: list[str] = Field(default_factory=list)
    dropped_tickers: list[str] = Field(default_factory=list)
    asset_risk_inputs: list[AssetRiskInput] = Field(default_factory=list)
    covariance_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    correlation_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    top_correlation_pairs: list[CorrelationPair] = Field(default_factory=list)
    risk_budget: PortfolioRiskBudget
    universe_risk_diagnostics: UniverseRiskDiagnostics
    governance_summary: RiskGovernanceSummary
    warnings: list[str] = Field(default_factory=list)


class AllocationConstraintSnapshot(BaseModel):
    max_weight: float
    min_weight: float
    target_volatility: float | None = None
    max_drawdown_tolerance: float
    cash_buffer_weight: float
    lookback_days: int
    max_selected_assets: int | None = None
    asset_class_constraints: list[AssetClassConstraintInput] = Field(default_factory=list)


class AssetClassExposure(BaseModel):
    asset_class: str
    weight: float
    min_weight: float | None = None
    max_weight: float | None = None
    within_bounds: bool = True


class AllocationCandidateConstraintDiagnostics(BaseModel):
    selected_asset_count: int
    max_selected_assets: int | None = None
    cardinality_breach: bool = False
    turnover_from_current: float | None = None
    asset_class_exposures: list[AssetClassExposure] = Field(default_factory=list)
    asset_class_breaches: list[str] = Field(default_factory=list)
    active_constraints: list[str] = Field(default_factory=list)


class AllocationCandidateAsset(BaseModel):
    ticker: str
    name: str
    weight: float
    amount: float
    expected_return: float | None = None
    volatility: float | None = None


class AllocationCandidateRiskDiagnostics(BaseModel):
    portfolio_volatility: float | None = None
    concentration_hhi: float | None = None
    effective_number_of_names: float | None = None
    max_single_name_weight: float | None = None
    weighted_drawdown_proxy: float | None = None
    target_volatility_gap: float | None = None
    risk_budget_breaches: list[str] = Field(default_factory=list)
    breach_recommended_actions: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Q5.4 — Governance: maps each breach type to the recommended corrective action. "
            "Empty when no breach is detected."
        ),
    )


class AllocationCandidatePortfolio(BaseModel):
    candidate_id: str
    objective: str
    selected: bool = False
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float | None = None
    tradeoff_summary: str
    weights: list[AllocationCandidateAsset] = Field(default_factory=list)
    risk_diagnostics: AllocationCandidateRiskDiagnostics | None = None
    constraint_diagnostics: AllocationCandidateConstraintDiagnostics | None = None


class AllocationOptimizationSummary(BaseModel):
    objective: str
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    risk_free_rate_used: float
    diversification_ratio: float | None = None
    selected_candidate_id: str | None = None
    constraint_snapshot: AllocationConstraintSnapshot
    selected_risk_diagnostics: AllocationCandidateRiskDiagnostics | None = None
    selected_constraint_diagnostics: AllocationCandidateConstraintDiagnostics | None = None
    candidate_portfolios: list[AllocationCandidatePortfolio] = Field(default_factory=list)
    efficient_frontier: list[EfficientFrontierPoint] = Field(default_factory=list)


# ── PC2.4 — Sleeve breakdown ──────────────────────────────────────────────────

class PortfolioSleeve(BaseModel):
    """
    A logical bucket grouping assets in the recommended portfolio by economic role.

    Sleeve names follow the PC2.4 schema:
    ``core_beta`` | ``satellite`` | ``fixed_income`` | ``alternatives`` | ``cash`` | ``other``
    """

    sleeve_name: str
    """Machine-readable bucket name (core_beta, satellite, fixed_income, alternatives, cash, other)."""
    label: str
    """Human-readable label (e.g. 'Core Beta', 'Fixed Income')."""
    tickers: list[str]
    """Tickers assigned to this sleeve, sorted by weight descending."""
    total_weight: float
    """Sum of target_weights for assets in this sleeve."""
    sleeve_expected_return: float | None = None
    """Weight-averaged expected return of sleeve assets (%, same units as optimizer)."""


class SleeveBreakdown(BaseModel):
    """Allocation decomposed into logical sleeves (PC2.4)."""

    sleeves: list[PortfolioSleeve]
    """Non-empty sleeves only, sorted by total_weight descending."""
    method: str
    """Description of the sleeve assignment rule used."""


# ── PC6.4 — Alternative allocations ──────────────────────────────────────────

class AlternativeAllocation(BaseModel):
    """
    A near-alternative allocation produced by a different optimization objective (PC6.4).

    Fields mirror ``AllocationOptimizationSummary`` so consumers can compare directly.
    All return/volatility values are in **percentage points** (same as optimizer output).
    """

    candidate_id: str
    """Internal candidate identifier (e.g. 'min_variance_assumption_aware')."""
    label: str
    """Human label describing this alternative (e.g. 'More Defensive')."""
    description: str
    """One-sentence rationale for this alternative."""
    weights: dict[str, float]
    """Per-ticker weights of this alternative (positive weights only)."""
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    return_diff: float
    """expected_return − recommended.expected_return (pp, negative = lower return)."""
    volatility_diff: float
    """expected_volatility − recommended.expected_volatility (pp, negative = lower risk)."""


class AllocationAlternatives(BaseModel):
    """Alternative allocations derived from non-selected optimization candidates (PC6.4)."""

    alternatives: list[AlternativeAllocation]
    """Alternatives sorted by sharpe_ratio descending (recommended excluded)."""
    method: str


# ── PC4.4 — Stress tests ──────────────────────────────────────────────────────

class StressScenarioResult(BaseModel):
    """
    Portfolio P&L under a single macro stress scenario (PC4.4).

    ``portfolio_impact`` is the approximate one-period return shock:
    Σ(target_weight_i × asset_class_shock_i).
    Asset class shocks are fractions (e.g. -0.30 = -30%).
    ``portfolio_impact`` is also a fraction.
    """

    scenario_name: str
    label: str
    description: str
    asset_class_shocks: dict[str, float]
    """Shock by asset class (fraction).  Tickers with missing class get 0."""
    portfolio_impact: float
    """Approximate portfolio P&L under this scenario (fraction, e.g. -0.12 = -12%)."""
    stressed_value: float
    """Hypothetical portfolio value per $1 invested: 1 + portfolio_impact."""
    largest_detractor: str | None
    """Ticker with the most negative weight × shock contribution."""
    largest_detractor_contribution: float | None
    """Contribution of the largest detractor (fraction)."""


class StressTestSummary(BaseModel):
    """Summary of all stress scenario results for the recommended allocation (PC4.4)."""

    scenarios: list[StressScenarioResult]
    """Results for each built-in scenario."""
    worst_scenario_name: str | None
    """Name of the scenario producing the largest loss."""
    worst_scenario_impact: float | None
    """Portfolio impact (fraction) of the worst scenario."""
    methodology: str
    """Description of how scenario impacts are computed."""


# ── PC7.1 — Benchmark comparison ─────────────────────────────────────────────

class BenchmarkComparison(BaseModel):
    """
    Comparison of the recommended allocation against a simple benchmark baseline (PC7.1).

    All return/volatility fields are in **percentage points** (e.g. 8.5 = 8.5% p.a.),
    consistent with ``AllocationOptimizationSummary.expected_return / expected_volatility``.
    """

    benchmark_name: str
    """Benchmark identifier, e.g. '60_40', 'equal_weight', 'acwi'."""
    benchmark_weights: dict[str, float]
    """Per-ticker weights in the benchmark portfolio (sum ≈ 1.0)."""
    benchmark_expected_return: float
    """Benchmark expected annualized return (%)."""
    benchmark_expected_volatility: float
    """Benchmark expected annualized volatility (%)."""
    benchmark_sharpe_ratio: float
    """(benchmark_er - rfr%) / benchmark_vol."""

    recommended_expected_return: float
    """Recommended portfolio expected return (%) — copied for side-by-side reading."""
    recommended_expected_volatility: float
    """Recommended portfolio expected volatility (%) — copied for side-by-side reading."""

    active_return: float
    """Recommended ER − Benchmark ER (percentage points)."""
    active_risk: float | None
    """
    Tracking error = σ(w_rec − w_bm) annualized (%).
    None when the covariance matrix is unavailable for all overlapping tickers.
    """
    information_ratio: float | None
    """active_return / active_risk. None when active_risk is None or zero."""
    method: str
    """Description of how benchmark weights were derived."""


class RebalancingTradeInstruction(BaseModel):
    """Per-ticker rebalancing instruction derived from current vs target weights."""

    ticker: str
    current_weight: float
    """Weight in the current portfolio (0 if not held)."""
    target_weight: float
    """Weight in the recommended allocation (0 if closed)."""
    delta_weight: float
    """target_weight - current_weight.  Positive = buy, negative = sell."""
    action: Literal["open", "buy", "hold", "sell", "close"]
    """
    open  — ticker not currently held, now entering.
    buy   — ticker already held, increasing weight.
    hold  — weight change < 0.1pp (within rebalancing noise band).
    sell  — ticker already held, reducing weight.
    close — ticker currently held, now exiting entirely.
    """


class RebalancingDelta(BaseModel):
    """
    Rebalancing instructions comparing the recommended allocation to the
    current portfolio (if provided via ``current_positions`` on the request).

    When ``current_positions`` is empty, ``available`` is ``False`` and all
    other fields reflect a full "open from scratch" view (turnover = 1.0 if
    assets are recommended, trades list every position as ``open``).
    """

    available: bool
    """True if current_positions were provided — turnover is then meaningful."""
    one_way_turnover: float
    """
    0.5 × Σ|target_w - current_w|.  Ranges [0, 1].
    One-way turnover: fraction of portfolio to trade.
    If not available, equals 0.5 × sum(target_weights) (full open cost).
    """
    trades: list[RebalancingTradeInstruction]
    """Per-ticker instructions, sorted by |delta_weight| descending."""
    new_positions: list[str]
    """Tickers recommended but not currently held (action=open)."""
    closed_positions: list[str]
    """Tickers currently held but not in recommendation (action=close)."""


class AllocationRecommendationResponse(BaseModel):
    recommendation_id: str
    run_id: str | None = None
    persistence_status: PersistenceStatus
    policy: InvestorPolicy
    eligibility: EligibleUniverseResponse
    assumptions: CapitalMarketAssumptionsResponse
    risk_inputs: PortfolioRiskInputsResponse
    eligible_tickers: list[str]
    recommended_assets: list[RecommendedAsset]
    rejected_assets: list[RejectedAsset]
    optimization: AllocationOptimizationSummary
    total_allocated_amount: float
    cash_reserve_amount: float
    sleeve_breakdown: SleeveBreakdown | None = None
    alternatives: AllocationAlternatives | None = None
    stress_tests: StressTestSummary | None = None
    rebalancing_delta: RebalancingDelta | None = None
    benchmark_comparison: BenchmarkComparison | None = None
    warnings: list[str] = Field(default_factory=list)


class AllocationRecommendationAsyncResponse(BaseModel):
    """Async allocator dispatch payload."""

    job_id: str
    status: Literal["PENDING"] = "PENDING"


class AllocationRunSummary(BaseModel):
    run_id: str
    recommendation_id: str
    created_at: datetime
    amount: float
    base_currency: str
    objective_used: str
    risk_profile: InvestorRiskProfile
    recommended_asset_count: int
    benchmark_preference: str


class AllocationRunDetail(AllocationRecommendationResponse):
    created_at: datetime
