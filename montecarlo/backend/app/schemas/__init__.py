"""
schemas/__init__.py
"""
from app.schemas.envelope import ApiResponse, DataQuality  # noqa: F401

# Per-domain schemas (Étape 4 — complétion audit)
from app.schemas.market import (  # noqa: F401
    IndexItem, FXPair, BondItem, CommodityItem, MacroIndicator, SnapshotResponse,
)
from app.schemas.backtest import (  # noqa: F401
    BacktestRequest, BacktestMetrics, BacktestRunResponse,
)
from app.schemas.backtest_api import (  # noqa: F401
    BacktestAsyncResponse,
    BacktestLimitationsResponse,
    BacktestRunRequest,
    CostModelResponse,
    FullRunResponse,
    RunSummary,
    TradeOut,
)
from app.schemas.risk import VaRRequest, VaRResponse  # noqa: F401
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo  # noqa: F401
from app.schemas.ml import (  # noqa: F401
    MLTrainAsyncResponse,
    MLTrainRequest,
    MLTrainResponse,
    ModelInfo,
    PredictRequest,
    PredictionResult,
    RunDetail,
    RunSummary,
    TrainRequest,
    TrainResponse,
)
from app.schemas.users import (  # noqa: F401
    AuditEventResponse,
    AuditTrailResponse,
    RoleInfo,
    RolesResponse,
    SecurityFeatures,
    SecurityStatusResponse,
    UserResponse,
    UserUpdate,
)
from app.schemas.events import EndpointStat, EventSummaryResponse  # noqa: F401
from app.schemas.allocator import (  # noqa: F401
    AllocationOptimizationSummary,
    AllocationRecommendationRequest,
    AllocationRecommendationResponse,
    AllocationRunDetail,
    AllocationRunSummary,
    AssetCapitalMarketAssumption,
    CapitalMarketAssumptionsResponse,
    CapitalMarketView,
    EligibilityCriteria,
    EligibleAsset,
    EligibleUniverseResponse,
    IneligibleAsset,
    InvestorObjectiveType,
    InvestorPolicy,
    InvestorRiskProfile,
    LiquidityNeeds,
    RecommendedAsset,
    RejectedAsset,
)
