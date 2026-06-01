"""
RAVINALA v3.0 — SIDEBAR ASSET CLASSIFICATIONS
Complete hierarchical structure for all asset classes
Author: Bloomberg-style trading platform
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AssetItem:
    """Individual asset/security"""
    id: str
    symbol: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    is_favorite: bool = False
    data_source: str = "LIVE"


@dataclass
class AssetSubCategory:
    """Subcategory within an asset class"""
    id: str
    name: str
    icon: str
    color: str
    items: List[AssetItem] = field(default_factory=list)


@dataclass
class AssetCategory:
    """Top-level asset class"""
    id: str
    name: str
    icon: str
    color: str
    subcategories: List[AssetSubCategory] = field(default_factory=list)


# ==================== COMPLETE ASSET CLASS HIERARCHY ====================

ASSET_CLASSES: List[AssetCategory] = [
    # ==================== EQUITIES ====================
    AssetCategory(
        id='equities',
        name='EQUITIES',
        icon='',
        color='#3B82F6',  # Blue
        subcategories=[
            AssetSubCategory(
                id='large-cap',
                name='Large Cap',
                icon='',
                color='#1E40AF',
                items=[
                    AssetItem(id='aapl', symbol='AAPL', name='Apple Inc.', price=192.53, change_percent=1.14),
                    AssetItem(id='msft', symbol='MSFT', name='Microsoft', price=412.56, change_percent=0.87),
                    AssetItem(id='googl', symbol='GOOGL', name='Alphabet Inc.', price=177.83, change_percent=1.05),
                    AssetItem(id='amzn', symbol='AMZN', name='Amazon.com', price=187.23, change_percent=-0.45),
                    AssetItem(id='nvda', symbol='NVDA', name='NVIDIA', price=892.34, change_percent=2.87),
                    AssetItem(id='tsla', symbol='TSLA', name='Tesla Inc.', price=289.45, change_percent=-1.23),
                ]
            ),
            AssetSubCategory(
                id='mid-cap',
                name='Mid Cap',
                icon='',
                color='#1E40AF',
                items=[
                    AssetItem(id='crm', symbol='CRM', name='Salesforce', price=312.45, change_percent=0.67),
                    AssetItem(id='adbe', symbol='ADBE', name='Adobe Inc.', price=587.23, change_percent=1.34),
                    AssetItem(id='intc', symbol='INTC', name='Intel Corp.', price=43.21, change_percent=-0.89),
                    AssetItem(id='nflx', symbol='NFLX', name='Netflix', price=451.23, change_percent=0.45),
                ]
            ),
            AssetSubCategory(
                id='international',
                name='International',
                icon='',
                color='#1E40AF',
                items=[
                    AssetItem(id='asml', symbol='ASML', name='ASML Holding', price=612.45, change_percent=2.15),
                    AssetItem(id='sap', symbol='SAP', name='SAP SE', price=189.23, change_percent=0.56),
                    AssetItem(id='nestle', symbol='NSRGY', name='Nestlé', price=87.34, change_percent=0.34),
                ]
            ),
            AssetSubCategory(
                id='emerging',
                name='Emerging Markets',
                icon='',
                color='#1E40AF',
                items=[
                    AssetItem(id='tcehy', symbol='TCEHY', name='Tencent', price=34.56, change_percent=1.23),
                    AssetItem(id='baba', symbol='BABA', name='Alibaba', price=87.65, change_percent=-0.45),
                    AssetItem(id='ibrx', symbol='IBRX', name='Ibovespa (Brazil)', price=127_567.0, change_percent=0.78),
                ]
            ),
        ]
    ),

    # ==================== FIXED INCOME ====================
    AssetCategory(
        id='fixed-income',
        name='FIXED INCOME',
        icon='',
        color='#10B981',  # Green
        subcategories=[
            AssetSubCategory(
                id='sovereign-bonds',
                name='Sovereign Bonds',
                icon='',
                color='#059669',
                items=[
                    AssetItem(id='us-10y', symbol='US10Y', name='US 10Y Treasury', price=4.22, change_percent=-0.12),
                    AssetItem(id='us-2y', symbol='US2Y', name='US 2Y Treasury', price=4.12, change_percent=0.08),
                    AssetItem(id='bund-10y', symbol='BUND10Y', name='German Bund 10Y', price=2.89, change_percent=-0.05),
                    AssetItem(id='jgb-10y', symbol='JGB10Y', name='Japan 10Y', price=1.45, change_percent=0.03),
                    AssetItem(id='uk-10y', symbol='UK10Y', name='UK Gilt 10Y', price=4.15, change_percent=-0.08),
                ]
            ),
            AssetSubCategory(
                id='corporate-bonds',
                name='Corporate Bonds',
                icon='',
                color='#059669',
                items=[
                    AssetItem(id='lqd', symbol='LQD', name='Investment Grade ETF', price=98.23, change_percent=0.45),
                    AssetItem(id='ig-spreads', symbol='IG-SPD', name='IG Credit Spreads', price=87.0, change_percent=0.12),
                    AssetItem(id='bbb-rated', symbol='BBB', name='BBB Corporate', price=92.34, change_percent=0.23),
                ]
            ),
            AssetSubCategory(
                id='high-yield',
                name='High Yield',
                icon='',
                color='#059669',
                items=[
                    AssetItem(id='hyg', symbol='HYG', name='High Yield ETF', price=78.45, change_percent=-0.23),
                    AssetItem(id='hy-spreads', symbol='HY-SPD', name='HY Credit Spreads', price=387.0, change_percent=0.34),
                ]
            ),
            AssetSubCategory(
                id='emerging-debt',
                name='Emerging Markets Debt',
                icon='',
                color='#059669',
                items=[
                    AssetItem(id='emb', symbol='EMB', name='EM Bond ETF', price=98.76, change_percent=0.67),
                    AssetItem(id='emdr', symbol='EMDR', name='EM Dollar Bonds', price=101.23, change_percent=0.45),
                ]
            ),
        ]
    ),

    # ==================== DERIVATIVES ====================
    AssetCategory(
        id='derivatives',
        name='DERIVATIVES',
        icon='',
        color='#F59E0B',  # Amber
        subcategories=[
            AssetSubCategory(
                id='futures',
                name='Futures',
                icon='',
                color='#D97706',
                items=[
                    AssetItem(id='es', symbol='ES', name='E-mini S&P 500', price=6787.75, change_percent=1.14),
                    AssetItem(id='nq', symbol='NQ', name='E-mini NASDAQ', price=24684.25, change_percent=1.25),
                    AssetItem(id='cl', symbol='CL', name='Crude Oil Future', price=94.73, change_percent=4.03),
                    AssetItem(id='gc', symbol='GC', name='Gold Future', price=2087.30, change_percent=0.52),
                    AssetItem(id='si', symbol='SI', name='Silver Future', price=31.45, change_percent=0.87),
                ]
            ),
            AssetSubCategory(
                id='options',
                name='Options Chains',
                icon='',
                color='#D97706',
                items=[
                    AssetItem(id='spy-options', symbol='SPY-OPT', name='SPY Options', price=None),
                    AssetItem(id='qqq-options', symbol='QQQ-OPT', name='QQQ Options', price=None),
                    AssetItem(id='iwm-options', symbol='IWM-OPT', name='IWM Options', price=None),
                    AssetItem(id='spy-puts', symbol='SPY-PUTS', name='SPY Put Chains', price=None),
                ]
            ),
            AssetSubCategory(
                id='volatility',
                name='Volatility',
                icon='',
                color='#D97706',
                items=[
                    AssetItem(id='vix', symbol='VIX', name='Volatility Index', price=23.7, change_percent=-9.34),
                    AssetItem(id='move', symbol='MOVE', name='MOVE (Bonds)', price=142.3, change_percent=2.45),
                    AssetItem(id='vvix', symbol='VVIX', name='VIX of VIX', price=34.56, change_percent=1.23),
                ]
            ),
        ]
    ),

    # ==================== COMMODITIES ====================
    AssetCategory(
        id='commodities',
        name='COMMODITIES',
        icon='',
        color='#EF4444',  # Red
        subcategories=[
            AssetSubCategory(
                id='metals',
                name='Metals',
                icon='',
                color='#DC2626',
                items=[
                    AssetItem(id='gold', symbol='GOLD', name='Gold ($/oz)', price=2087.30, change_percent=0.52),
                    AssetItem(id='silver', symbol='SILVER', name='Silver ($/oz)', price=24.56, change_percent=0.87),
                    AssetItem(id='platinum', symbol='PLAT', name='Platinum ($/oz)', price=987.45, change_percent=1.23),
                    AssetItem(id='copper', symbol='COPPER', name='Copper ($/lb)', price=4.32, change_percent=-0.45),
                ]
            ),
            AssetSubCategory(
                id='energy',
                name='Energy',
                icon='',
                color='#DC2626',
                items=[
                    AssetItem(id='wti', symbol='WTI', name='WTI Crude Oil', price=94.73, change_percent=4.03),
                    AssetItem(id='brent', symbol='BRENT', name='Brent Crude', price=99.45, change_percent=3.87),
                    AssetItem(id='natgas', symbol='NATGAS', name='Natural Gas', price=2.87, change_percent=-2.15),
                    AssetItem(id='coal', symbol='COAL', name='Coal', price=187.23, change_percent=0.34),
                ]
            ),
            AssetSubCategory(
                id='agriculture',
                name='Agriculture',
                icon='',
                color='#DC2626',
                items=[
                    AssetItem(id='wheat', symbol='WHEAT', name='Wheat', price=5.67, change_percent=-0.23),
                    AssetItem(id='corn', symbol='CORN', name='Corn', price=4.32, change_percent=0.45),
                    AssetItem(id='soy', symbol='SOY', name='Soybeans', price=12.34, change_percent=0.12),
                    AssetItem(id='sugar', symbol='SUGAR', name='Sugar', price=0.21, change_percent=-0.05),
                    AssetItem(id='coffee', symbol='COFFEE', name='Coffee', price=2.54, change_percent=0.34),
                ]
            ),
        ]
    ),

    # ==================== ETFs ====================
    AssetCategory(
        id='etfs',
        name='ETFs',
        icon='',
        color='#8B5CF6',  # Purple
        subcategories=[
            AssetSubCategory(
                id='equity-etfs',
                name='Equity ETFs',
                icon='',
                color='#7C3AED',
                items=[
                    AssetItem(id='spy', symbol='SPY', name='S&P 500 ETF', price=456.78, change_percent=1.14),
                    AssetItem(id='qqq', symbol='QQQ', name='NASDAQ-100 ETF', price=387.23, change_percent=1.25),
                    AssetItem(id='iwm', symbol='IWM', name='Russell 2000 ETF', price=189.34, change_percent=0.67),
                    AssetItem(id='vxf', symbol='VXF', name='Extended Market ETF', price=192.45, change_percent=0.89),
                ]
            ),
            AssetSubCategory(
                id='bond-etfs',
                name='Bond ETFs',
                icon='',
                color='#7C3AED',
                items=[
                    AssetItem(id='bnd', symbol='BND', name='Total Bond Market', price=72.34, change_percent=0.12),
                    AssetItem(id='lqd-etf', symbol='LQD', name='Investment Grade', price=98.23, change_percent=0.45),
                    AssetItem(id='hyg-etf', symbol='HYG', name='High Yield ETF', price=78.45, change_percent=-0.23),
                ]
            ),
            AssetSubCategory(
                id='commodity-etfs',
                name='Commodity ETFs',
                icon='',
                color='#7C3AED',
                items=[
                    AssetItem(id='gld', symbol='GLD', name='Gold ETF', price=187.45, change_percent=0.52),
                    AssetItem(id='slv', symbol='SLV', name='Silver ETF', price=24.56, change_percent=0.87),
                    AssetItem(id='dbc', symbol='DBC', name='Commodities ETF', price=24.32, change_percent=1.15),
                ]
            ),
            AssetSubCategory(
                id='balanced-etfs',
                name='Balanced/Mixed',
                icon='',
                color='#7C3AED',
                items=[
                    AssetItem(id='aor', symbol='AOR', name='Growth ETF', price=54.32, change_percent=0.89),
                    AssetItem(id='vbal', symbol='VBAL', name='Balanced ETF', price=74.56, change_percent=0.45),
                    AssetItem(id='vgro', symbol='VGRO', name='Growth Portfolio', price=92.34, change_percent=0.67),
                ]
            ),
        ]
    ),

    # ==================== CRYPTO ====================
    AssetCategory(
        id='crypto',
        name='CRYPTO',
        icon='',
        color='#F97316',  # Orange
        subcategories=[
            AssetSubCategory(
                id='major',
                name='Major',
                icon='',
                color='#EA580C',
                items=[
                    AssetItem(id='btc', symbol='BTC', name='Bitcoin', price=67543.25, change_percent=2.34),
                    AssetItem(id='eth', symbol='ETH', name='Ethereum', price=3421.50, change_percent=-1.15),
                    AssetItem(id='bnb', symbol='BNB', name='Binance Coin', price=612.34, change_percent=0.56),
                    AssetItem(id='sol', symbol='SOL', name='Solana', price=138.45, change_percent=0.52),
                ]
            ),
            AssetSubCategory(
                id='altcoins',
                name='Altcoins',
                icon='',
                color='#EA580C',
                items=[
                    AssetItem(id='xrp', symbol='XRP', name='Ripple', price=2.87, change_percent=1.23),
                    AssetItem(id='ada', symbol='ADA', name='Cardano', price=0.98, change_percent=-0.45),
                    AssetItem(id='doge', symbol='DOGE', name='Dogecoin', price=0.34, change_percent=0.67),
                    AssetItem(id='polkadot', symbol='DOT', name='Polkadot', price=7.23, change_percent=0.89),
                ]
            ),
            AssetSubCategory(
                id='defi-staking',
                name='DeFi & Staking',
                icon='',
                color='#EA580C',
                items=[
                    AssetItem(id='aave', symbol='AAVE', name='Aave', price=389.23, change_percent=3.45),
                    AssetItem(id='ldo', symbol='LDO', name='Lido', price=4.56, change_percent=2.15),
                    AssetItem(id='uni', symbol='UNI', name='Uniswap', price=12.34, change_percent=1.56),
                ]
            ),
        ]
    ),
]

# Default favorites for new users
DEFAULT_FAVORITES = [
    AssetItem(id='aapl', symbol='AAPL', name='Apple', price=192.53, change_percent=1.14, is_favorite=True),
    AssetItem(id='spy', symbol='SPY', name='S&P 500', price=456.78, change_percent=1.14, is_favorite=True),
    AssetItem(id='btc', symbol='BTC', name='Bitcoin', price=67543.25, change_percent=2.34, is_favorite=True),
]


def get_all_assets() -> List[AssetItem]:
    """Flatten all assets from hierarchy"""
    assets = []
    for category in ASSET_CLASSES:
        for subcategory in category.subcategories:
            assets.extend(subcategory.items)
    return assets


def search_assets(query: str) -> List[AssetItem]:
    """Search assets by symbol or name"""
    if not query.strip():
        return []
    
    query_lower = query.lower()
    results = []
    
    for asset in get_all_assets():
        if (asset.symbol.lower().startswith(query_lower) or 
            query_lower in asset.name.lower()):
            results.append(asset)
    
    return results[:15]  # Limit to 15 results
