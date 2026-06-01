"""
tradebook_models.py — Data models for the Ravinala Trade Book system.
All models are plain Python dataclasses, serializable to/from dict (JSON-safe).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import uuid


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════

class TradeStatus(str, Enum):
    DRAFT = 'draft'
    LIVE = 'live'
    MATURED = 'matured'
    KNOCKED = 'knocked'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class AssetClass(str, Enum):
    EQUITY = 'equity'
    EQUITY_INDEX = 'equity_index'
    FX = 'fx'
    RATES = 'rates'
    CREDIT = 'credit'
    COMMODITY = 'commodity'
    CRYPTO = 'crypto'
    MULTI_ASSET = 'multi_asset'


class ProductType(str, Enum):
    VANILLA_CALL = 'vanilla_call'
    VANILLA_PUT = 'vanilla_put'
    EUROPEAN_DIGITAL = 'european_digital'
    BARRIER_OPTION = 'barrier_option'
    AUTOCALL = 'autocall'
    PHOENIX = 'phoenix'
    ATHENA = 'athena'
    REVERSE_CONVERTIBLE = 'reverse_convertible'
    CAPITAL_PROTECTED_NOTE = 'capital_protected_note'
    WORST_OF_BASKET = 'worst_of_basket'
    BEST_OF_BASKET = 'best_of_basket'
    HIMALAYA = 'himalaya'
    CLIQUET = 'cliquet'
    VARIANCE_SWAP = 'variance_swap'
    RANGE_ACCRUAL = 'range_accrual'
    CONVERTIBLE_BOND = 'convertible_bond'
    CLN = 'credit_linked_note'
    CUSTOM = 'custom'


class Direction(str, Enum):
    BUY = 'buy'
    SELL = 'sell'


# ═══════════════════════════════════════════════════════════════
# SUB-OBJECTS
# ═══════════════════════════════════════════════════════════════

@dataclass
class Underlying:
    ticker: str
    name: str
    asset_class: str
    spot_at_inception: float
    current_spot: Optional[float] = None
    currency: str = 'USD'
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'Underlying':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class BarrierSpec:
    level_pct: float
    level_abs: float
    barrier_type: str     # 'knock_in' | 'knock_out' | 'autocall' | 'coupon'
    observation: str      # 'continuous' | 'discrete' | 'at_maturity'
    observation_dates: Optional[list] = None
    is_triggered: bool = False
    triggered_date: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CouponSpec:
    rate_pct: float
    frequency: str        # 'monthly' | 'quarterly' | 'semi_annual' | 'annual'
    is_conditional: bool
    condition_barrier_pct: Optional[float] = None
    is_memory: bool = False
    paid_coupons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PricingResult:
    timestamp: str
    model: str
    price: float          # In % of notional (e.g. 98.75 means 98.75%)
    price_currency: str
    notional_value: float # price/100 × notional

    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    rho: Optional[float] = None
    vanna: Optional[float] = None
    volga: Optional[float] = None

    spot_used: Optional[float] = None
    vol_used: Optional[float] = None
    rate_used: Optional[float] = None

    mc_paths: Optional[int] = None
    mc_std_error: Optional[float] = None
    mc_confidence_95: Optional[tuple] = None

    computation_time_ms: Optional[float] = None
    is_stale: bool = False   # True if market data could not be refreshed

    def to_dict(self) -> dict:
        d = asdict(self)
        # tuple is not JSON-serializable
        if d.get('mc_confidence_95') is not None:
            d['mc_confidence_95'] = list(d['mc_confidence_95'])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'PricingResult':
        if d is None:
            return None
        d = dict(d)
        if d.get('mc_confidence_95') is not None:
            d['mc_confidence_95'] = tuple(d['mc_confidence_95'])
        # Remove unknown keys
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class TradeVersion:
    version: int
    created_at: str
    created_by: str
    change_description: str
    parameters: dict
    pricing_result: Optional[dict] = None  # PricingResult as dict

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# TRADE — Central model
# ═══════════════════════════════════════════════════════════════

@dataclass
class Trade:
    # ── Identity ──────────────────────────────────────────────
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    internal_ref: str = ''
    external_ref: str = ''

    # ── Metadata ──────────────────────────────────────────────
    trade_date: str = ''
    created_at: str = ''
    updated_at: str = ''
    created_by: str = ''
    status: str = TradeStatus.DRAFT.value

    # ── Counterparty ──────────────────────────────────────────
    counterparty: str = ''
    sales_person: str = ''
    desk: str = ''

    # ── Product ───────────────────────────────────────────────
    product_type: str = ProductType.CUSTOM.value
    product_name: str = ''
    direction: str = Direction.SELL.value

    # ── Underlyings ───────────────────────────────────────────
    underlyings: list = field(default_factory=list)
    basket_type: str = 'single'

    # ── Terms ─────────────────────────────────────────────────
    notional: float = 1_000_000.0
    currency: str = 'EUR'
    inception_date: str = ''
    maturity_date: str = ''
    settlement_date: str = ''
    tenor_years: float = 0.0

    # ── Strikes & Barriers ────────────────────────────────────
    strike_pct: Optional[float] = None
    strike_abs: Optional[float] = None
    barriers: list = field(default_factory=list)

    # ── Coupon ────────────────────────────────────────────────
    coupon: Optional[dict] = None

    # ── Capital protection ────────────────────────────────────
    capital_protection_pct: Optional[float] = None
    participation_rate: Optional[float] = None
    cap_pct: Optional[float] = None

    # ── Pricing ───────────────────────────────────────────────
    pricing_model: str = 'monte_carlo'
    pricing_params: dict = field(default_factory=dict)
    initial_pricing: Optional[dict] = None
    current_pricing: Optional[dict] = None
    pricing_history: list = field(default_factory=list)

    # ── Market data at inception ──────────────────────────────
    inception_spots: dict = field(default_factory=dict)
    inception_vols: dict = field(default_factory=dict)
    inception_rate: Optional[float] = None
    inception_div_yield: Optional[float] = None
    correlation_matrix: Optional[list] = None

    # ── Versioning ────────────────────────────────────────────
    current_version: int = 1
    versions: list = field(default_factory=list)

    # ── P&L ───────────────────────────────────────────────────
    entry_price: Optional[float] = None      # % of notional
    current_mtm: Optional[float] = None      # absolute currency value
    unrealized_pnl: Optional[float] = None
    realized_pnl: float = 0.0
    total_pnl: Optional[float] = None
    pnl_currency: str = 'EUR'

    # ── Risk ──────────────────────────────────────────────────
    var_95_1d: Optional[float] = None
    var_99_1d: Optional[float] = None
    max_loss: Optional[float] = None

    # ── Tags & notes ──────────────────────────────────────────
    tags: list = field(default_factory=list)
    notes: str = ''
    attachments: list = field(default_factory=list)

    # ── Audit ─────────────────────────────────────────────────
    audit_trail: list = field(default_factory=list)

    # ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'Trade':
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})

    def get_current_pricing(self) -> Optional[PricingResult]:
        if self.current_pricing:
            return PricingResult.from_dict(self.current_pricing)
        return None

    def get_initial_pricing(self) -> Optional[PricingResult]:
        if self.initial_pricing:
            return PricingResult.from_dict(self.initial_pricing)
        return None

    def add_audit(self, user: str, action: str, details: str = ''):
        self.audit_trail.append({
            'timestamp': datetime.utcnow().isoformat(),
            'user': user,
            'action': action,
            'details': details,
        })

    def add_pricing_to_history(self, result: PricingResult):
        """Add a pricing result to history, keep last 100."""
        self.pricing_history.append(result.to_dict())
        if len(self.pricing_history) > 100:
            self.pricing_history = self.pricing_history[-100:]

    @property
    def display_status(self) -> str:
        icons = {
            'draft': 'DRAFT',
            'live': 'LIVE',
            'matured': 'MATURED',
            'knocked': 'KNOCKED',
            'cancelled': 'CANCELLED',
            'expired': 'EXPIRED',
        }
        return icons.get(self.status, self.status.upper())

    @property
    def pnl_display(self) -> str:
        if self.total_pnl is None:
            return 'N/A'
        sign = '+' if self.total_pnl >= 0 else ''
        return f"{sign}{self.total_pnl:,.0f} {self.pnl_currency}"

    @property
    def primary_underlying(self) -> Optional[dict]:
        return self.underlyings[0] if self.underlyings else None


# ═══════════════════════════════════════════════════════════════
# BOOK
# ═══════════════════════════════════════════════════════════════

@dataclass
class Book:
    book_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = 'Default Book'
    description: str = ''
    created_at: str = ''
    created_by: str = ''
    currency: str = 'EUR'
    trades: list = field(default_factory=list)  # List of Trade.to_dict()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'Book':
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})

    def get_trades(self) -> list:
        """Return Trade objects."""
        return [Trade.from_dict(t) for t in self.trades]

    def get_live_trades(self) -> list:
        return [t for t in self.get_trades() if t.status == TradeStatus.LIVE.value]

    @property
    def trade_count(self) -> int:
        return len(self.trades)


# ═══════════════════════════════════════════════════════════════
# DAILY SNAPSHOT
# ═══════════════════════════════════════════════════════════════

@dataclass
class DailySnapshot:
    date: str            # YYYY-MM-DD
    book_id: str
    timestamp: str       # ISO format
    market_data: dict = field(default_factory=dict)
    trades_snapshot: list = field(default_factory=list)
    book_metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'DailySnapshot':
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})


# ═══════════════════════════════════════════════════════════════
# STATUS DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════

STATUS_COLORS = {
    'draft': '#3B82F6',      # blue
    'live': '#22C55E',       # green
    'matured': '#6B7280',    # gray
    'knocked': '#F97316',    # orange
    'cancelled': '#EF4444',  # red
    'expired': '#9CA3AF',    # light gray
}

STATUS_ICONS = {
    'draft': '',
    'live': '',
    'matured': '',
    'knocked': '',
    'cancelled': '',
    'expired': '',
}

PRODUCT_TYPE_LABELS = {
    'vanilla_call': 'Vanilla Call',
    'vanilla_put': 'Vanilla Put',
    'european_digital': 'European Digital',
    'barrier_option': 'Barrier Option',
    'autocall': 'Autocall',
    'phoenix': 'Phoenix',
    'athena': 'Athena',
    'reverse_convertible': 'Reverse Convertible',
    'capital_protected_note': 'Capital Protected Note',
    'worst_of_basket': 'Worst-of Basket',
    'best_of_basket': 'Best-of Basket',
    'himalaya': 'Himalaya',
    'cliquet': 'Cliquet',
    'variance_swap': 'Variance Swap',
    'range_accrual': 'Range Accrual',
    'convertible_bond': 'Convertible Bond',
    'credit_linked_note': 'CLN',
    'custom': 'Custom',
}

ASSET_CLASS_LABELS = {
    'equity': 'Equity',
    'equity_index': 'Equity Index',
    'fx': 'FX',
    'rates': 'Rates / IR',
    'credit': 'Credit',
    'commodity': 'Commodity',
    'crypto': 'Crypto',
    'multi_asset': 'Multi-Asset',
}

ASSET_PREFIXES = {
    'equity': 'EQ',
    'equity_index': 'EQI',
    'fx': 'FX',
    'rates': 'IR',
    'credit': 'CR',
    'commodity': 'CO',
    'crypto': 'CRY',
    'multi_asset': 'MA',
    'custom': 'TR',
}
